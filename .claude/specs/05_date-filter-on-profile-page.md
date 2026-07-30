# Spec Document

## 1. Overview

Reference: see `CLAUDE.md` for full project architecture, code style, and tech constraints — this spec must stay consistent with it.

Add a month filter to the **"All expenses"** panel on `/profile`. Today that panel (added after spec `04_create-profile-page.md` was written — see cross-check below) dumps a user's entire expense history in one unfiltered list via `get_all_expenses(user_id)`. This step adds an optional `?month=YYYY-MM` query param to `GET /profile`, a `<select>` control in the template to pick a month, and a new `database/db.py` helper to list which months actually have data — so the user can narrow that panel down to one calendar month at a time.

**⚠️ Step-number cross-check (mismatch found):** CLAUDE.md's "Implemented vs stub routes" table has **no entry tagged "Step 5"** at all — the table jumps `Step 3` (`/logout`) → `Step 4` (`/profile`) → `Step 7` (`/expenses/add`) → `Step 8` → `Step 9`. Steps 5 and 6 don't exist in CLAUDE.md today. This spec treats "Step 5 — date filter on profile page" as an inferred sub-feature that extends the already-implemented, Step-4-tagged `GET /profile` route, not as a new stubbed route of its own — there is no stub to "unstub." Flag this to the human maintainer if Step 5 was meant to name something else, or if CLAUDE.md's table should be updated to include it (this spec does not edit CLAUDE.md itself, per the rule below).

**Also flagged, not fixed by choice:** CLAUDE.md still says "`database/db.py` is currently empty" — it is not; it's fully implemented (confirmed by reading the live file). This is pre-existing CLAUDE.md drift, unrelated to this feature, called out here for the maintainer rather than silently corrected.

**Scope decision:** the filter applies **only** to the "All expenses" panel. The summary stat cards (expenses logged, total spent, average expense), the "This month so far" delta card, the "Spending by category" bars, the "Recent expenses" mini-list (top 3), and `top_category` all stay lifetime/unfiltered exactly as they are today. Filtering the whole page's aggregates was considered and rejected — those cards already have their own well-defined lifetime/this-month semantics (`get_expense_summary`, `get_category_breakdown`, `get_month_over_month_summary`), and conflating them with an ad-hoc filter would blur what each card means. This mirrors spec 04's precedent of drawing an explicit, narrow scope boundary rather than letting a feature creep across the whole page.

**Implementation approach:** a plain HTML `GET` form (`<select name="month">` + submit button) that reloads `/profile?month=YYYY-MM` — no client-side JS. `static/js/main.js` is currently empty and nothing on `/profile` runs client-side JS today; adding a fetch/AJAX filter or an auto-submit-on-change listener would be new client-side infrastructure this step doesn't need. A native form submission keeps the route's existing "GET, read query args, render" shape and needs zero new JS.

---

## 2. Depends on

- Step 4 (`create-profile-page`) — requires the live `GET /profile` route, `get_all_expenses(user_id)`, and the "All expenses" panel markup in `templates/profile.html`. Confirmed present in `app.py` and `templates/profile.html` (note: the live route already exceeds what spec 04 documented — it also has `all_expenses` and `month_summary`, which spec 04 never mentioned; this spec builds on the live code, not spec 04's original text).

---

## 3. Routes

### `GET /profile` (extend the existing route, don't replace it)

- Current state: `app.py`'s `profile()` takes no `request.args` at all and always fetches `get_all_expenses(user["id"])` unfiltered.
- New behavior, added only around the "All expenses" data fetch:
  - Read `month = request.args.get("month")` (optional).
  - Validate it matches `^\d{4}-\d{2}$` (e.g. `"2026-07"`). If missing or invalid, treat as **"All time"** — no filter applied, identical to today's behavior. Do not `abort()` on a malformed value; a bad/garbage query string on a read-only filter control should degrade gracefully to the unfiltered view, not error the whole page (same defensive spirit as spec 04's stale-session handling, applied to an even lower-stakes case).
  - Fetch `available_months = get_available_expense_months(user["id"])` (see §5) to populate the dropdown, scoped strictly to `session["user_id"]` — never another user's months.
  - Fetch `all_expenses = get_all_expenses(user["id"], month=month if month is valid and present else None)`.
  - Pass `selected_month` (the validated value, or `None` for "All time") and `available_months` into the template alongside the existing context.
