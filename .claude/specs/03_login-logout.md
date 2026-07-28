# Spec Document

## 1. Overview

Reference: see `CLAUDE.md` for full project architecture, code style, and tech constraints — this spec must stay consistent with it.

Implement real authentication for `/login` (currently GET-only, renders the form but never checks credentials) and the session teardown for `/logout` (currently a raw-string stub). Together these give the app its first working session: `POST /login` verifies email/password against the `users` table and starts a session; `GET /logout` ends it.

**⚠️ Step-number cross-check (mismatch found):** CLAUDE.md's "Implemented vs stub routes" table tags **only `/logout`** as `Stub — Step 3`. `/login` is listed as `Implemented — renders login.html`, but that only describes the existing GET-only form render — there is no POST handler, no credential check, and no session creation behind it today (verified in `app.py`: `@app.route("/login")` with no `methods=`, body is just `return render_template("login.html")`). Because `feature_name="login_logout"` bundles both, and logout cannot be meaningfully implemented without something to log out of (no session mechanism exists anywhere in the codebase — no `flask.session` import, no `SECRET_KEY`), this spec scopes Step 3 as: **build real login authentication (POST handling + session start) together with logout (session teardown)**, not logout alone. Flag this to the human maintainer if Step 3 was intended to be logout-only and login auth belongs to a separate, unwritten step.

