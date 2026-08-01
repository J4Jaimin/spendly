# Spec Document

## 1. Overview

Reference: see `CLAUDE.md` for full project architecture, code style, and tech constraints — this spec must stay consistent with it.

Implement the "delete expense" feature: turn the existing `GET /expenses/<id>/delete` stub into a real flow that lets a logged-in user permanently remove one of their own expenses. You also need to add delete icon for delete expense. Today the route is a bare stub in `app.py` that returns the literal string `"Delete expense — coming in Step 9"` with no template, no confirmation, no session guard, and no DB interaction:

```python
@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"
```

This step adds `methods=["GET", "POST"]` to the route, a new `templates/expenses_delete.html` confirmation page, and a new `delete_expense(id, user_id)` helper in `database/db.py`. It reuses the session-guard and ownership-check-then-`abort(404)` pattern already proven by `edit_expense()` (spec 07) rather than inventing a new one.

**⚠️ Step-number cross-check (mismatch found):** this spec was requested as **"Step 8 — delete-expense-feature."** Per CLAUDE.md's "Implemented vs stub routes" table, **Step 8 is tagged to `GET /expenses/<id>/edit`** (already implemented, spec `07_edit-expense-feature.md`), while **`GET /expenses/<id>/delete` is explicitly tagged `Step 9`** — and the live stub's own body confirms this (`"Delete expense — coming in Step 9"`). So the *feature* requested here (delete-expense) does not match the *step number* requested (8); it matches Step 9. This is the same category of drift spec 07 already flagged for itself (filed as "07" while documenting Step 8 functionality). This spec is written for the functionality of the `Step 9` route (`GET/POST /expenses/<id>/delete`) despite being filed under the requested step number, per the `/create-spec` argument order. Flag this to the human maintainer to confirm whether this file should be renumbered `09_delete-expense-feature.md` to match CLAUDE.md, or whether the step numbering scheme was intentionally shifted. This spec does not edit CLAUDE.md itself.

**Also flagged, not fixed by choice:** CLAUDE.md still says `database/db.py` is currently empty and that `/logout`, `/profile`, `/expenses/add`, and `/expenses/<id>/edit` are stubs — all stale; `database/db.py` already has 17 functions implemented and all four of those routes are fully implemented (confirmed by reading the live files). This drift was already flagged by specs 05, 06, and 07 and is called out again here rather than silently corrected.

**Implementation approach — GET shows a confirmation page, POST performs the delete:** a raw `GET`-triggered delete is unsafe (browsers/crawlers can pre-fetch or re-request a `GET` URL, silently destroying data) and CLAUDE.md's own route table already lists this route the same nominal way `/expenses/<id>/edit` was listed before spec 07 gave it a `GET`+`POST` split. This spec follows that same precedent: `GET /expenses/<id>/edit` and `GET /expenses/<id>/delete` are the table's shorthand for "the route accessed via this GET URL," not a promise that no `POST` handling will be added. Concretely:
- **`GET`**: renders `expenses_delete.html`, a confirmation page showing the expense's date/category/amount/description and asking the user to confirm, with a `<form method="POST">` submitting back to the same URL and a "Cancel" link back to `/profile`. No data is touched.
- **`POST`**: performs the actual deletion via `delete_expense(id, user_id)`, then redirects to `/profile`.

This mirrors the plain-HTML-form, no-JS, no-AJAX approach already used by add-expense and edit-expense, and matches this codebase's "one responsibility per route" style — the same route function handles both "show" and "do," exactly like `edit_expense()` already does.

**Scope decision:** this step only implements `GET/POST /expenses/<id>/delete`, plus the minimum profile-page wiring needed to reach it (a delete icon-button next to the existing edit icon-button on each expense row). It does not touch the add-expense or edit-expense routes/templates beyond that addition.

---

## 2. Depends on

- Step 1 (`database-setup`) — requires the live `expenses` table schema, already defined in `database/db.py`. Confirmed present. The `expenses.user_id` foreign key has no `ON DELETE` clause (plain `FOREIGN KEY (user_id) REFERENCES users (id)`), but this is irrelevant here: `expenses` is the child table in that relationship and nothing else references `expenses.id`, so deleting an expense row triggers no cascade behavior to reason about.
- Step 4 (`create-profile-page`) — requires the session-guard-and-fetch pattern (`session.get("user_id")` → redirect to `login` if absent → `get_user_by_id` → `session.clear()` + redirect if stale) already used in `profile()`. This step reuses the identical pattern.
- Step 8 (`edit-expense-feature`, filed as spec `07`) — requires the exact ownership-check pattern already implemented in `edit_expense()`: fetch via `get_expense_by_id(id)`, and if the row doesn't exist **or** its `user_id` doesn't match `session["user_id"]`, `abort(404)` for both cases identically (never leak existence to a non-owner). This step reuses `get_expense_by_id` unchanged and applies the same check before either `GET` or `POST` proceeds.