- No other part of the route changes: the session guard, `get_expense_summary`, `get_category_breakdown`, `get_recent_expenses(limit=3)`, `get_month_over_month_summary`, and every other passed value stay exactly as they are today.

No changes to `/login`, `/register`, `/logout`, or any `/expenses/*` stub — those remain exactly as-is (per CLAUDE.md: never implement a stub route outside its assigned step).

---

## 4. Database Schema

No schema changes. Reuses the existing `expenses` table exactly as defined in `database/db.py`:

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | Primary key, autoincrement |
| user_id | INTEGER | Foreign key → users.id, not null |
| amount | REAL | Not null |
| category | TEXT | Not null |
| date | TEXT | Not null (`YYYY-MM-DD`, per existing `get_month_over_month_summary`'s `strftime('%Y-%m', date)` usage) |
| description | TEXT | Nullable |
| created_at | TEXT | Default `datetime('now')` |

Filtering follows the same `strftime('%Y-%m', date) = ?` pattern `get_month_over_month_summary` already uses — no new date-parsing convention introduced.

---

## 5. Functions to Implement (`database/db.py`)

### A. `get_available_expense_months(user_id)` — new

- `SELECT DISTINCT strftime('%Y-%m', date) AS month FROM expenses WHERE user_id = ? ORDER BY month DESC`, parameterized on `user_id`.
- Returns a list of dicts, newest month first: `{"value": "2026-07", "label": "July 2026"}` — `label` derived via `datetime.strptime(value, "%Y-%m").strftime("%B %Y")`.
- Empty list if the user has no expenses at all (template must handle this — see §12).

### B. `get_all_expenses(user_id, month=None)` — extend existing signature

- Current signature is `get_all_expenses(user_id)`, always `SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC, created_at DESC`.
- Add an optional `month=None` keyword param, default `None` so every existing caller (there's only the one, in `profile()`) keeps working unchanged if not passed.
- When `month` is given (already validated as `YYYY-MM` by the caller — this function does not re-validate format, it trusts its caller): add `AND strftime('%Y-%m', date) = ?` to the `WHERE` clause, parameterized — never string-format the month into the SQL.
- When `month` is `None`: identical query and result to today's unfiltered behavior.
- Return shape unchanged either way: list of `sqlite3.Row`.

---

## 6. Changes to `app.py`

- `profile()`: add the `request.args.get("month")` read, format validation (`re.fullmatch(r"\d{4}-\d{2}", month)` or equivalent), the `get_available_expense_months` call, and pass `month`/`None` into `get_all_expenses`. Pass `selected_month` and `available_months` into the `render_template("profile.html", ...)` call alongside the existing context values.
- No change to any other route.
- If a small helper is useful for turning a valid `month` string into a display label for the currently-selected option (e.g. reusing the same `"%Y-%m"` → `"%B %Y"` formatting as `get_available_expense_months`'s `label`), keep it a one-line local expression or reuse the label already present in `available_months` — don't introduce a new module-level helper for a single call site if it's not needed (`_format_inr`/`_format_display_date` exist because they're used across multiple template values already; this doesn't need a third one unless it turns out to be reused).

---

## 7. Files to Change

- `app.py` — `profile()` route only (§6).
- `database/db.py` — new `get_available_expense_months`, extended `get_all_expenses` (§5).
- `templates/profile.html` — add the month-filter form above the "All expenses" panel's list, and an empty-state message inside that panel for "valid month, zero expenses in it" (§12).
- `static/css/profile.css` — styling for the new filter form/select, matching the existing panel's visual style. No new CSS file — page-specific styles for `/profile` already live here.

---

## 8. Files to Create

None. This step only extends the existing profile page and its supporting files.

---

## 9. Dependencies

None. No new pip packages — `re` and `datetime` are already stdlib imports available in `app.py`/`database/db.py`.

---

## 10. Rules for Implementation

- **Parameterized queries only**: the `month` value comes directly from a query string (untrusted input) — it must always go through a `?` placeholder in `get_all_expenses` / `get_available_expense_months`, never be f-string-interpolated into SQL.
- **DB logic stays in `database/db.py`**: `profile()` in `app.py` only reads/validates `request.args` and calls the two functions above — it must not run SQL itself.
- **`url_for()` for every internal link**: the filter form's `action` must use `url_for('profile')`, not a hardcoded `/profile`.
- **Vanilla JS only, and none required here**: this feature ships with zero new JavaScript. If a future step wants auto-submit-on-change, that's separate scope, not this one.
- **No new pip packages.**
- **One responsibility per route function**: `profile()` still just fetches data and renders `profile.html` — validation of the `month` param is a small guard, not a second responsibility.
- Python: PEP 8, snake_case, consistent with the rest of `database/db.py` and `app.py`.

---

## 11. Expected Behavior

- Visiting `GET /profile` with no `month` param: identical to today — "All expenses" shows full history, dropdown (if rendered) shows "All time" selected.
- Visiting `GET /profile?month=2026-07` where the user has expenses in July 2026: "All expenses" panel shows only those rows, newest first; the dropdown reflects `July 2026` as selected; every other card/panel on the page is unchanged from the unfiltered view.
- Selecting a different month from the dropdown and submitting reloads `/profile?month=<value>` and shows that month's rows.
- A user with zero expenses overall: `available_months` is empty; the filter dropdown either isn't rendered or shows only a disabled "All time" option (implementer's call, but must not error) — same "No expenses yet" global empty state as today applies (the whole two-col layout, including the filter, only renders when `summary.count > 0`, unchanged from spec 04's existing `{% if summary.count == 0 %}` guard).

---

## 12. Error Handling Expectations

- **Malformed `month` param** (wrong format, garbage string, empty string after `?month=`): ignored, falls back to unfiltered "All time" — no `abort()`, no crash, page renders normally.
- **Well-formed `month` param with zero expenses in that month** (e.g. user hand-edits the URL to a month with no data, or all of that month's expenses were on a date range the user never actually spent in): "All expenses" panel shows a scoped inline empty message (e.g. "No expenses in July 2026") — this is a per-panel state, not the page-wide `summary.count == 0` empty state, since other cards still have lifetime data to show.
- **Ownership**: `get_available_expense_months` and the filtered `get_all_expenses` must both be scoped to `session["user_id"]` — never accept or leak another user's months/expenses regardless of what `month` value is requested.
- **No session / logged out**: unchanged — the existing guard at the top of `profile()` still redirects to `/login` before any of this filter logic runs.

---

## 13. Definition of Done

- [ ]  `GET /profile` with no `month` param behaves identically to the current unfiltered page.
- [ ]  `GET /profile?month=YYYY-MM` filters the "All expenses" panel to that month only; every other card/panel is unaffected.
- [ ]  `get_available_expense_months(user_id)` returns only the requesting user's distinct months, newest first, with a human-readable label.
- [ ]  `get_all_expenses(user_id, month=None)` is backward-compatible — the existing no-arg call site still works unchanged.
- [ ]  Malformed or garbage `month` values fall back to "All time" without erroring.
- [ ]  A valid month with zero expenses shows a scoped empty message inside the "All expenses" panel only.
- [ ]  Filter form uses `url_for('profile')`, not a hardcoded path.
- [ ]  All new/changed SQL uses `?` placeholders — no f-strings in SQL.
- [ ]  No new pip packages, no new JS file/framework, no DB logic added inside `app.py`.
- [ ]  Category breakdown, summary cards, "This month so far" delta, and "Recent expenses" (top 3) remain lifetime/unfiltered.
