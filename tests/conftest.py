"""Shared pytest fixtures for Spendly tests.

Critical: every test must run against a throwaway SQLite file, never the
real `expense_tracker.db` at the project root. `database.db.DB_PATH` is a
hardcoded module-level Path (not configurable via Flask config or env
vars), so we monkeypatch it directly before any table is created.
"""
from contextlib import contextmanager

import pytest
from flask import template_rendered

import app as app_module
import database.db as db


@pytest.fixture()
def app(tmp_path, monkeypatch):
    """Flask app configured against a throwaway, per-test SQLite file."""
    db_path = tmp_path / "test_expense_tracker.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)

    db.init_db()

    app_module.app.config["TESTING"] = True
    yield app_module.app


@pytest.fixture()
def client(app):
    """Flask test client bound to the throwaway-DB app."""
    return app.test_client()


@contextmanager
def _captured_templates(app):
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


@pytest.fixture()
def captured_templates(app):
    """Yield a list that accumulates (template, context) for every render.

    Lets tests assert on the exact values a route passes into
    render_template (e.g. selected_month, available_months, all_expenses)
    without depending on template markup details the spec doesn't dictate.
    """
    with _captured_templates(app) as recorded:
        yield recorded


def make_user(name="Test User", email="test@example.com", password="password123"):
    """Insert a user directly via the db helper and return their id."""
    user_id = db.create_user(name, email, password)
    assert user_id is not None, "setup failed: could not create test user"
    return user_id


def insert_expense(user_id, amount, category, date_str, description=None):
    """Insert an expense row directly, bypassing any route/form layer."""
    conn = db.get_db()
    try:
        conn.execute(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, amount, category, date_str, description),
        )
        conn.commit()
    finally:
        conn.close()


def login_as(client, user_id):
    """Set the session as if the user had already logged in."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
