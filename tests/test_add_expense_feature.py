"""Tests for spec 06: add-expense-feature.

Derived from .claude/specs/06_add-expense-feature.md. Behavior is asserted
against the spec's documented routes (§3), expected behavior (§11), error
handling expectations (§12), and Definition of Done (§13) only.
"""
import re

import pytest

from database.db import CATEGORIES, get_all_expenses

from tests.conftest import insert_expense, login_as, make_user


# --------------------------------------------------------------------- #
# GET /expenses/add                                                     #
# --------------------------------------------------------------------- #


def test_get_logged_out_redirects_to_login(client):
    response = client.get("/expenses/add")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_get_logged_in_renders_form_with_categories_and_no_errors(client, captured_templates):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)

    response = client.get("/expenses/add")

    assert response.status_code == 200
    assert len(captured_templates) == 1
    template, context = captured_templates[0]
    assert template.name == "expenses_add.html"
    assert context["categories"] == CATEGORIES
    # No errors on a fresh GET.
    assert not context.get("errors")


def test_get_logged_in_no_stub_string_returned(client):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)

    response = client.get("/expenses/add")

    body = response.get_data(as_text=True)
    assert "coming in Step 7" not in body


def test_stale_session_redirects_to_login_and_clears_session(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 999999  # no such user row

    response = client.get("/expenses/add")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_stale_session_on_post_also_redirects_and_clears(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 999999

    response = client.post(
        "/expenses/add",
        data={"amount": "10", "category": "Food", "date": "2024-01-01"},
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_form_action_uses_url_for_not_hardcoded(client):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)

    response = client.get("/expenses/add")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert re.search(r'<form[^>]*action="/expenses/add"', body) is not None


# --------------------------------------------------------------------- #
# POST /expenses/add — success cases                                    #
# --------------------------------------------------------------------- #


def test_post_valid_data_with_description_inserts_and_redirects(client):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={
            "amount": "42.50",
            "category": "Food",
            "date": "2024-03-15",
            "description": "Groceries",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    rows = get_all_expenses(user_id)
    assert len(rows) == 1
    row = rows[0]
    assert row["amount"] == 42.50
    assert row["category"] == "Food"
    assert row["date"] == "2024-03-15"
    assert row["description"] == "Groceries"
    assert row["user_id"] == user_id


def test_post_valid_data_without_description_succeeds(client):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={"amount": "15", "category": "Transport", "date": "2024-05-01"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    rows = get_all_expenses(user_id)
    assert len(rows) == 1
    # description is optional; omitted value should be stored as falsy
    # (NULL or empty string), never a truthy placeholder.
    assert not rows[0]["description"]


def test_post_valid_data_with_empty_description_string_succeeds(client):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={
            "amount": "15",
            "category": "Transport",
            "date": "2024-05-01",
            "description": "",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    rows = get_all_expenses(user_id)
    assert len(rows) == 1
    assert not rows[0]["description"]


# --------------------------------------------------------------------- #
# POST /expenses/add — invalid amount                                   #
# --------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "amount_value",
    [
        "",  # missing
        "not-a-number",  # non-numeric
        "0",  # zero
        "-5",  # negative
    ],
    ids=["missing", "non_numeric", "zero", "negative"],
)
def test_post_invalid_amount_rejected_no_insert(client, captured_templates, amount_value):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={"amount": amount_value, "category": "Food", "date": "2024-01-01"},
    )

    assert response.status_code == 200
    assert get_all_expenses(user_id) == []

    _, context = captured_templates[-1]
    assert "amount" in context["errors"]
    # Error is scoped to the amount field only — the valid fields shouldn't
    # also be flagged.
    assert "category" not in context["errors"]
    assert "date" not in context["errors"]


# --------------------------------------------------------------------- #
# POST /expenses/add — invalid category                                 #
# --------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "category_value",
    ["", "NotARealCategory"],
    ids=["missing", "unknown"],
)
def test_post_invalid_category_rejected_no_insert(client, captured_templates, category_value):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={"amount": "10", "category": category_value, "date": "2024-01-01"},
    )

    assert response.status_code == 200
    assert get_all_expenses(user_id) == []

    _, context = captured_templates[-1]
    assert "category" in context["errors"]


# --------------------------------------------------------------------- #
# POST /expenses/add — invalid date                                     #
# --------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "date_value",
    ["", "not-a-date", "2024-13-40", "01/01/2024"],
    ids=["missing", "garbage", "invalid_calendar_date", "wrong_format"],
)
def test_post_invalid_date_rejected_no_insert(client, captured_templates, date_value):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={"amount": "10", "category": "Food", "date": date_value},
    )

    assert response.status_code == 200
    assert get_all_expenses(user_id) == []

    _, context = captured_templates[-1]
    assert "date" in context["errors"]


def test_post_future_date_is_allowed(client):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={"amount": "10", "category": "Food", "date": "2099-01-01"},
    )

    assert response.status_code == 302
    rows = get_all_expenses(user_id)
    assert len(rows) == 1
    assert rows[0]["date"] == "2099-01-01"


# --------------------------------------------------------------------- #
# POST /expenses/add — multiple simultaneous errors, echoed values       #
# --------------------------------------------------------------------- #


def test_post_multiple_invalid_fields_all_errors_present_non_short_circuiting(
    client, captured_templates
):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={"amount": "-5", "category": "NotReal", "date": "garbage"},
    )

    assert response.status_code == 200
    assert get_all_expenses(user_id) == []

    _, context = captured_templates[-1]
    assert "amount" in context["errors"]
    assert "category" in context["errors"]
    assert "date" in context["errors"]


def test_post_invalid_form_echoes_submitted_values_back(client, captured_templates):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)

    response = client.post(
        "/expenses/add",
        data={
            "amount": "-5",
            "category": "Food",
            "date": "2024-01-01",
            "description": "keep me",
        },
    )

    assert response.status_code == 200
    _, context = captured_templates[-1]
    assert context["form_values"]["category"] == "Food"
    assert context["form_values"]["date"] == "2024-01-01"
    assert context["form_values"]["description"] == "keep me"


# --------------------------------------------------------------------- #
# Ownership                                                              #
# --------------------------------------------------------------------- #


def test_ownership_expense_always_attributed_to_session_user(client):
    user_a = make_user(name="A", email="a@example.com")
    user_b = make_user(name="B", email="b@example.com")
    login_as(client, user_a)

    # Attempt to tamper by supplying a user_id field pointing at another user.
    response = client.post(
        "/expenses/add",
        data={
            "amount": "10",
            "category": "Food",
            "date": "2024-01-01",
            "user_id": str(user_b),
        },
    )

    assert response.status_code == 302

    rows_a = get_all_expenses(user_a)
    rows_b = get_all_expenses(user_b)
    assert len(rows_a) == 1
    assert rows_a[0]["user_id"] == user_a
    assert rows_b == []


def test_ownership_multiple_users_expenses_stay_isolated(client):
    user_a = make_user(name="A", email="a@example.com")
    user_b = make_user(name="B", email="b@example.com")
    insert_expense(user_b, 999, "Food", "2021-08-01")

    login_as(client, user_a)
    client.post(
        "/expenses/add",
        data={"amount": "10", "category": "Food", "date": "2024-01-01"},
    )

    rows_a = get_all_expenses(user_a)
    rows_b = get_all_expenses(user_b)
    assert len(rows_a) == 1
    assert len(rows_b) == 1
    assert rows_a[0]["user_id"] == user_a
    assert rows_b[0]["user_id"] == user_b
