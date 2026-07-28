---
description: Insert N dummy expense rows for an existing user, spread across the last M months, for local dev/testing
argument-hint: "<user_id> <expenses_count> <months_back>"
allowed-tools: Read, Bash(python3:*)
---

Populate dummy expense rows into the `expenses` table for local dev/testing. Do this as a **one-off Bash-run script only** — do NOT add a new function to `database/db.py` or modify any existing project source file. Reuse the existing `get_db()` / `init_db()` helpers exactly as they are; everything else (validation, date/amount/category generation) lives only in the throwaway script for this run.

Arguments (parse from: $ARGUMENTS), in this order: `<user_id> <expenses_count> <months_back>`
- `user_id` — id of the existing user these expenses belong to
- `expenses_count` — how many dummy expense rows to insert
- `months_back` — how many past months (including the current month) to spread the expense dates across

## 0. Explore first

Before running anything, use the Explore subagent to re-read `database/db.py` and confirm the current `expenses` table schema (columns, constraints, FK to `users`), the `CATEGORIES` list, and the signatures of `get_db()` / `init_db()`. Treat the live file as ground truth — CLAUDE.md and this doc can drift out of date.

## 1. Validate arguments

- Require exactly 3 arguments. If missing, non-numeric, or extra, stop and print correct usage: `/populate-dummy-expenses <user_id> <expenses_count> <months_back>` — do not guess defaults for a malformed call.
- `user_id` must parse as a positive integer.
- `expenses_count` must parse as a positive integer, capped at 500 per run — if higher, stop and ask the user to run it in smaller batches instead of silently truncating.
- `months_back` must parse as a non-negative integer, capped at 24 — `0` means "current month only". If higher, stop and ask for confirmation before proceeding.

## 2. Verify the target user exists

Before inserting anything, query `users` for `user_id` in a fresh connection. If no row is found, abort with a clear message (e.g. "No user with id=<id> — run /populate-dummy-user first") instead of letting the insert fail later as an opaque FK `IntegrityError`. `PRAGMA foreign_keys = ON` is already set by `get_db()`, so an invalid `user_id` would otherwise fail confusingly deep in the insert loop.

## 3. Run a one-off python3 script via Bash

From the project root, run a script that:

- Imports `get_db`, `init_db` from `database.db` — do not add new imports or functions to `database/db.py` itself.
- Calls `init_db()` defensively first (idempotent `CREATE TABLE IF NOT EXISTS`).
- For each of the `expenses_count` rows to insert:
  - **category**: random pick from the same fixed pool used elsewhere in this project — `Food, Transport, Bills, Health, Entertainment, Shopping, Other` (matches `CATEGORIES` in `database/db.py`; do not invent new categories).
  - **amount**: random value in **INR**, e.g. between ₹50 and ₹5000, rounded to 2 decimals — this project's currency is INR only, never format or imply USD/`$` anywhere in generated descriptions or output.
  - **date**: pick a random month offset in `[0, months_back]` back from the current month, then a random valid day within that specific calendar month (use `calendar.monthrange` for correct day-count per month, the same approach `_build_sample_expenses` in `database/db.py` already uses — don't assume every month has 30/31 days). Format as `YYYY-MM-DD` to match the existing seeded data.
  - **description**: a short plausible dummy description matching the category (e.g. "Groceries for the week" for Food, "Electricity bill" for Bills).
- **Inserts with a parameterized query** (`?` placeholders, no f-strings in SQL), via `executemany` or a loop, all in one connection/transaction.
- **Commits once and closes the connection in `try/finally`** — don't leak connections on error, and don't leave a partial batch uncommitted if something fails mid-loop (roll back and report the failure clearly instead).
- **Prints a summary**: number of rows inserted, the `user_id`/name they belong to, the earliest and latest date used, and the total amount inserted (formatted as `₹<amount>`, never `$`).

## 4. Report

Tell the user: how many dummy expenses were inserted, for which user (id + name), the date range covered, and the total ₹ amount. Do not implement or modify `/expenses/add`, `database/db.py`, or any other project source file as a side effect — this command only runs a throwaway script that calls the existing DB helpers.
