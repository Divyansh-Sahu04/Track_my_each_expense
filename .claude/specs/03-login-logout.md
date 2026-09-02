# Spec: Login and Logout

## Overview
This feature implements real authentication for Spendly. Currently `GET /login` only renders a static form (`login.html`) with no handler for submission, and `GET /logout` is a placeholder that returns raw text. This step adds the `POST /login` route so a registered user can sign in (look up their account by email, verify the password against the stored hash, and start a logged-in session), and implements `GET /logout` to clear the session and return the user to the landing page. This builds directly on the `users` table and helpers from Step 1 and the session pattern established in Step 2 (registration), and is a prerequisite for any authenticated page (profile, expenses).

## Depends on
- Step 1 — Database setup (`database/db.py`: `get_db()`, `init_db()`, `users` table with `id`, `name`, `email`, `password_hash`, `created_at`)
- Step 2 — Registration (`create_user()`, `get_user_by_email()` in `database/db.py`; the `session["user_id"]` pattern established in `POST /register`)

## Routes
- `GET /login` — renders the login form — public (already implemented, unchanged)
- `POST /login` — validates credentials, starts the session, redirects to `/profile` — public
- `GET /logout` — clears the session, redirects to `/` — logged-in (currently a stub returning raw text; this step replaces it with a real implementation)

## Database changes
No schema changes and no new query functions. `get_user_by_email(email)` (already added in Step 2) is sufficient to look up the user for password verification.

## Templates
- **Create:** none
- **Modify:** `templates/login.html` — no structural changes expected; add an `{% if error %}` block matching the pattern already used in `register.html`, since the route needs to render an invalid-credentials error.

## Files to change
- `app.py` — add `POST` to the `/login` route (or a second route mapping) with form validation, user lookup, password verification via `werkzeug.security.check_password_hash`, session creation, and redirect; replace the stub `GET /logout` with a real implementation that clears the session and redirects
- `templates/login.html` — add error-message display block

## Files to create
None.

## New dependencies
No new dependencies. Use `werkzeug.security.check_password_hash` (pairs with `generate_password_hash`, already imported in `app.py`) and Flask's built-in `session`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterized queries only — never f-strings in SQL
- Passwords hashed with `werkzeug.security` — verify with `check_password_hash`, never compare plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validate required fields (email, password) server-side, not just via HTML `required` attributes
- On failed login (unknown email or wrong password), re-render `login.html` with a single generic error (e.g. "Invalid email or password") — do not reveal whether the email exists, to avoid leaking account existence
- On success, store the user's id in `session` (e.g. `session["user_id"]`) and redirect with `url_for()` — do not hardcode `/profile`
- `GET /logout` must use `session.clear()` (or remove `user_id` specifically) and redirect with `url_for("landing")` — do not hardcode `/`
- `/profile` is still a stub (Step 4) — redirecting there after login is expected even though it currently returns placeholder text; do not implement `/profile` itself in this step
- Do not add login-required route protection/decorators to other stub routes in this step — that belongs to the steps that implement those routes

## Definition of done
- [ ] Submitting the login form with the seeded demo account (`demo@spendly.com` / `demo123`) sets `session["user_id"]` and redirects away from `/login`
- [ ] Submitting the login form with a correct email but wrong password re-renders `login.html` with an error and does not set the session
- [ ] Submitting the login form with an email that doesn't exist re-renders `login.html` with the same generic error (no distinction from a wrong password)
- [ ] Submitting with a missing field (empty email/password) re-renders `login.html` with an error instead of raising a server error
- [ ] Visiting `/logout` after logging in clears the session and redirects to `/`
- [ ] Visiting `/logout` when not logged in does not raise a server error
- [ ] `app.py` still starts cleanly on port 5001 with no errors
- [ ] All DB access goes through `database/db.py`, using `?` placeholders