---

## 3. Routes

### `GET/POST /expenses/<int:id>/delete` (replace the existing stub, don't add a second route)

- Current state: GET-only stub that returns a raw string. No form, no session guard, no DB interaction, no ownership check.
- New behavior:
  - Add `methods=["GET", "POST"]` to the route decorator.
  - Session guard identical to `profile()`/`edit_expense()`: if `session.get("user_id")` is absent, redirect to `url_for("login")`. If `get_user_by_id(session["user_id"])` returns `None` (stale session), `session.clear()` and redirect to `login`.
  - Fetch the target expense via `get_expense_by_id(id)` (already implemented, spec 07). If it does not exist, **or** its `user_id` does not match `session["user_id"]`, call `abort(404)` — identical to `edit_expense()`'s check, applied before branching on method so it covers both `GET` and `POST`.
  - **On `GET`**: render `expenses_delete.html` with the fetched `expense` in context (for the confirmation copy: date, category, amount, description). No DB mutation occurs on `GET`.
  - **On `POST`**: call `delete_expense(id, session["user_id"])` (§5), then `redirect(url_for("profile"))`. No form fields are read — nothing about the delete is user-editable, so there's no validation step and no error-re-render path (unlike add/edit).
  - The `user_id` used for both the ownership check and the delete call is always `session["user_id"]` — never taken from the form or URL beyond the `id` path parameter — so a user can only ever delete their own expenses.

No changes to `/login`, `/register`, `/logout`, `/profile`'s own logic, `/expenses/add`, or `/expenses/<id>/edit` — those remain exactly as-is, aside from `profile.html` gaining a delete link next to the existing edit link (§8).

---

## 4. Database Schema

No schema changes. Reuses the existing `expenses` table exactly as defined in `database/db.py`:

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | Primary key, autoincrement |
| user_id | INTEGER | Foreign key → users.id, not null |
| amount | REAL | Not null |
| category | TEXT | Not null |
| date | TEXT | Not null (`YYYY-MM-DD`) |
| description | TEXT | Nullable |
| created_at | TEXT | Default `datetime('now')` |

Deleting a row here has no cascade implications — no other table has a foreign key referencing `expenses.id`.

---

## 5. Functions to Implement (`database/db.py`)

### A. `delete_expense(id, user_id)` — new

- `DELETE FROM expenses WHERE id = ? AND user_id = ?`, fully parameterized.
- Includes `user_id` in the `WHERE` clause (not just `id`) as a defense-in-depth ownership check at the DB layer, mirroring `update_expense`'s `WHERE id = ? AND user_id = ?` pattern (spec 07) — even though the route already verified ownership via `get_expense_by_id` before calling this.
- Follows the same connection-open / try-finally-close pattern already used by every other write function in the module (e.g. `create_expense`, `update_expense`).
- Returns nothing — the route has already confirmed the row exists and is owned by the current user before calling this, consistent with `update_expense`'s own no-return-value precedent.
- No new read function is needed: `get_expense_by_id(id)` (already implemented) is reused as-is for both the ownership check and fetching the expense's details to show on the confirmation page.

---

## 6. Changes to `app.py`

