"""Tests for spec 07 (filed under step 07, functionally step 8):
edit-expense-feature.

Derived from .claude/specs/07_edit-expense-feature.md. Behavior is
asserted against the spec's documented routes (§3), expected behavior
(§11), error handling expectations (§12), and Definition of Done (§13)
only — never against the implementation's internals.
"""
import re

import pytest

from database.db import get_expense_by_id

from tests.conftest import insert_expense, login_as, make_user


# --------------------------------------------------------------------- #
# GET /expenses/<id>/edit — session guard                               #
# --------------------------------------------------------------------- #


def test_get_logged_out_redirects_to_login(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense = get_expense_by_id(1)

    response = client.get(f"/expenses/{expense['id']}/edit")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_logged_out_redirects_to_login_before_processing(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense = get_expense_by_id(1)

    response = client.post(
        f"/expenses/{expense['id']}/edit",
        data={"amount": "20", "category": "Food", "date": "2024-02-02"},
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    # Nothing should have changed since the guard fires before any
    # form processing / ownership check.
    unchanged = get_expense_by_id(expense["id"])
    assert unchanged["amount"] == expense["amount"]
    assert unchanged["date"] == expense["date"]


def test_stale_session_get_redirects_to_login_and_clears_session(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense = get_expense_by_id(1)

    with client.session_transaction() as sess:
        sess["user_id"] = 999999  # no such user row

    response = client.get(f"/expenses/{expense['id']}/edit")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_stale_session_post_redirects_to_login_and_clears_session(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense = get_expense_by_id(1)

    with client.session_transaction() as sess:
        sess["user_id"] = 999999

    response = client.post(
        f"/expenses/{expense['id']}/edit",
        data={"amount": "20", "category": "Food", "date": "2024-02-02"},
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    with client.session_transaction() as sess:
        assert "user_id" not in sess


# --------------------------------------------------------------------- #
# 404 — nonexistent / not-owned expense (indistinguishable)             #
# --------------------------------------------------------------------- #


def test_get_nonexistent_expense_id_returns_404(client):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)

    response = client.get("/expenses/999999/edit")

    assert response.status_code == 404


def test_post_nonexistent_expense_id_returns_404(client):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)

    response = client.post(
        "/expenses/999999/edit",
        data={"amount": "20", "category": "Food", "date": "2024-02-02"},
    )

    assert response.status_code == 404


def test_get_expense_owned_by_different_user_returns_404(client):
    owner = make_user(name="Owner", email="owner@example.com")
    other = make_user(name="Other", email="other@example.com")
    insert_expense(owner, 50, "Food", "2024-01-01", description="Owner's lunch")
    expense = get_expense_by_id(1)

    login_as(client, other)
    response = client.get(f"/expenses/{expense['id']}/edit")

    assert response.status_code == 404


def test_post_expense_owned_by_different_user_returns_404_and_row_unchanged(client):
    owner = make_user(name="Owner", email="owner@example.com")
    other = make_user(name="Other", email="other@example.com")
    insert_expense(owner, 50, "Food", "2024-01-01", description="Owner's lunch")
    expense_before = get_expense_by_id(1)

    login_as(client, other)
    response = client.post(
        f"/expenses/{expense_before['id']}/edit",
        data={
            "amount": "999.99",
            "category": "Shopping",
            "date": "2099-12-31",
            "description": "hijacked",
        },
    )

    assert response.status_code == 404

    # Strongest ownership check: verify at the DB layer the row is
    # completely untouched, not just that the route returned 404.
    expense_after = get_expense_by_id(expense_before["id"])
    assert expense_after["amount"] == expense_before["amount"]
    assert expense_after["category"] == expense_before["category"]
    assert expense_after["date"] == expense_before["date"]
    assert expense_after["description"] == expense_before["description"]
    assert expense_after["user_id"] == owner


def test_404_response_identical_for_nonexistent_and_not_owned(client):
    """Ownership must never leak via a different status code than a
    plain nonexistent id (§3, §12)."""
    owner = make_user(name="Owner", email="owner@example.com")
    other = make_user(name="Other", email="other@example.com")
    insert_expense(owner, 50, "Food", "2024-01-01")
    owned_expense = get_expense_by_id(1)

    login_as(client, other)
    not_owned_response = client.get(f"/expenses/{owned_expense['id']}/edit")
    nonexistent_response = client.get("/expenses/999999/edit")

    assert not_owned_response.status_code == nonexistent_response.status_code == 404


# --------------------------------------------------------------------- #
# GET — own expense, pre-filled form                                    #
# --------------------------------------------------------------------- #


def test_get_own_expense_renders_prefilled_form(client, captured_templates):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 42.50, "Food", "2024-03-15", description="Groceries")
    expense = get_expense_by_id(1)

    login_as(client, user_id)
    response = client.get(f"/expenses/{expense['id']}/edit")

    assert response.status_code == 200
    assert len(captured_templates) == 1
    template, context = captured_templates[0]
    assert template.name == "expenses_edit.html"
    assert not context.get("errors")

    form_values = context["form_values"]
    assert float(form_values["amount"]) == 42.50
    assert form_values["category"] == "Food"
    assert form_values["date"] == "2024-03-15"
    assert form_values["description"] == "Groceries"


def test_get_own_expense_no_stub_string_returned(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense = get_expense_by_id(1)

    login_as(client, user_id)
    response = client.get(f"/expenses/{expense['id']}/edit")

    body = response.get_data(as_text=True)
    assert "coming in Step 8" not in body


def test_form_action_uses_url_for_not_hardcoded(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense = get_expense_by_id(1)

    login_as(client, user_id)
    response = client.get(f"/expenses/{expense['id']}/edit")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert (
        re.search(rf'<form[^>]*action="/expenses/{expense["id"]}/edit"', body)
        is not None
    )


# --------------------------------------------------------------------- #
# POST — success cases                                                  #
# --------------------------------------------------------------------- #


def test_post_valid_data_updates_row_in_place_and_redirects(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01", description="Old")
    expense_before = get_expense_by_id(1)

    login_as(client, user_id)
    response = client.post(
        f"/expenses/{expense_before['id']}/edit",
        data={
            "amount": "99.75",
            "category": "Shopping",
            "date": "2024-06-20",
            "description": "New description",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    expense_after = get_expense_by_id(expense_before["id"])
    assert expense_after["id"] == expense_before["id"]
    assert expense_after["created_at"] == expense_before["created_at"]
    assert expense_after["amount"] == 99.75
    assert expense_after["category"] == "Shopping"
    assert expense_after["date"] == "2024-06-20"
    assert expense_after["description"] == "New description"
    assert expense_after["user_id"] == user_id


def test_post_valid_data_does_not_create_a_new_row(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense_before = get_expense_by_id(1)

    login_as(client, user_id)
    client.post(
        f"/expenses/{expense_before['id']}/edit",
        data={"amount": "20", "category": "Transport", "date": "2024-02-02"},
    )

    # Still exactly one row with this id, and no sibling rows created.
    from database.db import get_all_expenses

    rows = get_all_expenses(user_id)
    assert len(rows) == 1
    assert rows[0]["id"] == expense_before["id"]


def test_post_empty_description_succeeds(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01", description="Old description")
    expense_before = get_expense_by_id(1)

    login_as(client, user_id)
    response = client.post(
        f"/expenses/{expense_before['id']}/edit",
        data={
            "amount": "10",
            "category": "Food",
            "date": "2024-01-01",
            "description": "",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    expense_after = get_expense_by_id(expense_before["id"])
    assert not expense_after["description"]


def test_post_missing_description_field_succeeds(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01", description="Old description")
    expense_before = get_expense_by_id(1)

    login_as(client, user_id)
    response = client.post(
        f"/expenses/{expense_before['id']}/edit",
        data={"amount": "10", "category": "Food", "date": "2024-01-01"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")


# --------------------------------------------------------------------- #
# POST — invalid amount                                                 #
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
def test_post_invalid_amount_rejected_no_update(client, captured_templates, amount_value):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01", description="Untouched")
    expense_before = get_expense_by_id(1)

    login_as(client, user_id)
    response = client.post(
        f"/expenses/{expense_before['id']}/edit",
        data={"amount": amount_value, "category": "Food", "date": "2024-01-01"},
    )

    assert response.status_code == 200

    expense_after = get_expense_by_id(expense_before["id"])
    assert expense_after["amount"] == expense_before["amount"]
    assert expense_after["description"] == expense_before["description"]

    _, context = captured_templates[-1]
    assert "amount" in context["errors"]
    assert "category" not in context["errors"]
    assert "date" not in context["errors"]


# --------------------------------------------------------------------- #
# POST — invalid category                                               #
# --------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "category_value",
    ["", "NotARealCategory"],
    ids=["missing", "unknown"],
)
def test_post_invalid_category_rejected_no_update(client, captured_templates, category_value):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense_before = get_expense_by_id(1)

    login_as(client, user_id)
    response = client.post(
        f"/expenses/{expense_before['id']}/edit",
        data={"amount": "10", "category": category_value, "date": "2024-01-01"},
    )

    assert response.status_code == 200

    expense_after = get_expense_by_id(expense_before["id"])
    assert expense_after["category"] == expense_before["category"]

    _, context = captured_templates[-1]
    assert "category" in context["errors"]


# --------------------------------------------------------------------- #
# POST — invalid date                                                   #
# --------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "date_value",
    ["", "not-a-date", "2024-13-40", "01/01/2024"],
    ids=["missing", "garbage", "invalid_calendar_date", "wrong_format"],
)
def test_post_invalid_date_rejected_no_update(client, captured_templates, date_value):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense_before = get_expense_by_id(1)

    login_as(client, user_id)
    response = client.post(
        f"/expenses/{expense_before['id']}/edit",
        data={"amount": "10", "category": "Food", "date": date_value},
    )

    assert response.status_code == 200

    expense_after = get_expense_by_id(expense_before["id"])
    assert expense_after["date"] == expense_before["date"]

    _, context = captured_templates[-1]
    assert "date" in context["errors"]


# --------------------------------------------------------------------- #
# POST — multiple simultaneous errors, echoed values                    #
# --------------------------------------------------------------------- #


def test_post_multiple_invalid_fields_all_errors_present_non_short_circuiting(
    client, captured_templates
):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense_before = get_expense_by_id(1)

    login_as(client, user_id)
    response = client.post(
        f"/expenses/{expense_before['id']}/edit",
        data={"amount": "-5", "category": "NotReal", "date": "garbage"},
    )

    assert response.status_code == 200

    expense_after = get_expense_by_id(expense_before["id"])
    assert expense_after["amount"] == expense_before["amount"]
    assert expense_after["category"] == expense_before["category"]
    assert expense_after["date"] == expense_before["date"]

    _, context = captured_templates[-1]
    assert "amount" in context["errors"]
    assert "category" in context["errors"]
    assert "date" in context["errors"]


def test_post_invalid_form_echoes_submitted_values_back(client, captured_templates):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense_before = get_expense_by_id(1)

    login_as(client, user_id)
    response = client.post(
        f"/expenses/{expense_before['id']}/edit",
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
# Ownership — user_id always taken from session, never form/URL         #
# --------------------------------------------------------------------- #


def test_post_cannot_override_ownership_via_form_user_id_field(client):
    user_a = make_user(name="A", email="a@example.com")
    user_b = make_user(name="B", email="b@example.com")
    insert_expense(user_a, 10, "Food", "2024-01-01")
    expense = get_expense_by_id(1)

    login_as(client, user_a)
    response = client.post(
        f"/expenses/{expense['id']}/edit",
        data={
            "amount": "20",
            "category": "Food",
            "date": "2024-02-02",
            "user_id": str(user_b),
        },
    )

    assert response.status_code == 302
    updated = get_expense_by_id(expense["id"])
    assert updated["user_id"] == user_a
