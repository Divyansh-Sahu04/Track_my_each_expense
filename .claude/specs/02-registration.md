# Spec: Registration

## Overview
This feature implements real user registration for Spendly. Currently `GET /register` only renders a static form (`register.html`) with no handler for submission. This step adds the `POST /register` route so a visitor can create an account: validate the submitted form, ensure the email isn't already taken, hash the password, insert the new user into the `users` table, start a logged-in session, and redirect to the profile page. This builds directly on the data layer from Step 1 and is a prerequisite for login (Step 3) and any authenticated page (profile, expenses).

## Depends on
- Step 1 — Database setup (`database/db.py`: `get_db()`, `init_db()`, `users` table with `id`, `name`, `email`, `password_hash`, `created_at`)

## Routes
- `GET /register` — renders the registration form — public (already implemented, unchanged)
- `POST /register` — validates input, creates the user, logs them in, redirects to `/profile` — public

## Database changes
No schema changes. `users` table already has everything needed (`name`, `email`, `password_hash`). This step only adds a query function to `database/db.py`:
- `create_user(name, email, password_hash)` — inserts a new row into `users`, returns the new user id
- `get_user_by_email(email)` — used to check for duplicate emails before insert

Both must use parameterized queries and live in `database/db.py`, never inline in `app.py`.

## Templates
- **Create:** none
- **Modify:** `templates/register.html` — no structural changes expected; the existing `{% if error %}` block already supports displaying validation/duplicate-email errors passed from the route. Only touch it if the route needs additional error context rendered.

## Files to change
- `app.py` — add `POST` to the `/register` route (or a second route mapping), form validation, duplicate-email check, password hashing, session creation, redirect
- `database/db.py` — add `create_user()` and `get_user_by_email()` helper functions

## Files to create
None.

## New dependencies
No new dependencies. Use `werkzeug.security.generate_password_hash` (already used in `seed_db()`) and Flask's built-in `session`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterized queries only — never f-strings in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash` before storage — never store plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validate required fields (name, email, password) server-side, not just via HTML `required` attributes
- Reject registration with a friendly error (re-rendered `register.html` with `error` set) if the email is already registered — rely on the `users.email UNIQUE` constraint as the backstop, but check with `get_user_by_email()` first for a clean error message
- On success, store the new user's id in `session` (e.g. `session["user_id"]`) and redirect with `url_for()` — do not hardcode `/profile`
- `/profile` is still a stub (Step 4) — redirecting there after registration is expected even though it currently returns placeholder text; do not implement `/profile` itself in this step

## Definition of done
- [ ] Submitting the register form with a new name/email/password creates a row in `users` with a hashed (not plaintext) password
- [ ] After successful registration, `session["user_id"]` is set and the browser is redirected away from `/register`
- [ ] Submitting with an email that already exists (e.g. `demo@spendly.com`) re-renders `register.html` with an error message and does not create a duplicate row
- [ ] Submitting with a missing field (empty name/email/password) re-renders `register.html` with an error instead of raising a server error
- [ ] No plaintext passwords appear anywhere in `expense_tracker.db`
- [ ] `app.py` still starts cleanly on port 5001 with no errors
- [ ] All new DB access goes through `database/db.py`, using `?` placeholders
