# Spec Document

## 1. Overview

Reference: see `CLAUDE.md` for full project architecture, code style, and tech constraints — this spec must stay consistent with it.

Implement `GET /profile`, currently a raw-string stub (`return "Profile page — coming in Step 4"`). This step makes it a real, **view-only** page that shows the logged-in user's account info (name, email, member-since date) **plus a summary of their expense activity**: total spent, total expenses logged, a per-category breakdown (rendered as a simple chart), and a short list of recent expenses. It is the first route in the app that requires an active session to view — no route today gates access behind login (the only existing session checks are the *inverse*: `/login` and `/register` redirect *away* if a session already exists).

**Step-number cross-check (match):** CLAUDE.md's "Implemented vs stub routes" table tags `GET /profile` as `Stub — Step 4`, and the feature name (`create profile page`) matches this route directly. No mismatch.

**Scope decision:** this is read-only — no edit form, no mutation of the `users` row or any `expenses` row. CLAUDE.md's route table has no separate "edit profile" step, so name/email/password editing stays out of scope. The expense data shown here is derived (read-only aggregates over the existing `expenses` table); nothing here duplicates or replaces the future `/expenses/add|edit|delete` steps.

**Charting constraint:** CLAUDE.md mandates "Vanilla JS only" and "No new pip packages" — this extends to not pulling in any JS charting library (Chart.js, D3, etc.), whether via a CDN `<script>` tag or otherwise, since that's exactly the kind of external frontend dependency the project explicitly avoids. The category breakdown "chart" must be built as plain HTML/CSS — a horizontal bar per category, with bar width set from a percentage computed server-side (Python/Jinja), no canvas, no SVG library, no JS chart rendering. `static/js/main.js` doesn't need to grow for this — the bars are pure CSS width values rendered into the template.

**Also flagged, not fixed by choice:** `database/db.py`'s `get_user_by_email()` returns every column, including `password_hash`, via `SELECT *`. This spec's new `get_user_by_id()` will have the same shape for consistency with the existing helper, but the route/template layer must never expose `password_hash` — templates only ever read `user.name`, `user.email`, `user.created_at`.

---

## 2. Depends on

- Step 1 (`database-setup`) — requires `get_db()`, the `users` table, and the `expenses` table. Confirmed present in `database/db.py`.
- Step 3 (`login-logout`) — requires `session["user_id"]` to be set on login and cleared on logout. Confirmed present in `app.py`'s `/login` and `/logout` routes.

---

## 3. Routes

### `GET /profile` (replace the raw-string stub)

