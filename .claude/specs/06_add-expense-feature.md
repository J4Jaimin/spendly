# Spec Document

## 1. Overview

Reference: see `CLAUDE.md` for full project architecture, code style, and tech constraints — this spec must stay consistent with it.

Implement the "add expense" feature: turn the existing `GET /expenses/add` stub into a real form that lets a logged-in user record a new expense against their own account. Today the route is a bare stub (`app.py:230-232`) that returns the literal string `"Add expense — coming in Step 7"` with no template, no form, and no POST handling. This step adds `methods=["GET", "POST"]` to the route, a new `templates/expenses_add.html` form (amount, category, date, description), a new `create_expense(...)` helper in `database/db.py` to insert the row, and validation for every field before it reaches the database.

**⚠️ Step-number cross-check (mismatch found):** this spec was requested as **"Step 6 — add-expense-feature."** CLAUDE.md's "Implemented vs stub routes" table has **no entry tagged "Step 6"** at all — the table jumps `Step 3` (`/logout`) → `Step 4` (`/profile`) → `Step 7` (`/expenses/add`) → `Step 8` (`/expenses/<id>/edit`) → `Step 9` (`/expenses/<id>/delete`). Steps 5 and 6 don't exist as route tags in CLAUDE.md (spec `05_date-filter-on-profile-page.md` already flagged the same gap for "Step 5," which turned out to be a sub-feature of the Step-4 route rather than a new stub). The feature described here — "add-expense-feature" — matches the route and stub comment that CLAUDE.md and `app.py` both explicitly tag **`Step 7`**, not Step 6 (`app.py:232`: `"Add expense — coming in Step 7"`). This spec proceeds using the requested filename number (`06_add-expense-feature.md`, per the `/create-spec` argument order) but implements the functionality of the route CLAUDE.md calls Step 7. Flag this to the human maintainer to confirm whether the spec should be renumbered to `07_add-expense-feature.md` to match CLAUDE.md, or whether CLAUDE.md's table should be updated to insert a Step 6 — this spec does not edit CLAUDE.md itself, per the rule below.

**Also flagged, not fixed by choice:** CLAUDE.md still says "`database/db.py` is currently empty" — it is not; it already has 14 functions implemented (confirmed by reading the live file). This is pre-existing CLAUDE.md drift, unrelated to this feature, already flagged once by spec 05 and called out again here rather than silently corrected.

**Scope decision:** this step only implements `GET /expenses/add` and its `POST` handling. It does **not** touch `GET /expenses/<id>/edit` or `GET /expenses/<id>/delete` — those remain untouched stubs tagged Step 8 and Step 9 respectively, per CLAUDE.md's rule against implementing a stub outside its assigned step.

**Implementation approach:** a plain HTML `POST` form on `templates/expenses_add.html` (no client-side JS, no AJAX) that submits back to `GET /expenses/add`'s own URL. On successful validation and insert, the route redirects to `GET /profile` (the natural place a user lands after adding an expense, and where the new row will immediately show up in "Recent expenses" / "All expenses"). On validation failure, the route re-renders the same form with the submitted values preserved and inline error messages — no separate error page, no `abort()` for validation errors (those are user-correctable input problems, not HTTP errors).

---

## 2. Depends on

- Step 1 (`database-setup`) — requires the live `expenses` table schema and the `CATEGORIES` fixed list, both already defined in `database/db.py`. Confirmed present.
- Step 4 (`create-profile-page`) — requires the session-guard-and-fetch pattern (`session.get("user_id")` → redirect to `login` if absent → `get_user_by_id` → `session.clear()` + redirect if stale) already used in `profile()` (`app.py:138-144`). This step reuses the identical pattern rather than inventing a new one.

---

## 3. Routes

### `GET/POST /expenses/add` (replace the existing stub, don't add a second route)

