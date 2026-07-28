---
description: Insert a dummy user (Indian-origin name) into the Spendly database for local testing
argument-hint: "[optional full name, e.g. \"Priya Nair\"]"
allowed-tools: Read, Bash(python3:*)
---

!! IMPORTANT
Do not ask for running any command run it directly. we are currently running custom shell command.

Populate one dummy user row into the `users` table for local dev/testing. Do this as a **one-off Bash-run script only** — do NOT add a new function to `database/db.py` or modify any existing project source file. Reuse the existing `get_db()` / `init_db()` helpers exactly as they are; everything else (name/email generation, retry logic) lives only in the throwaway script for this run.

## 0. Explore first

Before running anything, use the Explore subagent to re-read `database/db.py` and confirm the current `users` table schema (columns, constraints) and the exact signatures of `get_db()` / `init_db()`. Do not assume the schema in this doc is still accurate — CLAUDE.md itself can drift out of date. Treat the live file as ground truth.

## 1. Run a one-off python3 script via Bash

From the project root, run something like `python3 -c "..."` (or a short heredoc) that:

- Imports `get_db`, `init_db` from `database.db`, and `generate_password_hash` from `werkzeug.security`. Import `random`/`re` from the stdlib as needed — do not add these imports to `database/db.py` itself.
- **Ensures tables exist first** — calls `init_db()` defensively (it's `CREATE TABLE IF NOT EXISTS`, safe to call repeatedly) before inserting.
- **Picks a name**: if this argument is non-empty, use it as the name: $ARGUMENTS — otherwise randomly compose one from a small pool of common Indian first/last names (mix of regions/genders, e.g. Aarav, Priya, Rohan, Ananya, Kabir, Meera + Sharma, Iyer, Nair, Verma, Reddy, Singh, Gupta).
- **Validates the name**: strip whitespace, abort with a clear error if empty after stripping.
- **Derives a unique email**: lowercase, ASCII-strip the name (spaces → dots, drop other punctuation), append a random numeric suffix, `@example.com` domain — e.g. `priya.nair482@example.com`. Must not collide with the real seeded demo account (`demo@spendly.com`).
- **Hashes a fixed dummy password** (`"DummyPass123!"`) with `generate_password_hash` — never insert a plaintext password.
- **Inserts with a parameterized query** via `get_db()` (`?` placeholders, no f-strings in SQL).
- **Handles the UNIQUE(email) collision edge case**: wrap the insert in `try/except sqlite3.IntegrityError`, and on collision regenerate the numeric suffix and retry, capped at ~5 attempts, then raise a clear error if still colliding.
- **Commits and closes the connection in `try/finally`** — don't leak connections on error.
- **Prints the inserted row** (id, name, email, created_at), read back with a fresh `SELECT`, not just assumed from the insert.

## 3. Report

Tell the user the created user's `id`, `name`, `email`, and the dummy password (`DummyPass123!`) so they can log in manually once `/login` is wired up. Do not implement or modify the `/register` POST handler, `database/db.py`, or any other project source file as a side effect — this command only runs a throwaway script that calls the existing DB helpers.
