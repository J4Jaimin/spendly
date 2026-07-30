"""Tests for spec 05: month filter on the /profile "All expenses" panel.

Derived from .claude/specs/05_date-filter-on-profile-page.md. Behavior is
asserted against the spec's documented routes, functions, rules, and error
handling expectations only.
"""
import re

import pytest

from database.db import get_all_expenses, get_available_expense_months

from tests.conftest import insert_expense, login_as, make_user


# --------------------------------------------------------------------- #
# Route-level tests: GET /profile?month=...                             #
# --------------------------------------------------------------------- #


def test_no_month_param_shows_full_unfiltered_history(client, captured_templates):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)
    insert_expense(user_id, 10, "Food", "2021-04-01")
    insert_expense(user_id, 20, "Food", "2021-05-01")
    insert_expense(user_id, 30, "Food", "2021-06-01")

    response = client.get("/profile")

    assert response.status_code == 200
    assert len(captured_templates) == 1
    _, context = captured_templates[0]
    assert context["selected_month"] is None
    assert len(context["all_expenses"]) == 3


def test_valid_month_filters_all_expenses_panel_only(client, captured_templates):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)
    insert_expense(user_id, 10, "Food", "2021-05-02", description="may-1")
    insert_expense(user_id, 15, "Transport", "2021-05-10", description="may-2")
    insert_expense(user_id, 20, "Bills", "2021-06-01", description="june-1")

    response = client.get("/profile?month=2021-05")

    assert response.status_code == 200
    _, context = captured_templates[-1]
    assert context["selected_month"] == "2021-05"
    descriptions = {row["description"] for row in context["all_expenses"]}
    assert descriptions == {"may-1", "may-2"}


def test_valid_month_filter_returns_newest_first(client, captured_templates):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)
    insert_expense(user_id, 10, "Food", "2021-05-02", description="early")
    insert_expense(user_id, 20, "Food", "2021-05-20", description="late")

    response = client.get("/profile?month=2021-05")

    assert response.status_code == 200
    _, context = captured_templates[-1]
    descriptions = [row["description"] for row in context["all_expenses"]]
    assert descriptions == ["late", "early"]


def test_other_panels_unaffected_by_month_filter(client, captured_templates):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)
    insert_expense(user_id, 10, "Food", "2021-04-15")
    insert_expense(user_id, 20, "Transport", "2021-05-15")
    insert_expense(user_id, 30, "Bills", "2021-06-15")

    unfiltered = client.get("/profile")
    filtered = client.get("/profile?month=2021-05")

    assert unfiltered.status_code == 200
    assert filtered.status_code == 200
    assert len(captured_templates) == 2
    _, unfiltered_ctx = captured_templates[0]
    _, filtered_ctx = captured_templates[1]

    # These cards/panels stay lifetime/unfiltered regardless of the filter.
    assert unfiltered_ctx["summary"] == filtered_ctx["summary"]
    assert unfiltered_ctx["categories"] == filtered_ctx["categories"]
    assert unfiltered_ctx["top_category"] == filtered_ctx["top_category"]
    assert unfiltered_ctx["recent_expenses"] == filtered_ctx["recent_expenses"]
    assert unfiltered_ctx["month_summary"] == filtered_ctx["month_summary"]
    assert unfiltered_ctx["available_months"] == filtered_ctx["available_months"]

    # Only the "All expenses" panel and selected_month differ.
    assert filtered_ctx["selected_month"] == "2021-05"
    assert len(filtered_ctx["all_expenses"]) == 1
    assert len(unfiltered_ctx["all_expenses"]) == 3


def test_available_months_populated_newest_first_with_labels(client, captured_templates):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)
    insert_expense(user_id, 10, "Food", "2021-04-01")
    insert_expense(user_id, 20, "Food", "2021-06-01")
    insert_expense(user_id, 30, "Food", "2021-05-01")

    response = client.get("/profile")

    assert response.status_code == 200
    _, context = captured_templates[-1]
    assert context["available_months"] == [
        {"value": "2021-06", "label": "June 2021"},
        {"value": "2021-05", "label": "May 2021"},
        {"value": "2021-04", "label": "April 2021"},
    ]


@pytest.mark.parametrize(
    "bad_month",
    ["", "garbage", "2021", "2021/05", "05-2021", "abcd-ef", "2021-05-01"],
)
def test_malformed_month_falls_back_to_all_time(client, captured_templates, bad_month):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)
    insert_expense(user_id, 10, "Food", "2021-04-01")
    insert_expense(user_id, 20, "Food", "2021-05-01")

    response = client.get(f"/profile?month={bad_month}")

    assert response.status_code == 200
    _, context = captured_templates[-1]
    assert context["selected_month"] is None
    assert len(context["all_expenses"]) == 2


def test_valid_month_with_zero_expenses_shows_scoped_empty_state(client, captured_templates):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)
    insert_expense(user_id, 10, "Food", "2021-04-01")

    response = client.get("/profile?month=2099-01")

    assert response.status_code == 200
    _, context = captured_templates[-1]
    assert context["selected_month"] == "2099-01"
    assert context["all_expenses"] == []
    # Page-wide "no expenses yet" empty state must NOT trigger — the user
    # does have lifetime expenses, this is only an empty month.
    assert context["summary"]["count"] == 1