- Current state: `app.py:230-232` is a GET-only stub that returns a raw string. No form, no session guard, no DB interaction.
- New behavior:
  - Add `methods=["GET", "POST"]` to the route decorator.
  - Session guard identical to `profile()`: if `session.get("user_id")` is absent, redirect to `url_for("login")`. If `get_user_by_id(session["user_id"])` returns `None` (stale session), `session.clear()` and redirect to `login`.
  - **On `GET`**: render `expenses_add.html` with the fixed `CATEGORIES` list (for the category `<select>`) and no pre-filled values (or empty-string defaults).
  - **On `POST`**: read `amount`, `category`, `date`, `description` from `request.form`. Validate each (see §12). If any validation fails, re-render `expenses_add.html` with the submitted values echoed back into the form fields and an error message — do not insert anything, do not redirect. If all fields are valid, call `create_expense(user_id, amount, category, date, description)` (§5), then `redirect(url_for("profile"))`.
  - The inserted expense's `user_id` is always `session["user_id"]` — never taken from the form — so a user can only ever create an expense for themselves.

No changes to `/login`, `/register`, `/logout`, `/profile`, or the `/expenses/<id>/edit` and `/expenses/<id>/delete` stubs — those remain exactly as-is (per CLAUDE.md: never implement a stub route outside its assigned step).

---

## 4. Database Schema

No schema changes. Reuses the existing `expenses` table exactly as defined in `database/db.py`:

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | Primary key, autoincrement |
| user_id | INTEGER | Foreign key → users.id, not null |
| amount | REAL | Not null |
| category | TEXT | Not null |
| date | TEXT | Not null (`YYYY-MM-DD`, matching the format every existing read function already assumes, e.g. `strftime('%Y-%m', date)` in `get_month_over_month_summary`) |
| description | TEXT | Nullable |
| created_at | TEXT | Default `datetime('now')` |

`create_expense` writes `date` in the same `YYYY-MM-DD` string format the rest of the codebase already reads — no new date convention introduced. `description` is optional and may be inserted as `NULL`/empty string when omitted.

---

## 5. Functions to Implement (`database/db.py`)

### A. `create_expense(user_id, amount, category, date, description)` — new

- `INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)`, fully parameterized — `user_id`, `amount`, `category`, `date`, and `description` all passed as bind params, never string-formatted into the SQL.
- Follows the same connection-open / try-finally-close pattern already used by every other write function in the module (e.g. `create_user`).
- Returns the new expense's `id` (via `cursor.lastrowid`), so the caller can confirm the insert succeeded if needed.
- Does **not** re-validate `amount`/`category`/`date` format — validation is the route's responsibility (§3, §12); this function trusts its caller, consistent with how `get_all_expenses(user_id, month=None)` trusts its caller not to pass a malformed `month`.

---

## 6. Changes to `app.py`

