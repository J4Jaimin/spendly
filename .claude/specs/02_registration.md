# Spec Document

## 1. Overview

Reference: see `CLAUDE.md` for full project architecture, code style, and tech constraints — this spec must stay consistent with it.

Implement the POST handling for `/register`: validate the signup form, hash the password, insert a new user row, and redirect to `/login` on success (re-rendering the form with an error on failure).

**⚠️ Step-number cross-check (mismatch found):** CLAUDE.md's "Implemented vs stub routes" table does **not** tag `/register` (or `/login`) with any step number — they are both listed only as `Implemented — renders <template>.html`, referring to the GET-only render that already exists. Explicit step tags in CLAUDE.md only cover Step 3 (`/logout`), Step 4 (`/profile`), Step 7–9 (`/expenses/*`). Step 1 is `database-setup` (see `.claude/specs/01_database-setup.md`). "Step 2" is not written down anywhere in CLAUDE.md — this spec assumes "Step 2" = completing registration, since it is the natural next step after Step 1 (database layer) and before Step 3 (logout), but **this is an inference, not a confirmed CLAUDE.md label**. Flag this to the human maintainer if that ordering assumption is wrong.

**Scope decision:** on success, registration redirects to `/login` — it does **not** start a session for the new user. No session/login-state mechanism exists anywhere in this codebase yet (`app.py` never imports or uses `flask.session`), and no step is currently designated for building it. Auto-login-after-signup is a reasonable alternative design, but building session infrastructure is arguably part of the (still unstepped) login feature, not registration. This is called out explicitly rather than silently assumed either way — revisit if the intended step ordering says otherwise.

---

## 2. Depends on

- Step 1 (`database-setup`) — requires `get_db()`, `init_db()`, and the `users` table to already exist. Confirmed present in `database/db.py`.

---

## 3. Routes

### `POST /register` (extend the existing route, don't replace the GET behavior)

