# Spec Document

## 1. Overview

Reference: see `CLAUDE.md` for full project architecture, code style, and tech constraints — this spec must stay consistent with it.

Implement the "edit expense" feature: turn the existing `GET /expenses/<id>/edit` stub into a real form that lets a logged-in user update one of their own existing expenses. Today the route is a bare stub (`app.py`) that returns the literal string `"Edit expense — coming in Step 8"` with no template, no form, and no POST handling:

```python
@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"
```

This step adds `methods=["GET", "POST"]` to the route, a new `templates/expenses_edit.html` form (amount, category, date, description — pre-filled with the expense's current values), a new `get_expense_by_id(id)` helper and a new `update_expense(...)` helper in `database/db.py`, and the same field validation used by add-expense, plus an ownership check that add-expense didn't need (add always creates a *new* row for the current user; edit must first prove the row being edited already belongs to them).

**⚠️ Step-number cross-check (mismatch found):** this spec was requested as **"Step 7 — edit-expense-feature."** Per CLAUDE.md's "Implemented vs stub routes" table, **Step 7 is tagged to `GET /expenses/add`** (already implemented, per spec `06_add-expense-feature.md`), while **`GET /expenses/<id>/edit` is explicitly tagged `Step 8`** — and `app.py`'s own stub body confirms this (`"Edit expense — coming in Step 8"`). So the *feature* requested here (edit-expense) does not match the *step number* requested (7); it matches Step 8. This spec is written for the functionality of the `Step 8` route (`GET/POST /expenses/<id>/edit`) despite being filed under the requested step number, per the `/create-spec` argument order. Flag this to the human maintainer to confirm whether this file should be renumbered `08_edit-expense-feature.md` to match CLAUDE.md, or whether the step number was intentionally reused. This spec does not edit CLAUDE.md itself.

**Also flagged, not fixed by choice:** CLAUDE.md still says `database/db.py` is currently empty and that `GET /expenses/add` is a stub — both are stale; `database/db.py` already has 15 functions implemented and `/expenses/add` is fully implemented (confirmed by reading the live files). This drift was already flagged by specs 05 and 06 and is called out again here rather than silently corrected.

**Scope decision:** this step only implements `GET/POST /expenses/<id>/edit`. It does **not** touch `GET /expenses/<id>/delete` — that remains an untouched stub tagged Step 9, per CLAUDE.md's rule against implementing a stub outside its assigned step.

**Implementation approach:** a plain HTML `POST` form on `templates/expenses_edit.html` (no client-side JS, no AJAX), mirroring `templates/expenses_add.html` but pre-filled with the expense's existing values and submitting back to `GET /expenses/<id>/edit`'s own URL. On successful validation and update, the route redirects to `GET /profile`. On validation failure, the route re-renders the same form with the submitted values preserved and inline error messages, exactly like add-expense's pattern.

---

## 2. Depends on

- Step 1 (`database-setup`) — requires the live `expenses` table schema and the `CATEGORIES` fixed list, both already defined in `database/db.py`. Confirmed present.
- Step 4 (`create-profile-page`) — requires the session-guard-and-fetch pattern (`session.get("user_id")` → redirect to `login` if absent → `get_user_by_id` → `session.clear()` + redirect if stale) already used in `profile()`. This step reuses the identical pattern.
- Step 7 (`add-expense-feature`) — requires the exact field-validation logic (`amount`, `category`, `date`, `description`) and the errors/`form_values` re-render pattern already implemented in `add_expense()` and `expenses_add.html`. This step reuses that logic rather than inventing a new validation scheme, so edit and add stay consistent.

---

## 3. Routes

### `GET/POST /expenses/<int:id>/edit` (replace the existing stub, don't add a second route)

- Current state: GET-only stub that returns a raw string. No form, no session guard, no DB interaction, no ownership check.
- New behavior:
  - Add `methods=["GET", "POST"]` to the route decorator.
  - Session guard identical to `profile()`: if `session.get("user_id")` is absent, redirect to `url_for("login")`. If `get_user_by_id(session["user_id"])` returns `None` (stale session), `session.clear()` and redirect to `login`.
  - Fetch the target expense via `get_expense_by_id(id)` (§5). If it does not exist, **or** its `user_id` does not match `session["user_id"]`, call `abort(404)` — both cases return the same 404 response so a logged-in user cannot distinguish "this id doesn't exist" from "this id belongs to someone else" (prevents expense-id enumeration/probing).
  - **On `GET`**: render `expenses_edit.html` with the fixed `CATEGORIES` list and `form_values` pre-filled from the fetched expense's current `amount`, `category`, `date`, `description`.
  - **On `POST`**: read `amount`, `category`, `date`, `description` from `request.form`. Validate each using the same rules as `add_expense()` (§12). If any validation fails, re-render `expenses_edit.html` with the submitted values echoed back and inline errors — do not update anything, do not redirect. If all fields are valid, call `update_expense(id, user_id, amount, category, date, description)` (§5), then `redirect(url_for("profile"))`.
  - The `user_id` used for both the ownership check and the update call is always `session["user_id"]` — never taken from the form or URL beyond the `id` path parameter — so a user can only ever edit their own expenses.

No changes to `/login`, `/register`, `/logout`, `/profile`, `/expenses/add`, or the `/expenses/<id>/delete` stub — those remain exactly as-is (per CLAUDE.md: never implement a stub route outside its assigned step).

---

## 4. Database Schema

No schema changes. Reuses the existing `expenses` table exactly as defined in `database/db.py`:

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | Primary key, autoincrement |
| user_id | INTEGER | Foreign key → users.id, not null |
| amount | REAL | Not null |
| category | TEXT | Not null |
| date | TEXT | Not null (`YYYY-MM-DD`, matching the format every existing read function already assumes) |
| description | TEXT | Nullable |
| created_at | TEXT | Default `datetime('now')` — untouched on edit; edit only updates `amount`, `category`, `date`, `description` |

---

## 5. Functions to Implement (`database/db.py`)

### A. `get_expense_by_id(id)` — new

- `SELECT * FROM expenses WHERE id = ?`, fully parameterized.
- Returns the row (as `sqlite3.Row`, consistent with every other read function in the module) or `None` if no row matches.
- Does **not** filter by `user_id` — ownership is checked by the caller (`edit_expense()` in `app.py`) by comparing the returned row's `user_id` against `session["user_id"]`, matching how the rest of the module keeps DB access generic and pushes authorization decisions to the route layer.

### B. `update_expense(id, user_id, amount, category, date, description)` — new

- `UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ? AND user_id = ?`, fully parameterized.
- Includes `user_id` in the `WHERE` clause (not just `id`) as a defense-in-depth ownership check at the DB layer, even though the route already verified ownership via `get_expense_by_id` — mirrors the "never trust a single layer" principle implied by CLAUDE.md's ownership rules.
- Follows the same connection-open / try-finally-close pattern already used by every other write function in the module (e.g. `create_expense`).
- Returns nothing (or the row count via `cursor.rowcount`, implementer's call) — the route has already confirmed the row exists and is owned by the current user before calling this, so a silent no-op on a mismatched `WHERE` should not normally occur.
- Does **not** re-validate `amount`/`category`/`date` format — validation is the route's responsibility (§3, §12), consistent with `create_expense`.

---

## 6. Changes to `app.py`

- Import `get_expense_by_id` and `update_expense` from `database.db` (added to the existing `from database.db import (...)` block).
- Import `abort` from `flask` (not currently imported, since no route uses it yet).
- Rewrite `edit_expense(id)`:
  - Add `methods=["GET", "POST"]`.
  - Add the session guard (copied from `profile()`'s pattern).
  - Fetch the expense via `get_expense_by_id(id)`; `abort(404)` if missing or not owned by `session["user_id"]`.
  - On `GET`, render `expenses_edit.html` with `categories=CATEGORIES` and `form_values` pre-filled from the fetched expense.
  - On `POST`, validate `request.form` fields (§12, identical rules to `add_expense`); on failure, re-render the same template with `errors` and the submitted `form_values`; on success, call `update_expense(...)` and `redirect(url_for("profile"))`.
- No change to any other route.

---

## 7. Files to Change

- `app.py` — `edit_expense()` route only (§6), plus the import line and the new `abort` import.
- `database/db.py` — new `get_expense_by_id` and `update_expense` functions (§5).

---

## 8. Files to Create

- `templates/expenses_edit.html` — extends `base.html`; same field set and structure as `expenses_add.html` (amount number input, category `<select>` populated from `categories`, date input, optional description input, inline validation errors), but form fields are pre-filled from `form_values` on `GET` (not empty) and the form submits via `POST` to `url_for('edit_expense', id=expense.id)` instead of `add_expense`.
- `static/css/expenses_edit.css` — page-specific styling for the edit form, following the precedent set by `static/css/expenses_add.css` (one CSS file per page, no inline `<style>` tags). Implementer may share the bulk of the layout rules with `expenses_add.css` since the two forms are visually near-identical, but per CLAUDE.md's architecture each page still gets its own CSS file rather than a shared inline `<style>` block.

---

## 9. Dependencies

None. No new pip packages — form parsing uses Flask's built-in `request.form`; date/amount validation uses stdlib (`datetime.strptime`, `float()`/`try`-`except`), already available and already used by `add_expense()`.

---

## 10. Rules for Implementation

- **Parameterized queries only**: `amount`, `category`, `date`, and `description` all come from untrusted form input — every value must go through a `?` placeholder in both `get_expense_by_id`'s `SELECT` and `update_expense`'s `UPDATE`, never f-string-interpolated into SQL.
- **DB logic stays in `database/db.py`**: `edit_expense()` in `app.py` only reads/validates `request.form`, calls `get_expense_by_id` and `update_expense`, and does the ownership comparison in Python — it must not run SQL itself.
- **`url_for()` for every internal link**: the form's `action` must use `url_for('edit_expense', id=...)`; the redirect on success must use `url_for('profile')`; the Cancel link must use `url_for('profile')` — no hardcoded paths.
- **`abort()` for HTTP errors**: a missing or not-owned expense id uses `abort(404)`, not a raw string return or a redirect.
- **Vanilla JS only, and none required here**: this feature ships with zero new JavaScript — plain HTML form + server-side validation only.
- **No new pip packages.**
- **One responsibility per route function**: `edit_expense()` fetches the expense, checks ownership, validates form data, calls one DB function, and renders/redirects — it doesn't grow extra responsibilities.
- **Never use raw string returns for stub routes once a step is implemented**: the current `return "Edit expense — coming in Step 8"` must be fully replaced by `render_template`/`redirect`/`abort` calls — no string ever returned from this route once this step ships.
- **Ownership**: the expense being edited must belong to `session["user_id"]`, checked both in the route (via `get_expense_by_id` + comparison) and in the DB layer (via `update_expense`'s `WHERE user_id = ?`). A user must never be able to edit another user's expense by guessing/incrementing an id.
- Python: PEP 8, snake_case, consistent with the rest of `database/db.py` and `app.py`.

---

## 11. Expected Behavior

- Visiting `GET /expenses/<id>/edit` while logged in, for an expense owned by the current user: renders a form pre-filled with that expense's current amount, category, date, and description.
- Visiting `GET /expenses/<id>/edit` while logged out: redirected to `/login`, identical to `/profile`'s existing guard.
- Visiting `GET /expenses/<id>/edit` for an id that doesn't exist, or that exists but belongs to a different user: `404`.
- Submitting the form with valid values: the existing row is updated in place (same `id`, same `created_at`) for the logged-in user, and the browser is redirected to `/profile`, where the updated values immediately appear.
- Submitting the form with an invalid value (e.g. negative amount, unknown category, malformed date): the same form re-renders with the previously entered values still filled in and a clear inline error message — no update happens, no redirect.
- Submitting the form with a valid but empty `description`: the update still succeeds; `description` is optional, same as add-expense.

---

## 12. Error Handling Expectations

- **Missing/invalid `amount`**: not present, non-numeric, zero, or negative — rejected with an inline error ("Amount must be a positive number"); no update. Identical rule to add-expense.
- **Missing/unknown `category`**: not present, or not one of the exact 7 values in `CATEGORIES` — rejected with an inline error; no update. The server must validate even though the `<select>` constrains normal use, since a form can be tampered with client-side.
- **Missing/invalid `date`**: not present, or doesn't parse as a valid calendar date (via `datetime.strptime(date, "%Y-%m-%d")`) — rejected with an inline error; no update.
- **Missing required fields generally**: `amount`, `category`, and `date` are required; `description` is the only optional field.
- **Ownership — editing another user's expense**: attempting to `GET` or `POST` `/expenses/<id>/edit` for an id owned by a different user returns `404`, not `403` — the app must not reveal that the id exists at all to a non-owner.
- **Editing a non-existent expense id**: `404`, same response as the ownership-mismatch case above (indistinguishable by design).
- **No session / logged out**: same guard as `/profile` and `/expenses/add` — redirect to `/login` before any form processing or ownership check happens, on both `GET` and `POST`.
- **Stale session** (`user_id` in session but no matching user row): `session.clear()` and redirect to `/login`, identical to `/profile`'s existing handling.

---

## 13. Definition of Done

- [ ]  `GET /expenses/<id>/edit` while logged in, for the user's own expense, renders a form pre-filled with that expense's current values — the stub's raw string return is gone.
- [ ]  `GET /expenses/<id>/edit` while logged out redirects to `/login`.
- [ ]  `GET`/`POST /expenses/<id>/edit` for a non-existent id returns `404`.
- [ ]  `GET`/`POST /expenses/<id>/edit` for an id owned by a different user returns `404` (not `403`, not a leak of existence).
- [ ]  `POST /expenses/<id>/edit` with fully valid data updates the existing row in place (same `id`) and redirects to `/profile`.
- [ ]  `POST /expenses/<id>/edit` with an invalid `amount` (missing, non-numeric, zero, or negative) is rejected with an inline error and no update.
- [ ]  `POST /expenses/<id>/edit` with an invalid/unknown `category` is rejected with an inline error and no update.
- [ ]  `POST /expenses/<id>/edit` with an invalid/missing `date` is rejected with an inline error and no update.
- [ ]  `POST /expenses/<id>/edit` with an empty `description` still succeeds (field is optional).
- [ ]  An expense can never be updated by a user other than the one who owns it, even via direct POST with a guessed id.
- [ ]  Form `action` and the success redirect both use `url_for()`, no hardcoded paths.
- [ ]  `get_expense_by_id`'s `SELECT` and `update_expense`'s `UPDATE` both use `?` placeholders — no f-strings in SQL.
- [ ]  No DB logic added inside `app.py`; no new pip packages; no new JS file/framework.
- [ ]  `/expenses/<id>/delete` stub remains untouched.