- Import `CATEGORIES` and `create_expense` from `database.db` (added to the existing `from database.db import (...)` block).
- Rewrite `add_expense()`:
  - Add `methods=["GET", "POST"]`.
  - Add the session guard (copied from `profile()`'s pattern).
  - On `GET`, render `expenses_add.html` with `categories=CATEGORIES` and empty form defaults.
  - On `POST`, validate `request.form` fields (§12); on failure, re-render the same template with `errors` and the submitted `form_values` in context so the user doesn't lose their input; on success, call `create_expense(...)` and `redirect(url_for("profile"))`.
- No change to any other route.

---

## 7. Files to Change

- `app.py` — `add_expense()` route only (§6), plus the import line.
- `database/db.py` — new `create_expense` function (§5).

---

## 8. Files to Create

- `templates/expenses_add.html` — extends `base.html`; form with `amount` (number input), `category` (`<select>` populated from `categories`), `date` (date input), `description` (optional text input); displays validation errors inline next to the offending field when present; submits via `POST` to `url_for('add_expense')`.
- `static/css/expenses_add.css` — page-specific styling for the new form, following the precedent set by `static/css/profile.css` (one CSS file per page, no inline `<style>` tags).

---

## 9. Dependencies

None. No new pip packages — form parsing uses Flask's built-in `request.form`; date/amount validation uses stdlib (`datetime.strptime`, `float()`/`try`-`except`), already available.

---

## 10. Rules for Implementation

- **Parameterized queries only**: `amount`, `category`, `date`, and `description` all come from untrusted form input — every value must go through a `?` placeholder in `create_expense`'s `INSERT`, never f-string-interpolated into SQL.
- **DB logic stays in `database/db.py`**: `add_expense()` in `app.py` only reads/validates `request.form` and calls `create_expense(...)` — it must not run SQL itself.
- **`url_for()` for every internal link**: the form's `action` must use `url_for('add_expense')`; the redirect on success must use `url_for('profile')`, not hardcoded paths.
- **Vanilla JS only, and none required here**: this feature ships with zero new JavaScript — plain HTML form + server-side validation only.
- **No new pip packages.**
- **One responsibility per route function**: `add_expense()` fetches/validates form data, calls one DB function, and renders/redirects — it doesn't grow extra responsibilities.
- **Never use raw string returns for stub routes once a step is implemented**: the current `return "Add expense — coming in Step 7"` must be fully replaced by `render_template`/`redirect` calls — no string ever returned from this route once this step ships.
- **Ownership**: the expense's `user_id` is always `session["user_id"]`, never a value read from the submitted form.
- Python: PEP 8, snake_case, consistent with the rest of `database/db.py` and `app.py`.

---

## 11. Expected Behavior

- Visiting `GET /expenses/add` while logged in: renders a form with an amount field, a category dropdown populated from the 7 fixed `CATEGORIES`, a date field, and an optional description field — all empty/default.
- Visiting `GET /expenses/add` while logged out: redirected to `/login`, identical to `/profile`'s existing guard.
- Submitting the form with valid values: a new row is inserted for the logged-in user, and the browser is redirected to `/profile`, where the new expense immediately appears in "Recent expenses" and "All expenses."
- Submitting the form with an invalid value (e.g. negative amount, unknown category, malformed date, missing required field): the same form re-renders with the previously entered values still filled in (except the invalid one, implementer's call) and a clear inline error message — no row is inserted, no redirect happens.
- Submitting the form with a valid but empty `description`: the expense is still inserted successfully; `description` is optional.

---

## 12. Error Handling Expectations

- **Missing/invalid `amount`**: not present, non-numeric, zero, or negative — all rejected with an inline error ("Amount must be a positive number"); no insert.
- **Missing/unknown `category`**: not present, or not one of the exact 7 values in `CATEGORIES` — rejected with an inline error; no insert. The `<select>` should make an unknown value hard to submit under normal use, but the server must still validate it (a form can be tampered with client-side).
- **Missing/invalid `date`**: not present, or doesn't parse as a valid calendar date (e.g. via `datetime.strptime(date, "%Y-%m-%d")`) — rejected with an inline error; no insert. A syntactically valid but future date is allowed (no rule in this codebase restricts expenses to past dates).
- **Missing required fields generally**: `amount`, `category`, and `date` are required; `description` is the only optional field.
- **Ownership**: the inserted `user_id` is always `session["user_id"]` — there is no field in the form for it, so there is no way to insert an expense on another user's behalf.
- **No session / logged out**: same guard as `/profile` — redirect to `/login` before any form processing happens, on both `GET` and `POST`.
- **Stale session** (`user_id` in session but no matching user row): `session.clear()` and redirect to `/login`, identical to `/profile`'s existing handling.

---

## 13. Definition of Done

- [ ]  `GET /expenses/add` while logged in renders a real form (amount, category dropdown from `CATEGORIES`, date, optional description) — the stub's raw string return is gone.
- [ ]  `GET /expenses/add` while logged out redirects to `/login`.
- [ ]  `POST /expenses/add` with fully valid data inserts a new expense row scoped to `session["user_id"]` and redirects to `/profile`.
- [ ]  `POST /expenses/add` with an invalid `amount` (missing, non-numeric, zero, or negative) is rejected with an inline error and no insert.
- [ ]  `POST /expenses/add` with an invalid/unknown `category` is rejected with an inline error and no insert.
- [ ]  `POST /expenses/add` with an invalid/missing `date` is rejected with an inline error and no insert.
- [ ]  `POST /expenses/add` with an empty `description` still succeeds (field is optional).
- [ ]  The newly created expense is never attributed to any user other than the one in `session["user_id"]`.
- [ ]  Form `action` and the success redirect both use `url_for()`, no hardcoded paths.
- [ ]  `create_expense`'s `INSERT` uses `?` placeholders — no f-strings in SQL.
- [ ]  No DB logic added inside `app.py`; no new pip packages; no new JS file/framework.
- [ ]  `/expenses/<id>/edit` and `/expenses/<id>/delete` stubs remain untouched.