- Current state: `app.py` defines `@app.route("/register")` with no `methods=`, i.e. GET-only, and the body is just `return render_template("register.html")`. No form validation, hashing, or DB logic exists.
- Change the decorator to `methods=["GET", "POST"]`.
- On `GET`: unchanged — render `register.html` with no error.
- On `POST`:
  - Read `name`, `email`, `password` from `request.form`.
  - Validate (see §11 Rules / §12 Expected Behavior / §13 Error Handling below).
  - On validation failure or DB conflict: re-render `register.html` with `error=<message>` (matches the template's existing `{% if error %}` block — no template change needed).
  - On success: insert the user, then `redirect(url_for("login"))`.

No changes to `GET /login`, `GET /logout`, `GET /profile`, or any `/expenses/*` stub — those remain exactly as-is (per CLAUDE.md: never implement a stub route outside its assigned step).

---

## 4. Database Schema

No schema changes. Reuses the existing `users` table exactly as defined in `database/db.py`:

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | Primary key, autoincrement |
| name | TEXT | Not null |
| email | TEXT | Unique, not null |
| password_hash | TEXT | Not null |
| created_at | TEXT | Default datetime('now') |

---

## 5. Functions to Implement (`database/db.py`)

Per CLAUDE.md ("Never put DB logic in route functions"), add a new helper — do not inline SQL in `app.py`.

### A. `create_user(name, email, password)`

- Hash `password` with `generate_password_hash` (already imported in `db.py`, same convention as `seed_db()`).
- Insert via `get_db()` using a parameterized query:
  ```sql
  INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)
  ```
- Wrap the insert in `try/except sqlite3.IntegrityError` to catch a duplicate `email` (UNIQUE constraint) and raise/return a distinguishable result (e.g. a custom exception or `None`) so the route can show "Email already registered" instead of a raw 500.
- Commit and close the connection in `try/finally`.
- Return the new user's `id` (via `cursor.lastrowid`) on success.

### B. `get_user_by_email(email)` (needed for a pre-check / future login step)

- `SELECT * FROM users WHERE email = ?`, parameterized.
- Returns a `sqlite3.Row` or `None`.
- Reused by this feature to give a clean "already registered" message before attempting the insert (defense in depth alongside the `IntegrityError` catch, since two requests could race).

---

## 6. Changes to `app.py`

- Import `request`, `redirect`, `url_for` from `flask` (only `Flask`, `render_template` are currently imported).
- Import `create_user`, `get_user_by_email` from `database.db`.
- Update `/register` route: add `methods=["GET", "POST"]` and the validation/insert/redirect logic described in §3.
- Route function stays single-responsibility per CLAUDE.md code style: parse form → validate → call `db` helper → render or redirect. No SQL, no hashing logic inline in `app.py`.

---

## 7. Files to Change

- `app.py` — `/register` route (imports + POST handling)
- `database/db.py` — add `create_user()` and `get_user_by_email()`

---

## 8. Files to Create

- None. `templates/register.html` already has the `{% if error %}` block this feature needs — no template change required, provided the error message is passed as `error=<str>` to `render_template`.

---

## 9. Dependencies

- No new pip packages. Uses `werkzeug.security.generate_password_hash` (already in `requirements.txt` via `werkzeug`) and Flask's built-in `request`/`redirect`/`url_for` (already in `requirements.txt` via `flask`).

---

## 10. Rules for Implementation

- Route functions: one responsibility only (fetch/validate → call db helper → render/redirect) — no DB logic inline in `app.py`.
- DB queries: parameterized (`?`) only, never f-strings in SQL.
- `PRAGMA foreign_keys = ON` is already enforced per-connection by `get_db()` — no action needed here since `users` has no FK.
- Never hardcode URLs — use `url_for("login")` for the redirect, not `"/login"` (note: `register.html`'s own `<form action="/register">` is currently hardcoded rather than using `url_for()`; fixing that is a template nit that's in-scope to correct while touching this feature, but is not required for POST handling to function).
- Use `abort()` (e.g. `abort(400)`) only for malformed/unexpected requests, not for ordinary validation failures — a bad email/password is expected user error and should re-render the form with `error`, not a hard HTTP error page.
- Never install new packages.
- Password hashing must go through `generate_password_hash` — never store or compare plaintext.

---

## 11. Expected Behavior

- `GET /register` — unchanged, renders the empty form.
- `POST /register` with valid, unique `name`/`email`/`password` — creates the user, redirects to `/login`.
- `POST /register` with a duplicate `email` — re-renders `register.html` with an "Email already registered" error; no new row inserted.
- `POST /register` with missing/empty `name`, `email`, or `password` — re-renders with a clear validation error; no DB call attempted.
- `POST /register` with a password shorter than 8 characters — re-renders with a validation error (the template's placeholder already implies an 8-char minimum, but nothing currently enforces it server-side; this feature is what makes that real, since HTML `required` alone doesn't enforce length and client-side JS is out of scope — vanilla-JS-only per CLAUDE.md, and adding it isn't necessary when server-side validation covers it).
- `POST /register` with a malformed email (no `@`, etc.) — re-renders with a validation error (basic format check; full RFC-5322 validation is out of scope).

---

## 12. Error Handling Expectations

- Duplicate email → caught as `sqlite3.IntegrityError` in `create_user()` (and/or pre-checked via `get_user_by_email()`) → shown as a form error, not a 500.
- Empty/missing `name`, `email`, or `password` in `request.form` → validated in the route before calling `create_user()` → shown as a form error, not a `KeyError`/500.
- Password too short (< 8 chars) → validated in the route → form error.
- Whitespace-only `name` (e.g. `"   "`) → strip and treat as empty → form error, matching the `NOT NULL` intent even though SQLite would happily store whitespace.
- Any other unexpected DB error → let it propagate as a 500 (no need to swallow errors that shouldn't happen), consistent with "never use bare `return 'error string'`" — an unhandled exception surfaces as Flask's default error page, which is acceptable for truly unexpected failures.
- Concurrent duplicate-email race (two simultaneous signups with the same email) → the `UNIQUE` constraint at the DB level is the actual source of truth and will reject the second insert even if the pre-check (`get_user_by_email`) raced past — `create_user()`'s `try/except sqlite3.IntegrityError` must still catch this, the pre-check alone is not sufficient.

---

## 13. Definition of Done

- [ ]  `POST /register` accepts form submissions (`methods=["GET", "POST"]`)
- [ ]  Valid signups insert a new row into `users` with a hashed password
- [ ]  Duplicate email is rejected with a user-facing form error, not a crash
- [ ]  Empty/missing fields are rejected with a user-facing form error
- [ ]  Password shorter than 8 characters is rejected with a user-facing form error
- [ ]  Successful registration redirects to `/login` via `url_for("login")`
- [ ]  No DB logic added to `app.py` — all SQL lives in `database/db.py`
- [ ]  All new queries are parameterized
- [ ]  No new pip packages added
- [ ]  `GET /register`, `/login`, `/logout`, `/profile`, `/expenses/*` stub routes remain untouched