def test_ownership_month_filter_scoped_to_session_user(client, captured_templates):
    user_a = make_user(name="A", email="a@example.com")
    user_b = make_user(name="B", email="b@example.com")
    insert_expense(user_a, 10, "Food", "2021-04-01")
    insert_expense(user_b, 999, "Food", "2021-08-01")

    login_as(client, user_a)
    response = client.get("/profile?month=2021-08")

    assert response.status_code == 200
    _, context = captured_templates[-1]
    # user B's month must not leak into A's available months or results
    assert {m["value"] for m in context["available_months"]} == {"2021-04"}
    assert context["all_expenses"] == []


def test_ownership_available_months_only_own_months(client, captured_templates):
    user_a = make_user(name="A", email="a@example.com")
    user_b = make_user(name="B", email="b@example.com")
    insert_expense(user_a, 10, "Food", "2021-04-01")
    insert_expense(user_a, 15, "Food", "2021-05-01")
    insert_expense(user_b, 20, "Food", "2021-06-01")
    insert_expense(user_b, 25, "Food", "2021-07-01")

    login_as(client, user_a)
    response = client.get("/profile")

    assert response.status_code == 200
    _, context = captured_templates[-1]
    values = {m["value"] for m in context["available_months"]}
    assert values == {"2021-04", "2021-05"}


def test_zero_expenses_overall_available_months_empty_and_no_crash(client, captured_templates):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)

    response = client.get("/profile")

    assert response.status_code == 200
    _, context = captured_templates[-1]
    assert context["available_months"] == []
    assert context["selected_month"] is None


def test_no_session_redirects_to_login(client):
    response = client.get("/profile?month=2021-05")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_filter_form_action_points_to_profile(client):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)
    insert_expense(user_id, 10, "Food", "2021-04-01")

    response = client.get("/profile")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    # The filter form must submit to /profile (via url_for('profile')),
    # never a different or malformed hardcoded path.
    assert re.search(r'<form[^>]*action="/profile"', body) is not None


def test_selected_month_option_marked_selected_in_dropdown(client):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)
    insert_expense(user_id, 10, "Food", "2021-05-01")
    insert_expense(user_id, 20, "Food", "2021-06-01")

    response = client.get("/profile?month=2021-05")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    option_pattern = re.compile(
        r'<option[^>]*value="2021-05"[^>]*selected|'
        r'<option[^>]*selected[^>]*value="2021-05"'
    )
    assert option_pattern.search(body) is not None


# --------------------------------------------------------------------- #
# Database-level tests: get_all_expenses(user_id, month=None)           #
# --------------------------------------------------------------------- #


def test_get_all_expenses_backward_compatible_no_month_arg(app):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2021-04-01")
    insert_expense(user_id, 20, "Food", "2021-05-01")

    rows = get_all_expenses(user_id)

    assert len(rows) == 2


def test_get_all_expenses_month_filters_by_calendar_month(app):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2021-04-15")
    insert_expense(user_id, 20, "Food", "2021-05-02")
    insert_expense(user_id, 30, "Food", "2021-05-20")

    rows = get_all_expenses(user_id, month="2021-05")

    assert len(rows) == 2
    assert all(row["date"].startswith("2021-05") for row in rows)


def test_get_all_expenses_month_none_identical_to_unfiltered(app):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2021-04-15")
    insert_expense(user_id, 20, "Food", "2021-05-02")

    default_call = get_all_expenses(user_id)
    explicit_none = get_all_expenses(user_id, month=None)

    assert len(default_call) == len(explicit_none) == 2


def test_get_all_expenses_ordering_newest_first(app):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2021-05-05", description="middle")
    insert_expense(user_id, 20, "Food", "2021-05-20", description="newest")
    insert_expense(user_id, 30, "Food", "2021-05-01", description="oldest")

    rows = get_all_expenses(user_id, month="2021-05")

    assert [row["description"] for row in rows] == ["newest", "middle", "oldest"]


def test_get_all_expenses_month_scoped_to_user(app):
    user_a = make_user(name="A", email="a@example.com")
    user_b = make_user(name="B", email="b@example.com")
    insert_expense(user_a, 10, "Food", "2021-05-01")
    insert_expense(user_b, 20, "Food", "2021-05-02")

    rows = get_all_expenses(user_a, month="2021-05")

    assert len(rows) == 1
    assert rows[0]["user_id"] == user_a


# --------------------------------------------------------------------- #
# Database-level tests: get_available_expense_months(user_id)           #
# --------------------------------------------------------------------- #


def test_get_available_expense_months_empty_for_new_user(app):
    user_id = make_user(email="a@example.com")

    months = get_available_expense_months(user_id)

    assert months == []


def test_get_available_expense_months_distinct_newest_first_with_labels(app):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2021-04-01")
    insert_expense(user_id, 15, "Food", "2021-04-15")  # same month, must dedupe
    insert_expense(user_id, 20, "Food", "2021-06-01")
    insert_expense(user_id, 30, "Food", "2021-05-01")

    months = get_available_expense_months(user_id)

    assert months == [
        {"value": "2021-06", "label": "June 2021"},
        {"value": "2021-05", "label": "May 2021"},
        {"value": "2021-04", "label": "April 2021"},
    ]


def test_get_available_expense_months_scoped_to_user(app):
    user_a = make_user(name="A", email="a@example.com")
    user_b = make_user(name="B", email="b@example.com")
    insert_expense(user_a, 10, "Food", "2021-04-01")
    insert_expense(user_b, 20, "Food", "2021-07-01")

    months_a = get_available_expense_months(user_a)

    assert months_a == [{"value": "2021-04", "label": "April 2021"}]
