from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, abort

from database.db import (
    get_db, init_db, seed_db, create_user, get_user_by_email, authenticate_user,
    get_user_by_id, get_expense_summary, get_category_breakdown, get_recent_expenses,
    get_all_expenses, get_available_expense_months, get_month_over_month_summary,
    CATEGORIES, create_expense, get_expense_by_id, update_expense,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"  # dev-only; no secrets management yet


@app.after_request
def add_no_cache_headers(response):
    """Prevent the browser from serving cached pages via back/forward nav.

    Without this, the browser back-button cache (bfcache) can redisplay a
    page like /login or /profile without a fresh request, bypassing the
    session checks in the route functions below.
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name or not email or not password or not confirm_password:
        return render_template("register.html", error="All fields are required.")

    if "@" not in email or "." not in email.split("@")[-1]:
        return render_template("register.html", error="Please enter a valid email address.")

    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.")

    if password != confirm_password:
        return render_template("register.html", error="Passwords do not match.")

    if get_user_by_email(email) is not None:
        return render_template("register.html", error="Email already registered.")

    user_id = create_user(name, email, password)
    if user_id is None:
        return render_template("register.html", error="Email already registered.")

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="Email and password are required.")

    user = authenticate_user(email, password)
    if user is None:
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"] = user["id"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def _format_inr(amount):
    """Format a number as rupees using Indian digit grouping, e.g. 123456.7 -> '₹1,23,456.70'."""
    sign = "-" if amount < 0 else ""
    rupees, paise = divmod(round(abs(amount) * 100), 100)
    digits = str(rupees)
    if len(digits) > 3:
        last3, rest = digits[-3:], digits[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        digits = ",".join(groups) + "," + last3
    return f"{sign}₹{digits}.{paise:02d}"


def _format_display_date(value):
    """Format a stored 'YYYY-MM-DD[...]' string as '25 Jul 2026'."""
    return datetime.strptime(value[:10], "%Y-%m-%d").strftime("%d %b %Y")


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = get_user_by_id(session["user_id"])
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    summary = get_expense_summary(user["id"])
    categories = get_category_breakdown(user["id"])
    recent_expenses = get_recent_expenses(user["id"], limit=3)

    raw_month = request.args.get("month")
    month = None
    selected_month_label = None
    if raw_month:
        try:
            parsed_month = datetime.strptime(raw_month, "%Y-%m")
        except ValueError:
            parsed_month = None
        if parsed_month is not None:
            month = parsed_month.strftime("%Y-%m")
            selected_month_label = parsed_month.strftime("%B %Y")

    available_months = get_available_expense_months(user["id"])
    all_expenses = get_all_expenses(user["id"], month=month)
    month_over_month = get_month_over_month_summary(user["id"])

    average = summary["total"] / summary["count"] if summary["count"] > 0 else 0

    this_month_total = month_over_month["this_month_total"]
    last_month_total = month_over_month["last_month_total"]
    if last_month_total > 0:
        change_pct = (this_month_total - last_month_total) / last_month_total * 100
        if change_pct > 0:
            month_delta = {"text": f"{change_pct:.0f}% more than last month", "direction": "up"}
        elif change_pct < 0:
            month_delta = {"text": f"{abs(change_pct):.0f}% less than last month", "direction": "down"}
        else:
            month_delta = {"text": "Same as last month", "direction": "flat"}
    elif this_month_total > 0:
        month_delta = {"text": "No spending last month", "direction": "up"}
    else:
        month_delta = {"text": "No spending yet", "direction": "flat"}

    return render_template(
        "profile.html",
        user=user,
        member_since=_format_display_date(user["created_at"]),
        summary={
            "count": summary["count"],
            "total_display": _format_inr(summary["total"]),
            "average_display": _format_inr(average),
        },
        categories=[
            {**cat, "total_display": _format_inr(cat["total"])}
            for cat in categories
        ],
        top_category={
            **categories[0],
            "total_display": _format_inr(categories[0]["total"]),
        },
        recent_expenses=[
            {
                "id": expense["id"],
                "date_display": _format_display_date(expense["date"]),
                "category": expense["category"],
                "description": expense["description"] or "",
                "amount_display": _format_inr(expense["amount"]),
            }
            for expense in recent_expenses
        ],
        all_expenses=[
            {
                "id": expense["id"],
                "date_display": _format_display_date(expense["date"]),
                "category": expense["category"],
                "description": expense["description"] or "",
                "amount_display": _format_inr(expense["amount"]),
            }
            for expense in all_expenses
        ],
        selected_month=month,
        selected_month_label=selected_month_label,
        available_months=available_months,
        month_summary={
            "this_month_label": month_over_month["this_month_label"],
            "this_month_display": _format_inr(this_month_total),
            "delta_text": month_delta["text"],
            "delta_direction": month_delta["direction"],
        },
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = get_user_by_id(session["user_id"])
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template(
            "expenses_add.html",
            categories=CATEGORIES,
            errors={},
            form_values={"amount": "", "category": "", "date": "", "description": ""},
        )

    amount_raw = request.form.get("amount", "").strip()
    category_raw = request.form.get("category", "").strip()
    date_raw = request.form.get("date", "").strip()
    description_raw = request.form.get("description", "").strip()

    form_values = {
        "amount": amount_raw,
        "category": category_raw,
        "date": date_raw,
        "description": description_raw,
    }
    errors = {}

    amount_value = None
    if not amount_raw:
        errors["amount"] = "Amount must be a positive number."
    else:
        try:
            amount_value = float(amount_raw)
        except ValueError:
            errors["amount"] = "Amount must be a positive number."
        else:
            if amount_value <= 0:
                errors["amount"] = "Amount must be a positive number."

    if not category_raw or category_raw not in CATEGORIES:
        errors["category"] = "Please choose a valid category."

    date_value = None
    if not date_raw:
        errors["date"] = "Please enter a valid date."
    else:
        try:
            date_value = datetime.strptime(date_raw, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            errors["date"] = "Please enter a valid date."

    if errors:
        return render_template(
            "expenses_add.html",
            categories=CATEGORIES,
            errors=errors,
            form_values=form_values,
        )

    create_expense(
        session["user_id"],
        amount_value,
        category_raw,
        date_value,
        description_raw or None,
    )
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = get_user_by_id(session["user_id"])
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    expense = get_expense_by_id(id)
    if expense is None or expense["user_id"] != session["user_id"]:
        abort(404)

    if request.method == "GET":
        return render_template(
            "expenses_edit.html",
            expense=expense,
            categories=CATEGORIES,
            errors={},
            form_values={
                "amount": expense["amount"],
                "category": expense["category"],
                "date": expense["date"],
                "description": expense["description"] or "",
            },
        )

    amount_raw = request.form.get("amount", "").strip()
    category_raw = request.form.get("category", "").strip()
    date_raw = request.form.get("date", "").strip()
    description_raw = request.form.get("description", "").strip()

    form_values = {
        "amount": amount_raw,
        "category": category_raw,
        "date": date_raw,
        "description": description_raw,
    }
    errors = {}

    amount_value = None
    if not amount_raw:
        errors["amount"] = "Amount must be a positive number."
    else:
        try:
            amount_value = float(amount_raw)
        except ValueError:
            errors["amount"] = "Amount must be a positive number."
        else:
            if amount_value <= 0:
                errors["amount"] = "Amount must be a positive number."

    if not category_raw or category_raw not in CATEGORIES:
        errors["category"] = "Please choose a valid category."

    date_value = None
    if not date_raw:
        errors["date"] = "Please enter a valid date."
    else:
        try:
            date_value = datetime.strptime(date_raw, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            errors["date"] = "Please enter a valid date."

    if errors:
        return render_template(
            "expenses_edit.html",
            expense=expense,
            categories=CATEGORIES,
            errors=errors,
            form_values=form_values,
        )

    update_expense(
        id,
        session["user_id"],
        amount_value,
        category_raw,
        date_value,
        description_raw or None,
    )
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