- Current state: `app.py` defines `@app.route("/profile")` with body `return "Profile page — coming in Step 4"` — must not remain once this step is implemented (CLAUDE.md: "Never use raw string returns for stub routes once a step is implemented").
- Guard, checked first: if `session.get("user_id")` is not set (no active session), redirect to `url_for("login")`. This is the first route in the codebase requiring login — there is no existing `@login_required`-style decorator to reuse, and introducing one for a single route would be premature abstraction (CLAUDE.md: don't design for hypothetical future requirements). Use an inline check, consistent with how `/login` and `/register` already do inline `session.get("user_id")` checks (just gating the opposite direction).
- If logged in, fetch the user via `get_user_by_id(session["user_id"])`.
  - Edge case: session references a `user_id` that no longer exists in `users` (row deleted out from under an active session — not reachable via any route in this app today, but the lookup can still return `None` and must be handled defensively). If `None`, clear the stale session (`session.clear()`) and redirect to `url_for("login")`, same as an unauthenticated visit.
- Also fetch, for the same `user_id`:
  - `get_expense_summary(user_id)` — total count and total amount spent.
  - `get_category_breakdown(user_id)` — per-category totals across all 7 fixed `CATEGORIES`, with a percentage-of-total already computed for bar widths.
  - `get_recent_expenses(user_id, limit=5)` — the 5 most recent expenses.
- Render `profile.html` passing `user`, `summary`, `categories`, and `recent_expenses`.

No changes to `/login`, `/register`, `/logout`, or any `/expenses/*` stub — those remain exactly as-is (per CLAUDE.md: never implement a stub route outside its assigned step). This route only *reads* `expenses`; it does not add any way to create/edit/delete one.

---

## 4. Database Schema

No schema changes. Reuses the existing `users` and `expenses` tables exactly as defined in `database/db.py`:

**users**

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | Primary key, autoincrement |
| name | TEXT | Not null |
| email | TEXT | Unique, not null |
| password_hash | TEXT | Not null |
| created_at | TEXT | Default datetime('now') |

**expenses**

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | Primary key, autoincrement |
| user_id | INTEGER | Not null, FK → users(id) |
| amount | REAL | Not null |
| category | TEXT | Not null |
| date | TEXT | Not null (YYYY-MM-DD) |
| description | TEXT | |
| created_at | TEXT | Default datetime('now') |

---

## 5. Functions to Implement (`database/db.py`)

Per CLAUDE.md ("Never put DB logic in route functions"), add these helpers — do not inline any lookup, aggregation, or sorting in `app.py`.

### A. `get_user_by_id(user_id)`

- Confirmed this does not exist yet — the only existing lookup helper is `get_user_by_email(email)`, and `session["user_id"]` stores the numeric primary key, not an email.
- Mirror `get_user_by_email()`'s shape exactly: open a connection via `get_db()`, run `SELECT * FROM users WHERE id = ?` with the id as a parameterized value, `.fetchone()`, close the connection in `finally`.
- Return the `sqlite3.Row` if found, or `None` if no such id.

### B. `get_expense_summary(user_id)`

- Run one parameterized aggregate query: `SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ?`.
- `COALESCE(..., 0)` matters: `SUM()` over zero rows returns SQL `NULL`, not `0` — without it, a brand-new user with no expenses would get `total = None` and crash any template arithmetic/formatting downstream.
- Return a dict (or the `sqlite3.Row`) with `count` and `total`.

### C. `get_category_breakdown(user_id)`

- Run one parameterized query grouping the user's expenses by category: `SELECT category, COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ? GROUP BY category`.
- The result only contains categories the user has actually spent in — but the fixed `CATEGORIES` list (already defined in `database/db.py`) has 7 entries, and the chart should show all 7 (some at 0), not just the ones with data, so the breakdown looks consistent between users. Zero-fill: build a dict from the query result, then iterate `CATEGORIES` and default missing ones to `0`.
- Compute each category's percentage of the user's total spend for bar width: `percentage = (category_total / grand_total * 100) if grand_total > 0 else 0`. Guard the division — a user with zero expenses has `grand_total == 0`, and dividing by it must not raise `ZeroDivisionError`.
- Return a list of dicts, one per category, each with `category`, `total`, and `percentage`, sorted by `total` descending (highest spend shown first).

### D. `get_recent_expenses(user_id, limit=5)`

- Run one parameterized query: `SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC, created_at DESC LIMIT ?`, passing both `user_id` and `limit` as parameters (never string-format the limit into the query).
- Return the list of matching rows (0 to `limit` rows, in reverse-chronological order).

---

## 6. Changes to `app.py`

- Import `get_user_by_id`, `get_expense_summary`, `get_category_breakdown`, and `get_recent_expenses` from `database.db` (extend the existing `from database.db import ...` line).
- Replace `/profile`'s raw-string stub body with: the not-logged-in guard → `get_user_by_id` lookup → stale-session guard → fetch summary/breakdown/recent → `render_template("profile.html", user=user, summary=summary, categories=categories, recent_expenses=recent_expenses)`.
- Route stays single-responsibility per CLAUDE.md code style: guard → fetch (four small calls, each doing one thing) → render. No SQL, no aggregation, no percentage math inline in `app.py` — all of that lives in `database/db.py`.

---

## 7. Files to Change

- `app.py` — import the four new functions, replace `/profile` route body
- `database/db.py` — add `get_user_by_id()`, `get_expense_summary()`, `get_category_breakdown()`, `get_recent_expenses()`
- `templates/base.html` — nav currently shows a "Logout" link when `session.get('user_id')` is set, but no "Profile" link anywhere; add `<a href="{{ url_for('profile') }}">Profile</a>` inside the existing `{% if session.get('user_id') %}` block, alongside "Logout"

---

## 8. Files to Create

- `templates/profile.html` — extends `base.html`. Sections:
  - Account info: `user.name`, `user.email`, `user.created_at` (labeled "Member since").
  - Summary: `summary.count` expenses logged, `summary.total` total spent (format as currency, e.g. `₹{{ "%.2f"|format(summary.total) }}`).
  - Category breakdown: one horizontal bar per entry in `categories`, bar width via inline `style="width: {{ category.percentage }}%"`, label showing category name and its total; empty state ("No expenses yet") shown instead when `summary.count == 0`.
  - Recent expenses: a simple list/table of `recent_expenses` (date, category, amount, description); empty state ("No expenses yet") shown when the list is empty.
  - No form, no inputs anywhere on this page — strictly read-only.
- `static/css/profile.css` — page-specific styles per CLAUDE.md ("Page-specific styles → new `.css` file, not inline `<style>` tags"), linked from `profile.html`'s `{% block head %}`. Includes the bar-chart styling (container + fill width driven by the inline `style` percentage from the template, colors/labels from CSS).

---

## 9. Dependencies

- No new pip packages, no new JS packages, no CDN-hosted charting library. Uses only `flask.session` (already imported in `app.py`), the existing `sqlite3`/`get_db()` machinery in `database/db.py`, and plain CSS for the bar chart.

---

## 10. Rules for Implementation

- Route functions: one responsibility only (guard → fetch → render) — no DB logic, aggregation, or percentage math inline in `app.py`.
- DB queries: parameterized (`?`) only, never f-strings in SQL — this applies to the new aggregate/group-by/limit queries just as much as the existing lookups.
- Never hardcode URLs — use `url_for("profile")` in `base.html`'s new nav link, and any internal links inside `profile.html`.
- `profile.html` must extend `base.html` (CLAUDE.md: "all templates must extend this").
- Page-specific styles go in a new `static/css/profile.css`, not inline `<style>` tags.
- No JS charting library, no CDN script tags, no npm packages — the category chart is CSS bars with server-computed percentages, matching "Vanilla JS only" / "No new pip packages".
- Never use raw string returns for `/profile` once implemented.
- Never install new packages.
- Port stays 5001 — unrelated to this feature, don't touch `app.run(...)`.
- No CSRF protection exists yet anywhere in this codebase — irrelevant here since this page has no form/mutation, consistent with current state.
- Never expose `password_hash` to the template — `profile.html` only reads `user.name`, `user.email`, `user.created_at`.
- Guard all division (percentage calculation) against a zero grand total — a user with no expenses must not crash the page.

---

## 11. Expected Behavior

- `GET /profile` while logged out — redirects to `/login`, does not render any profile content.
- `GET /profile` while logged in with a valid session and existing expenses — renders `profile.html` showing name/email/member-since, total count + total spent, a 7-category bar breakdown sorted highest-spend-first, and the 5 most recent expenses.
- `GET /profile` while logged in with **zero** expenses (e.g. a brand-new registrant who hasn't added any yet) — renders the same page with `summary.count == 0`, `summary.total == 0`, all 7 categories shown at 0%/₹0, and an empty-state message in place of the recent-expenses list. Must not crash (no `ZeroDivisionError`, no `NoneType` formatting error from an unguarded `SUM()`).
- `GET /profile` with a session `user_id` that no longer matches any row in `users` — clears the session and redirects to `/login`, same as the logged-out case (no crash, no 500).
- Nav bar: a logged-in user now sees both "Profile" and "Logout" links; a logged-out user sees "Sign in" / "Get started" as before (unchanged).

---

## 12. Error Handling Expectations

- No active session (`session.get("user_id")` is falsy) → redirect to `url_for("login")`, not `abort(401)` — matches the existing UX pattern in this app of redirecting rather than showing hard HTTP error pages for auth gating.
- Session references a non-existent user id → `get_user_by_id()` returns `None` → route clears the session and redirects to `/login`, rather than raising (e.g. indexing a `None` row) or rendering a template with missing data.
- Zero expenses for the user → `get_expense_summary()`'s `COALESCE(SUM(amount), 0)` prevents `total` from ever being SQL `NULL`/Python `None`; `get_category_breakdown()`'s percentage calc is guarded against division by zero; `get_recent_expenses()` simply returns an empty list, which the template renders as an empty state, not an error.
- Any other unexpected DB error during lookup/aggregation → let it propagate as a 500, consistent with "never use bare `return 'error string'`" — an unhandled exception surfaces as Flask's default error page, acceptable for truly unexpected failures.

---

## 13. Definition of Done

- [ ]  `GET /profile` while logged out redirects to `/login`, no raw-string stub remains
- [ ]  `GET /profile` while logged in renders `profile.html` with the current user's name, email, and member-since date
- [ ]  Profile page shows total expenses logged and total amount spent (`get_expense_summary`)
- [ ]  Profile page shows a per-category breakdown across all 7 fixed categories as CSS bars sized by percentage of total spend (`get_category_breakdown`), sorted highest-spend-first
- [ ]  Profile page shows the 5 most recent expenses (`get_recent_expenses`), newest first
- [ ]  A user with zero expenses sees a working empty state (0%/₹0 bars, "No expenses yet" message) with no crash
- [ ]  `GET /profile` with a stale/invalid session `user_id` clears the session and redirects to `/login` without crashing
- [ ]  `get_user_by_id()`, `get_expense_summary()`, `get_category_breakdown()`, `get_recent_expenses()` all added to `database/db.py`, each using parameterized queries
- [ ]  `profile.html` extends `base.html` and contains no inline `<style>` tags
- [ ]  `static/css/profile.css` created for page-specific styles, including the bar-chart styling
- [ ]  No JS charting library or CDN script added — category chart is pure CSS bars
- [ ]  `base.html` nav shows a "Profile" link (via `url_for('profile')`) alongside "Logout" when a session is active
- [ ]  `password_hash` is never passed into `profile.html`'s rendered output
- [ ]  No DB logic, aggregation, or percentage math added to `app.py` — all of it lives in `database/db.py`
- [ ]  No new pip packages added
- [ ]  `/login`, `/register`, `/logout`, and all `/expenses/*` stub routes remain untouched
