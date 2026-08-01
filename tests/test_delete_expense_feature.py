"""Tests for spec 08 (filed under step 08, functionally step 9):
delete-expense-feature.

Derived from .claude/specs/08_delete-expense-feature.md. Behavior is
asserted against the spec's documented routes (§3), expected behavior
(§11), error handling expectations (§12), and Definition of Done (§13)
only — never against the implementation's internals.
"""
import re

import pytest

from database.db import get_expense_by_id, get_expense_summary

from tests.conftest import insert_expense, login_as, make_user


# --------------------------------------------------------------------- #
# GET/POST /expenses/<id>/delete — session guard                        #
# --------------------------------------------------------------------- #


def test_get_logged_out_redirects_to_login(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense = get_expense_by_id(1)

    response = client.get(f"/expenses/{expense['id']}/delete")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_logged_out_redirects_to_login_and_row_unchanged(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01", description="Untouched")
    expense = get_expense_by_id(1)

    response = client.post(f"/expenses/{expense['id']}/delete")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    # The guard must fire before any deletion — row must still exist,
    # completely unchanged.
    unchanged = get_expense_by_id(expense["id"])
    assert unchanged is not None
    assert unchanged["amount"] == expense["amount"]
    assert unchanged["category"] == expense["category"]
    assert unchanged["date"] == expense["date"]
    assert unchanged["description"] == expense["description"]


def test_stale_session_get_redirects_to_login_and_clears_session(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense = get_expense_by_id(1)

    with client.session_transaction() as sess:
        sess["user_id"] = 999999  # no such user row

    response = client.get(f"/expenses/{expense['id']}/delete")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    with client.session_transaction() as sess:
        assert "user_id" not in sess

    # Stale session must not have deleted anything either.
    assert get_expense_by_id(expense["id"]) is not None


def test_stale_session_post_redirects_to_login_and_clears_session(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense = get_expense_by_id(1)

    with client.session_transaction() as sess:
        sess["user_id"] = 999999

    response = client.post(f"/expenses/{expense['id']}/delete")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    with client.session_transaction() as sess:
        assert "user_id" not in sess

    assert get_expense_by_id(expense["id"]) is not None


# --------------------------------------------------------------------- #
# 404 — nonexistent / not-owned expense (indistinguishable)             #
# --------------------------------------------------------------------- #


def test_get_nonexistent_expense_id_returns_404(client):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)

    response = client.get("/expenses/999999/delete")

    assert response.status_code == 404


def test_post_nonexistent_expense_id_returns_404(client):
    user_id = make_user(email="a@example.com")
    login_as(client, user_id)

    response = client.post("/expenses/999999/delete")

    assert response.status_code == 404


def test_get_expense_owned_by_different_user_returns_404(client):
    owner = make_user(name="Owner", email="owner@example.com")
    other = make_user(name="Other", email="other@example.com")
    insert_expense(owner, 50, "Food", "2024-01-01", description="Owner's lunch")
    expense = get_expense_by_id(1)

    login_as(client, other)
    response = client.get(f"/expenses/{expense['id']}/delete")

    assert response.status_code == 404


def test_post_expense_owned_by_different_user_returns_404_and_row_unchanged(client):
    owner = make_user(name="Owner", email="owner@example.com")
    other = make_user(name="Other", email="other@example.com")
    insert_expense(owner, 50, "Food", "2024-01-01", description="Owner's lunch")
    expense_before = get_expense_by_id(1)

    login_as(client, other)
    response = client.post(f"/expenses/{expense_before['id']}/delete")

    assert response.status_code == 404

    # Strongest ownership check: verify at the DB layer the row is
    # completely untouched (byte-for-byte), not just that the route
    # returned 404.
    expense_after = get_expense_by_id(expense_before["id"])
    assert expense_after is not None
    assert expense_after["id"] == expense_before["id"]
    assert expense_after["user_id"] == expense_before["user_id"]
    assert expense_after["amount"] == expense_before["amount"]
    assert expense_after["category"] == expense_before["category"]
    assert expense_after["date"] == expense_before["date"]
    assert expense_after["description"] == expense_before["description"]
    assert expense_after["created_at"] == expense_before["created_at"]


def test_404_response_identical_for_nonexistent_and_not_owned(client):
    """Ownership must never leak via a different status code than a
    plain nonexistent id (§3, §12)."""
    owner = make_user(name="Owner", email="owner@example.com")
    other = make_user(name="Other", email="other@example.com")
    insert_expense(owner, 50, "Food", "2024-01-01")
    owned_expense = get_expense_by_id(1)

    login_as(client, other)
    not_owned_get = client.get(f"/expenses/{owned_expense['id']}/delete")
    nonexistent_get = client.get("/expenses/999999/delete")

    assert not_owned_get.status_code == nonexistent_get.status_code == 404

    not_owned_post = client.post(f"/expenses/{owned_expense['id']}/delete")
    nonexistent_post = client.post("/expenses/999999/delete")

    assert not_owned_post.status_code == nonexistent_post.status_code == 404


# --------------------------------------------------------------------- #
# GET — own expense, confirmation page, no mutation                     #
# --------------------------------------------------------------------- #


def test_get_own_expense_renders_confirmation_page(client, captured_templates):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 42.50, "Food", "2024-03-15", description="Groceries")
    expense = get_expense_by_id(1)

    login_as(client, user_id)
    response = client.get(f"/expenses/{expense['id']}/delete")

    assert response.status_code == 200
    assert len(captured_templates) == 1
    template, context = captured_templates[0]
    assert template.name == "expenses_delete.html"

    ctx_expense = context["expense"]
    assert ctx_expense["id"] == expense["id"]
    assert ctx_expense["amount"] == expense["amount"]
    assert ctx_expense["category"] == expense["category"]
    assert ctx_expense["date"] == expense["date"]
    assert ctx_expense["description"] == expense["description"]


def test_get_own_expense_no_stub_string_returned(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense = get_expense_by_id(1)

    login_as(client, user_id)
    response = client.get(f"/expenses/{expense['id']}/delete")

    body = response.get_data(as_text=True)
    assert "coming in Step 9" not in body


def test_get_never_mutates_even_when_repeated(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01", description="Still here")
    expense = get_expense_by_id(1)

    login_as(client, user_id)
    for _ in range(3):
        response = client.get(f"/expenses/{expense['id']}/delete")
        assert response.status_code == 200

    unchanged = get_expense_by_id(expense["id"])
    assert unchanged is not None
    assert unchanged["amount"] == expense["amount"]
    assert unchanged["category"] == expense["category"]
    assert unchanged["date"] == expense["date"]
    assert unchanged["description"] == expense["description"]


def test_confirmation_form_action_and_cancel_link_use_url_for(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense = get_expense_by_id(1)

    login_as(client, user_id)
    response = client.get(f"/expenses/{expense['id']}/delete")

    assert response.status_code == 200
    body = response.get_data(as_text=True)

    # Form must POST back to this same delete URL.
    assert (
        re.search(
            rf'<form[^>]*method="POST"[^>]*action="/expenses/{expense["id"]}/delete"',
            body,
            re.IGNORECASE,
        )
        is not None
        or re.search(
            rf'<form[^>]*action="/expenses/{expense["id"]}/delete"[^>]*method="POST"',
            body,
            re.IGNORECASE,
        )
        is not None
    )

    # Cancel link must point back to /profile.
    assert re.search(r'href="/profile"', body) is not None


# --------------------------------------------------------------------- #
# POST — success cases                                                  #
# --------------------------------------------------------------------- #


def test_post_own_expense_deletes_row_and_redirects_to_profile(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 25, "Food", "2024-01-01", description="Lunch")
    expense = get_expense_by_id(1)

    login_as(client, user_id)
    response = client.post(f"/expenses/{expense['id']}/delete")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    assert get_expense_by_id(expense["id"]) is None


def test_deleted_expense_removed_from_profile_recent_and_all_expenses(
    client, captured_templates
):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01", description="Keep me")
    insert_expense(user_id, 20, "Transport", "2024-01-02", description="Delete me")
    keep = get_expense_by_id(1)
    to_delete = get_expense_by_id(2)

    login_as(client, user_id)
    response = client.post(f"/expenses/{to_delete['id']}/delete")
    assert response.status_code == 302

    captured_templates.clear()
    profile_response = client.get("/profile")
    assert profile_response.status_code == 200

    _, context = captured_templates[-1]

    recent_descriptions = {row["description"] for row in context["recent_expenses"]}
    all_descriptions = {row["description"] for row in context["all_expenses"]}

    assert "Delete me" not in recent_descriptions
    assert "Delete me" not in all_descriptions
    assert "Keep me" in recent_descriptions
    assert "Keep me" in all_descriptions


def test_deleted_expense_summary_totals_reflect_removal(client, captured_templates):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    insert_expense(user_id, 20, "Transport", "2024-01-02")
    to_delete = get_expense_by_id(2)

    login_as(client, user_id)

    # DB-level summary (count, total) before the delete — the direct,
    # spec-defined (§4 of spec 04) source of truth for "total spent".
    summary_before = get_expense_summary(user_id)

    captured_templates.clear()
    before_response = client.get("/profile")
    assert before_response.status_code == 200
    _, before_context = captured_templates[-1]
    assert before_context["summary"]["count"] == summary_before["count"]

    response = client.post(f"/expenses/{to_delete['id']}/delete")
    assert response.status_code == 302

    summary_after = get_expense_summary(user_id)
    assert summary_after["count"] == summary_before["count"] - 1
    assert summary_after["total"] == pytest.approx(summary_before["total"] - 20)

    # The rendered profile page's own summary context must reflect the
    # same drop in expense count.
    captured_templates.clear()
    after_response = client.get("/profile")
    assert after_response.status_code == 200
    _, after_context = captured_templates[-1]
    assert after_context["summary"]["count"] == summary_after["count"]


def test_second_post_to_already_deleted_id_returns_404(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense = get_expense_by_id(1)

    login_as(client, user_id)
    first_response = client.post(f"/expenses/{expense['id']}/delete")
    assert first_response.status_code == 302

    second_response = client.post(f"/expenses/{expense['id']}/delete")
    assert second_response.status_code == 404


def test_second_get_to_already_deleted_id_returns_404(client):
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense = get_expense_by_id(1)

    login_as(client, user_id)
    delete_response = client.post(f"/expenses/{expense['id']}/delete")
    assert delete_response.status_code == 302

    stale_confirmation = client.get(f"/expenses/{expense['id']}/delete")
    assert stale_confirmation.status_code == 404


def test_cancel_link_get_does_not_delete(client):
    """'Cancel' is a plain GET-navigable link back to /profile — visiting
    it (or the confirmation page in general) must not delete anything."""
    user_id = make_user(email="a@example.com")
    insert_expense(user_id, 10, "Food", "2024-01-01")
    expense = get_expense_by_id(1)

    login_as(client, user_id)
    client.get(f"/expenses/{expense['id']}/delete")
    profile_response = client.get("/profile")

    assert profile_response.status_code == 200
    assert get_expense_by_id(expense["id"]) is not None


# --------------------------------------------------------------------- #
# Ownership — user_id always taken from session, never form/URL         #
# --------------------------------------------------------------------- #


def test_deleting_one_users_expense_never_affects_another_users_expenses(client):
    user_a = make_user(name="A", email="a@example.com")
    user_b = make_user(name="B", email="b@example.com")

    insert_expense(user_a, 10, "Food", "2024-01-01", description="A1")
    insert_expense(user_b, 20, "Transport", "2024-01-02", description="B1")
    insert_expense(user_b, 30, "Shopping", "2024-01-03", description="B2")

    a_expense = get_expense_by_id(1)
    b_expense_1 = get_expense_by_id(2)
    b_expense_2 = get_expense_by_id(3)

    login_as(client, user_a)
    response = client.post(f"/expenses/{a_expense['id']}/delete")
    assert response.status_code == 302

    assert get_expense_by_id(a_expense["id"]) is None

    # User B's rows must be entirely untouched.
    b1_after = get_expense_by_id(b_expense_1["id"])
    b2_after = get_expense_by_id(b_expense_2["id"])
    assert b1_after is not None
    assert b2_after is not None
    assert b1_after["amount"] == b_expense_1["amount"]
    assert b1_after["description"] == b_expense_1["description"]
    assert b2_after["amount"] == b_expense_2["amount"]
    assert b2_after["description"] == b_expense_2["description"]


def test_post_cannot_delete_another_users_expense_via_spoofed_user_id_field(client):
    user_a = make_user(name="A", email="a@example.com")
    user_b = make_user(name="B", email="b@example.com")
    insert_expense(user_a, 10, "Food", "2024-01-01", description="A's expense")
    expense = get_expense_by_id(1)

    # Logged in as B, attacker tries to delete A's expense while
    # spoofing a user_id form field (e.g. hoping the route trusts the
    # form over the session for ownership).
    login_as(client, user_b)
    response = client.post(
        f"/expenses/{expense['id']}/delete",
        data={"user_id": str(user_a)},
    )

    assert response.status_code == 404
    still_there = get_expense_by_id(expense["id"])
    assert still_there is not None
    assert still_there["user_id"] == user_a
    assert still_there["amount"] == expense["amount"]
    assert still_there["description"] == expense["description"]
