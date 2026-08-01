"""SQLite database helpers for Spendly.

All database access lives here. Route handlers in app.py must never
open a connection or execute SQL directly — call functions from this
module instead.
"""

import calendar
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

DB_PATH = Path(__file__).resolve().parent.parent / "expense_tracker.db"

CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]


def get_db():
    """Open a new SQLite connection with row access and FK enforcement.

    The caller owns the returned connection and must close it.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the users and expenses tables if they don't exist yet."""
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """)
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert demo data once. No-op if users already has rows."""
    conn = get_db()
    try:
        row = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        if row["count"] > 0:
            return

        password_hash = generate_password_hash("demo123")
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", password_hash),
        )
        user_id = cursor.lastrowid

        conn.executemany(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            _build_sample_expenses(user_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_user_by_email(email):
    """Return the user row matching email, or None if no such user."""
    conn = get_db()
    try:
        return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id):
    """Return the user row matching id, or None if no such user."""
    conn = get_db()
    try:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        conn.close()


def get_expense_summary(user_id):
    """Return {"count": int, "total": float} for a user's expenses."""
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0) AS total
            FROM expenses WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        return {"count": row["count"], "total": row["total"]}
    finally:
        conn.close()


def get_category_breakdown(user_id):
    """Return per-category totals for a user across all fixed CATEGORIES.

    Each entry has "category", "total", and "percentage" (share of the
    user's overall spend), sorted by total descending. Categories with
    no expenses are zero-filled rather than omitted.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT category, COALESCE(SUM(amount), 0) AS total
            FROM expenses WHERE user_id = ? GROUP BY category
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    totals_by_category = {row["category"]: row["total"] for row in rows}
    grand_total = sum(totals_by_category.values())

    breakdown = []
    for category in CATEGORIES:
        total = totals_by_category.get(category, 0)
        percentage = (total / grand_total * 100) if grand_total > 0 else 0
        breakdown.append(
            {
                "category": category,
                "total": total,
                "percentage": percentage,
            }
        )

    breakdown.sort(key=lambda entry: entry["total"], reverse=True)
    return breakdown


def get_recent_expenses(user_id, limit=5):
    """Return a user's most recent expenses, newest first."""
    conn = get_db()
    try:
        return conn.execute(
            """
            SELECT * FROM expenses WHERE user_id = ?
            ORDER BY date DESC, created_at DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()


def get_all_expenses(user_id, month=None):
    """Return a user's expense history, newest first.

    Pass month as a "YYYY-MM" string (already validated by the caller —
    this function trusts it and does not re-validate format) to restrict
    results to that calendar month. Omitting it, or passing None,
    returns the full unfiltered history, identical to before.
    """
    conn = get_db()
    try:
        if month:
            return conn.execute(
                """
                SELECT * FROM expenses WHERE user_id = ?
                AND strftime('%Y-%m', date) = ?
                ORDER BY date DESC, created_at DESC
                """,
                (user_id, month),
            ).fetchall()
        return conn.execute(
            """
            SELECT * FROM expenses WHERE user_id = ?
            ORDER BY date DESC, created_at DESC
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()


def get_available_expense_months(user_id):
    """Return the distinct calendar months a user has expenses in.

    Newest first: [{"value": "2026-07", "label": "July 2026"}, ...].
    Empty list if the user has no expenses at all.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT strftime('%Y-%m', date) AS month
            FROM expenses WHERE user_id = ?
            ORDER BY month DESC
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "value": row["month"],
            "label": datetime.strptime(row["month"], "%Y-%m").strftime("%B %Y"),
        }
        for row in rows
    ]


def get_month_over_month_summary(user_id):
    """Return this-vs-last calendar month spend for a user.

    Returns {"this_month_label", "this_month_total",
    "last_month_label", "last_month_total"}, both totals COALESCE-guarded
    against NULL for a month with zero expenses.
    """
    today = date.today()
    last_month_date = today.replace(day=1) - timedelta(days=1)
    this_month_key = today.strftime("%Y-%m")
    last_month_key = last_month_date.strftime("%Y-%m")

    conn = get_db()
    try:
        this_total = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total FROM expenses
            WHERE user_id = ? AND strftime('%Y-%m', date) = ?
            """,
            (user_id, this_month_key),
        ).fetchone()["total"]
        last_total = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total FROM expenses
            WHERE user_id = ? AND strftime('%Y-%m', date) = ?
            """,
            (user_id, last_month_key),
        ).fetchone()["total"]
    finally:
        conn.close()

    return {
        "this_month_label": today.strftime("%B"),
        "this_month_total": this_total,
        "last_month_label": last_month_date.strftime("%B"),
        "last_month_total": last_total,
    }


def authenticate_user(email, password):
    """Return the user row if email/password match, else None.

    Returns None for both "no such email" and "wrong password" so the
    caller cannot distinguish which part of the credentials was wrong.
    """
    user = get_user_by_email(email)
    if user is None:
        return None
    if not check_password_hash(user["password_hash"], password):
        return None
    return user


def create_user(name, email, password):
    """Insert a new user with a hashed password.

    Returns the new user's id on success, or None if the email is
    already taken (race-condition safety net alongside the caller's
    pre-check via get_user_by_email).
    """
    password_hash = generate_password_hash(password)
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def create_expense(user_id, amount, category, date, description):
    """Insert a new expense for user_id.

    Trusts the caller to have already validated amount/category/date —
    this function does not re-validate format. Returns the new expense's id.
    """
    conn = get_db()
    try:
        cursor = conn.execute(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, amount, category, date, description),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _build_sample_expenses(user_id):
    """Return 8 (user_id, amount, category, date, description) rows.

    Covers all 7 fixed categories at least once, with dates evenly
    spread across the current calendar month in YYYY-MM-DD format.
    """
    today = date.today()
    _, days_in_month = calendar.monthrange(today.year, today.month)

    day_slots = [
        max(1, min(days_in_month, round(1 + i * (days_in_month - 1) / 7)))
        for i in range(8)
    ]
    dates = [today.replace(day=d).isoformat() for d in day_slots]

    entries = [
        (60.50, "Food", "Groceries for the week"),
        (25.00, "Transport", "Bus pass top-up"),
        (120.00, "Bills", "Electricity bill"),
        (45.75, "Health", "Pharmacy purchase"),
        (30.00, "Entertainment", "Movie tickets"),
        (85.20, "Shopping", "New running shoes"),
        (15.00, "Other", "Miscellaneous purchase"),
        (22.40, "Food", "Lunch with friends"),
    ]

    return [
        (user_id, amount, category, expense_date, description)
        for (amount, category, description), expense_date in zip(entries, dates)
    ]
