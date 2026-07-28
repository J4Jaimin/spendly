"""SQLite database helpers for Spendly.

All database access lives here. Route handlers in app.py must never
open a connection or execute SQL directly — call functions from this
module instead.
"""
import calendar
import sqlite3
from datetime import date
from pathlib import Path

from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).resolve().parent.parent / "expense_tracker.db"

CATEGORIES = [
    "Food", "Transport", "Bills", "Health",
    "Entertainment", "Shopping", "Other",
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
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
            """
        )
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
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()


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