**Scope decision:** on successful login, redirect to `/` (the `landing` route), not `/profile`. `/profile` is a Step 4 stub that only returns the placeholder string `"Profile page — coming in Step 4"` — it is not a usable "logged in home," so it is deliberately **not** used as a redirect target anywhere in this feature. On logout, redirect to `/login`. Additionally, both `/login` and `/register` guard against being visited while already logged in: if `session.get("user_id")` is set, either route immediately redirects to `/` regardless of HTTP method, rather than re-showing the auth form or (in `/register`'s case) letting an already-authenticated user create a second account. This guard is checked first, before any method-specific branching, in both routes.

**Also flagged, not fixed by choice:** `templates/login.html`'s form currently hardcodes `<form method="POST" action="/login">` instead of using `url_for('login')`, which already violates CLAUDE.md's "never hardcode URLs" rule. Since this feature is what makes the POST actually work, fixing that hardcoded action is in-scope (same precedent as the registration spec, which fixed a similar nit in its own template).

---

## 2. Depends on

- Step 1 (`database-setup`) — requires `get_db()` and the `users` table. Confirmed present in `database/db.py`.
- Step 2 (`registration`) — requires `create_user()` and `get_user_by_email()`, and that at least one user can exist with a `password_hash` set via `generate_password_hash`. Confirmed present in `database/db.py`.

---

## 3. Routes

### `POST /login` (extend the existing route, don't replace the GET behavior)

- Current state: `app.py` defines `@app.route("/login")` with no `methods=`, i.e. GET-only, body is `return render_template("login.html")`.
- Change the decorator to `methods=["GET", "POST"]`.
- Guard, checked first regardless of method: if a session already exists (`session.get("user_id")` is set), redirect to `url_for("landing")` (edge case: visiting or posting to `/login` while already logged in).
- On `GET` (and not already logged in): unchanged, render `login.html` with no error.
- On `POST` (and not already logged in):
  - Read `email`, `password` from `request.form`.
  - Validate (see §10 Rules / §11 Expected Behavior / §12 Error Handling below).
  - On validation failure or bad credentials: re-render `login.html` with `error=<message>` (matches the template's existing `{% if error %}` block — no template logic change needed, only the hardcoded form action).
  - On success: set `session["user_id"] = user["id"]`, then `redirect(url_for("landing"))`.

### `GET /register` (add an already-logged-in guard to the existing route)

- Current state: `app.py` defines `@app.route("/register", methods=["GET", "POST"])`, fully implemented per Step 2, with no session awareness (session didn't exist as a concept yet when that step was built).
- Add the same guard as `/login`, checked first regardless of method: if `session.get("user_id")` is set, redirect to `url_for("landing")` — an already-authenticated user should not see the registration form or be able to submit it to create a second account.
- All other registration validation/behavior from `02_registration.md` is unchanged.

### `GET /logout` (replace the raw-string stub)

- Current state: `@app.route("/logout")` returns the raw string `"Logout — coming in Step 3"` — this must not remain once this step is implemented (CLAUDE.md: "Never use raw string returns for stub routes once a step is implemented").
- New behavior: clear the session (`session.clear()`), then `redirect(url_for("login"))`.
- Idempotent: if there is no active session (already logged out, or never logged in), still succeeds and redirects to `/login` — no error.

No changes to `GET /profile` or any `/expenses/*` stub — those remain exactly as-is (per CLAUDE.md: never implement a stub route outside its assigned step).

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

Per CLAUDE.md ("Never put DB logic in route functions"), add one new helper — do not inline the lookup or password check in `app.py`.

### A. `authenticate_user(email, password)`

- Look up the user via the existing `get_user_by_email(email)` — do not duplicate that query.
- If no user found, return `None`.
- Compare `password` against the stored hash with `check_password_hash(user["password_hash"], password)` (from `werkzeug.security`, same module already used for `generate_password_hash` in `create_user`/`seed_db`).
- If the hash check fails, return `None`.
- On success, return the `sqlite3.Row` for the user (so the route can read `user["id"]`).
- Deliberately returns the same `None` for "no such email" and "wrong password" — the route must show one generic error for both (see §12), to avoid leaking which part of the credentials was wrong (user enumeration).

---

## 6. Changes to `app.py`

- Import `session` from `flask` (currently imports `Flask, render_template, request, redirect, url_for` — add `session`).
- Import `authenticate_user` from `database.db`.
- Set `app.secret_key` (or `app.config["SECRET_KEY"]`) — required for Flask to sign session cookies; without it, `session[...]` writes raise a `RuntimeError`. Nothing in the codebase sets this today. Use a fixed dev value for now (no secrets-management system exists yet in this project) — flag this as a follow-up for real deployment, not something this spec solves.
- Update `/login` route: add `methods=["GET", "POST"]`, the already-logged-in guard (checked before method branching), and the validate/authenticate/session/redirect logic on `POST` described in §3.
- Update `/register` route: add the same already-logged-in guard at the top of the function, before its existing method branching.
- Replace `/logout`'s raw-string stub body with `session.clear()` + `redirect(url_for("login"))`.
- All three routes stay single-responsibility per CLAUDE.md code style: guard/parse/validate → call db helper → set session → redirect/render. No SQL, no password comparison inline in `app.py`.

---

## 7. Files to Change

- `app.py` — imports, `/login` route (already-logged-in guard + POST handling), `/register` route (already-logged-in guard only), `/logout` route (replace stub)
- `database/db.py` — add `authenticate_user()`
- `templates/login.html` — fix hardcoded `action="/login"` to `action="{{ url_for('login') }}"`
- `templates/base.html` — nav currently always shows "Sign in" / "Get started" with no session awareness; add a conditional (`{% if session.get('user_id') %}` / `{% else %}`) so a logged-in user sees a "Logout" link (`url_for('logout')`) instead of "Sign in" / "Get started"

---

## 8. Files to Create

- None.

---

## 9. Dependencies

- No new pip packages. Uses `flask.session` (built into Flask, already in `requirements.txt`) and `werkzeug.security.check_password_hash` (same `werkzeug` dependency already used for `generate_password_hash`).

---

## 10. Rules for Implementation

- Route functions: one responsibility only (guard/parse/validate → call db helper → set session/render/redirect) — no DB logic or password comparison inline in `app.py`.
- DB queries: parameterized (`?`) only, never f-strings in SQL — `authenticate_user()` reuses `get_user_by_email()`'s existing parameterized query rather than writing a new one.
- Never hardcode URLs — use `url_for("login")` / `url_for("logout")` / `url_for("landing")` everywhere, including fixing `login.html`'s existing hardcoded `action="/login"`.
- Use `abort()` only for malformed/unexpected requests, not for ordinary validation/auth failures — bad credentials are expected user error and should re-render the form with `error`, not a hard HTTP error page.
- Never install new packages.
- Password comparison must go through `check_password_hash` — never compare plaintext, never compare against `password_hash` directly with `==`.
- Port stays 5001 — unrelated to this feature, but do not touch the `app.run(...)` call.
- No CSRF protection exists yet anywhere in this codebase (confirmed: no CSRF token field in `login.html` or `register.html`) — this feature does not introduce one either; consistent with current state, not a regression.

---

## 11. Expected Behavior

- `GET /login` while logged out — unchanged, renders the empty form.
- `GET /login` while already logged in — redirects straight to `/`, does not show the form again.
- `POST /login` while already logged in (e.g. a stale form resubmitted) — redirects to `/`, does not re-authenticate.
- `POST /login` with a valid, existing email + matching password — sets `session["user_id"]`, redirects to `/`.
- `POST /login` with an unknown email — re-renders `login.html` with a generic "Invalid email or password." error; no session set.
- `POST /login` with a known email but wrong password — re-renders `login.html` with the same generic "Invalid email or password." error (not "wrong password", to avoid confirming the email exists); no session set.
- `POST /login` with missing/empty `email` or `password` — re-renders with a "Email and password are required." validation error; no DB call attempted.
- `GET /register` while already logged in — redirects straight to `/`, does not show the signup form.
- `POST /register` while already logged in — redirects to `/`, does not create a second account.
- `GET /logout` while logged in — clears the session, redirects to `/login`.
- `GET /logout` while already logged out — still succeeds (no-op clear), redirects to `/login`; does not error or crash.

---

## 12. Error Handling Expectations

- Unknown email or wrong password → both return `None` from `authenticate_user()` → route shows one generic "Invalid email or password." form error, never distinguishing which field was wrong (user enumeration prevention).
- Empty/missing `email` or `password` in `request.form` → validated in the route before calling `authenticate_user()` → shown as a form error, not a `KeyError`/500.
- Missing `SECRET_KEY` → not a runtime scenario this spec needs to branch on; it's a startup precondition (`app.secret_key` set once at app creation in §6), not per-request error handling.
- Accessing `/logout` with no active session → must not raise (e.g. no `KeyError` from assuming `session["user_id"]` exists) — use `session.clear()` or `session.pop("user_id", None)`, both of which are safe when the key is absent.
- Any other unexpected DB error during lookup → let it propagate as a 500, consistent with "never use bare `return 'error string'`" — an unhandled exception surfaces as Flask's default error page, acceptable for truly unexpected failures.

---

## 13. Definition of Done

- [ ]  `POST /login` accepts form submissions (`methods=["GET", "POST"]`)
- [ ]  Valid credentials start a session (`session["user_id"]`) and redirect to `/`
- [ ]  Unknown email and wrong password both show the same generic error, no session set
- [ ]  Empty/missing email or password shows a validation error, no DB call attempted
- [ ]  `GET /login` while already logged in redirects to `/` instead of re-showing the form
- [ ]  `POST /login` while already logged in redirects to `/` instead of re-authenticating
- [ ]  `GET /register` while already logged in redirects to `/` instead of showing the signup form
- [ ]  `POST /register` while already logged in redirects to `/` instead of creating a second account
- [ ]  `GET /logout` clears the session and redirects to `/login`, with no raw-string stub remaining
- [ ]  `GET /logout` is safe (no crash) when there is no active session
- [ ]  `login.html`'s form action uses `url_for('login')` instead of the hardcoded `/login`
- [ ]  `base.html` nav shows "Logout" instead of "Sign in"/"Get started" when a session is active
- [ ]  No DB logic or password comparison added to `app.py` — all of it lives in `database/db.py`
- [ ]  All queries reuse existing parameterized helpers, no new raw SQL in `app.py`
- [ ]  No new pip packages added
- [ ]  `GET /profile`, `/expenses/*` stub routes remain untouched; `/profile` is not used as a redirect target anywhere