- Add `delete_expense` (the new `database.db` function — note this collides in name with the existing route function `delete_expense(id)`; the DB function must be imported under its own name and the route must call it as `db.delete_expense(...)` or the import must alias it, e.g. `from database.db import (..., delete_expense as db_delete_expense)`, to avoid the route function shadowing the DB function it needs to call within its own body). **Implementer decision point, flagged explicitly**: pick either an import alias or a differently-named DB function (e.g. `remove_expense`) — CLAUDE.md doesn't mandate a specific resolution, but the route function and the DB function cannot share the bare name `delete_expense` in the same module without one shadowing the other.
- Rewrite `delete_expense(id)`:
  - Add `methods=["GET", "POST"]`.
  - Add the session guard (copied from `edit_expense()`'s pattern).
  - Fetch the expense via `get_expense_by_id(id)`; `abort(404)` if missing or not owned by `session["user_id"]`.
  - On `GET`, render `expenses_delete.html` with `expense=expense`.
  - On `POST`, call the delete DB function with `(id, session["user_id"])`, then `redirect(url_for("profile"))`.
- No change to any other route.

---

## 7. Files to Change

- `app.py` — `delete_expense()` route only (§6), plus the import line (with the naming resolution noted above).
- `database/db.py` — new delete function (§5).
- `templates/profile.html` — add a delete icon-button next to the existing edit icon-button inside the `.recent-actions` span, in both the "Recent expenses" and "All expenses" loops. Use the `trash` icon already defined in `templates/_icons.html` (`{{ icon('trash') }}`), matching the existing `{{ icon('pencil') }}` edit link's markup shape: `<a href="{{ url_for('delete_expense', id=expense.id) }}" aria-label="Delete expense">{{ icon('trash') }}</a>`. This link navigates to the confirmation page — it does not delete anything itself (no JS, no direct-POST link), consistent with §3's GET-shows/POST-does split.
- `static/css/profile.css` — `.recent-row`'s trailing grid column (currently `32px`, sized for exactly one action icon) needs to accommodate two icons side by side; either widen that column (e.g. to `64px`) or let `.recent-actions` (already `display: flex; justify-content: flex-end`) space both icons with a small `gap`. Add a hover style for the new delete link using the existing `--danger` token (e.g. `.recent-actions a.action-danger:hover { color: var(--danger); }`), so delete reads as destructive on hover while looking identical to edit at rest — consistent with how `--danger` is already used elsewhere in this codebase (e.g. `.stat-delta-up`).

---

## 8. Files to Create

- `templates/expenses_delete.html` — extends `base.html`; a confirmation page, not a form-with-fields page (no inputs to fill in). Structure: `page-section` > `page-container` > `page-header` (title "Delete expense") > a single `panel` card showing the expense's date/category/amount/description as read-only summary text (not editable inputs — this isn't `expenses_edit.html`'s field-per-row shape), a clear warning that this action is permanent, then a `<form method="POST" action="{{ url_for('delete_expense', id=expense.id) }}">` containing just a submit button styled as destructive (e.g. a new `.btn-danger` class, since none currently exists in the codebase) and a "Cancel" link (`url_for('profile')`, `.btn-ghost`) back to safety.
- `static/css/expenses_delete.css` — page-specific styling for the confirmation card and the new `.btn-danger` button, following the one-CSS-file-per-page precedent set by `expenses_add.css`/`expenses_edit.css`. `.btn-danger` should visually mirror `.btn-primary`'s shape/sizing but use `--danger`/`--danger-light` tokens instead of the ink/accent ones, so it reads as "the same kind of control, dangerous version" rather than a foreign element.

---

## 9. Dependencies

None. No new pip packages — this feature needs no numeric/date parsing at all (no form fields to validate), just Flask's `request.method` branching and the existing DB helpers.

---

## 10. Rules for Implementation

- **Parameterized queries only**: the delete function's `WHERE id = ? AND user_id = ?` must use `?` placeholders — never f-string-interpolated into SQL.
- **DB logic stays in `database/db.py`**: `delete_expense()` in `app.py` only performs the session guard, ownership check, and calls one DB function — it must not run SQL itself.
- **`url_for()` for every internal link**: the confirmation form's `action`, the profile-page delete link, and the Cancel link must all use `url_for()` — no hardcoded paths.
- **`abort()` for HTTP errors**: a missing or not-owned expense id uses `abort(404)`, not a raw string return or a redirect — identical to `edit_expense()`.
- **GET must not mutate state**: only the `POST` branch may call the delete function. A `GET` to this route — including a browser prefetch, a crawler, or a user simply refreshing the confirmation page — must never delete anything.
- **Vanilla JS only, and none required here**: this feature ships with zero new JavaScript — a plain HTML confirmation form, no `confirm()` dialog, no AJAX.
- **No new pip packages.**
- **One responsibility per route function**: `delete_expense()` checks ownership, then either renders the confirmation or performs the delete and redirects — it doesn't grow extra responsibilities.
- **Never use raw string returns for stub routes once a step is implemented**: the current `return "Delete expense — coming in Step 9"` must be fully replaced by `render_template`/`redirect`/`abort` calls.
- **Ownership**: the expense being deleted must belong to `session["user_id"]`, checked both in the route (via `get_expense_by_id` + comparison) and in the DB layer (via the delete function's `WHERE user_id = ?`). A user must never be able to delete another user's expense by guessing/incrementing an id.
- **Page-specific styles → new `.css` file**: `expenses_delete.css`, not an inline `<style>` block, and not stuffed into `profile.css`/`expenses_edit.css`.
- Python: PEP 8, snake_case, consistent with the rest of `database/db.py` and `app.py`.

---

## 11. Expected Behavior

- Visiting `GET /expenses/<id>/delete` while logged in, for an expense owned by the current user: renders a confirmation page showing that expense's details and a "Delete" button plus a "Cancel" link. Nothing is deleted yet.
- Visiting `GET /expenses/<id>/delete` while logged out: redirected to `/login`, identical to `/profile`'s and `/expenses/<id>/edit`'s existing guard.
- Visiting `GET /expenses/<id>/delete` for an id that doesn't exist, or that exists but belongs to a different user: `404`.
- Clicking "Cancel" on the confirmation page: returns to `/profile` with no DB change (a plain link, no `POST`).
- Submitting the confirmation form (`POST`): the expense row is permanently removed from the DB for the logged-in user, and the browser is redirected to `/profile`, where the deleted expense no longer appears in "Recent expenses" or "All expenses," and summary totals (expense count, total spent, category breakdown) reflect its removal.
- Re-submitting the same `POST` a second time (e.g. via browser back-button resubmit), or visiting the confirmation page again for the now-deleted id: `404`, since `get_expense_by_id` will return `None` — deletion is not silently idempotent-success, it's a hard 404 on the now-nonexistent id, consistent with how a nonexistent id is always handled elsewhere in this feature set.

---

## 12. Error Handling Expectations

- **No session / logged out**: same guard as `/profile` and `/expenses/<id>/edit` — redirect to `/login` before any confirmation rendering or deletion happens, on both `GET` and `POST`.
- **Stale session** (`user_id` in session but no matching user row): `session.clear()` and redirect to `/login`, identical to `/profile`'s existing handling.
- **Deleting a non-existent expense id**: `404` on both `GET` and `POST`.
- **Ownership — deleting another user's expense**: attempting to `GET` or `POST` `/expenses/<id>/delete` for an id owned by a different user returns `404`, not `403` — the app must not reveal that the id exists at all to a non-owner. Identical requirement to `edit_expense()`.
- **Double-delete / stale confirmation page**: `POST`ing to a delete URL for an id that was already deleted (e.g. two browser tabs, or a back-button resubmit after a successful delete) returns `404` on the second attempt, since the ownership-check-via-`get_expense_by_id` step now finds nothing — no special-cased "already deleted" message, same as the general nonexistent-id case.
- **`GET` must never delete**: even a repeated `GET` (refresh, browser prefetch, crawler) to the confirmation URL must be side-effect-free — this is the one CLAUDE.md-adjacent rule this feature adds beyond what add/edit needed, since add/edit's `GET` branches were already naturally read-only (rendering an empty/pre-filled form) but a *delete* confirmation page is the one place in this app where a naive GET-triggers-the-action implementation would be a real data-loss bug.

---

## 13. Definition of Done

- [ ]  `GET /expenses/<id>/delete` while logged in, for the user's own expense, renders a confirmation page showing that expense's details — the stub's raw string return is gone, and nothing is deleted by this request.
- [ ]  `GET /expenses/<id>/delete` while logged out redirects to `/login`.
- [ ]  `GET`/`POST /expenses/<id>/delete` for a non-existent id returns `404`.
- [ ]  `GET`/`POST /expenses/<id>/delete` for an id owned by a different user returns `404` (not `403`, not a leak of existence).
- [ ]  `POST /expenses/<id>/delete` for the user's own expense removes the row from the DB and redirects to `/profile`.
- [ ]  After a successful delete, the expense no longer appears in `/profile`'s "Recent expenses," "All expenses," or summary totals.
- [ ]  A second `POST`/`GET` to the same now-deleted id returns `404` (no crash, no silent no-op success).
- [ ]  An expense can never be deleted by a user other than the one who owns it, even via direct `POST` with a guessed id.
- [ ]  A plain `GET` to the confirmation page (including a repeated refresh) never deletes anything — only an explicit `POST` does.
- [ ]  "Cancel" on the confirmation page returns to `/profile` without deleting anything.
- [ ]  The delete function's `DELETE` statement uses `?` placeholders — no f-strings in SQL.
- [ ]  Profile page shows a delete icon-button next to the existing edit icon-button on every expense row (both "Recent expenses" and "All expenses"), using `url_for('delete_expense', id=...)`.
- [ ]  No DB logic added inside `app.py`; no new pip packages; no new JS file/framework.
- [ ]  `/expenses/add` and `/expenses/<id>/edit` remain functionally unchanged (aside from `profile.html`'s new delete link sitting next to the existing edit link).
