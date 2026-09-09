# Spec: Add Profile Photo

## Overview
Spendly's profile page currently renders a text avatar built from the user's
initials (`current_user['name'][:2] | upper`). This feature lets a logged-in
user upload a real profile photo that replaces that initials avatar across
the app. It builds on the existing profile page and session-based auth, and
is the first feature to introduce file uploads to Spendly.

## Depends on
- Step 3 (Login/Logout) — requires session-based auth to identify the user
- Step 5 (Profile Page Backend) — requires `profile.html` and the
  `current_user` context processor

## Routes
- `GET /profile/photo` — render a dedicated upload/change-photo form — logged-in
- `POST /profile/photo` — accept an uploaded image file, validate it, store it,
  and update the user's `photo_filename` — logged-in
- `POST /profile/photo/remove` — delete the current photo and revert to the
  initials avatar — logged-in

## Database changes
`database/db.py` currently defines only `users` and `expenses` (verified by
reading `init_db()`). This feature adds one column:

- `users.photo_filename TEXT` — nullable; stores the stored filename (e.g.
  `3.jpg`) of the user's uploaded photo, or `NULL` if none has been uploaded.

Add this column to the `CREATE TABLE IF NOT EXISTS users` statement in
`init_db()`. No migration script is needed since the table is created fresh
via `CREATE TABLE IF NOT EXISTS` in this project's dev workflow.

## Templates
- **Create:** `templates/profile_photo.html` — extends `base.html`; shows the
  current avatar (photo or initials), a file input, an "Upload" button, and
  (when a photo already exists) a "Remove photo" button.
- **Modify:** `templates/profile.html` — replace the hardcoded initials
  `<div class="profile-avatar">` with logic that renders
  `<img>` when `current_user['photo_filename']` is set, falling back to the
  initials div otherwise. Add a small "Change photo" link pointing to
  `url_for('profile_photo')`.
- **Modify:** `templates/base.html` — the initials-based logic in the navbar
  is not currently avatar-based (it shows a text welcome message), so no
  change is required there.

## Files to change
- `database/db.py` — add `photo_filename` column to `users` table schema
- `app.py` — add the three new routes and file-validation helper
- `templates/profile.html` — swap in conditional avatar rendering
- `static/css/style.css` or a new `profile.css` — style for `<img>` avatar
  (circular, fixed size) so it visually matches the existing initials avatar

## Files to create
- `templates/profile_photo.html` — upload/change photo page
- `static/css/profile_photo.css` — page-specific styles (upload form, preview)
- `static/uploads/profile_photos/` — directory where uploaded images are
  stored (created at runtime if missing; add a `.gitkeep` so the empty dir is
  tracked, and add `static/uploads/profile_photos/*` to `.gitignore` so
  uploaded files themselves are not committed)

## New dependencies
No new dependencies. File upload handling uses Flask's built-in
`request.files` and Werkzeug's built-in `secure_filename` — both already
available via the existing Flask/Werkzeug install in `requirements.txt`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only (`?` placeholders) — never f-strings in SQL
- Passwords hashed with werkzeug (unaffected by this feature, but do not
  regress existing password handling)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All DB logic (reading/writing `photo_filename`) belongs in
  `database/db.py`, never inline in `app.py` routes
- Validate uploaded files server-side: allow only `.jpg`, `.jpeg`, `.png`
  extensions and a max file size (e.g. 2 MB); reject anything else with a
  flashed error and re-render the upload form — never trust the client
  `Content-Type` header alone
- Always run uploaded filenames through `werkzeug.utils.secure_filename`,
  and generate the stored filename server-side (e.g. `f"user_{user_id}.<ext>"`)
  rather than trusting the client-supplied filename directly, to prevent
  path traversal and filename collisions
- Use `abort()` for HTTP errors (e.g. unauthenticated access), not bare
  `return "error string"`
- Keep the upload directory (`static/uploads/profile_photos/`) inside
  `static/` so uploaded images can be served via `url_for('static', ...)`
  without a custom file-serving route

## Definition of done
- [ ] Visiting `/profile/photo` while logged out redirects to `/login`
- [ ] Visiting `/profile/photo` while logged in shows the current avatar
      (initials if no photo yet) and an upload form
- [ ] Uploading a valid `.jpg`/`.png` under the size limit succeeds, redirects
      to `/profile`, and the new photo now appears in place of the initials
      avatar
- [ ] Uploading a non-image file (e.g. `.txt` renamed to `.jpg`, or a real
      `.pdf`) is rejected with a flashed error and no DB/file changes occur
- [ ] Uploading a file over the size limit is rejected with a flashed error
- [ ] Clicking "Remove photo" clears `photo_filename`, deletes the stored
      file, and reverts the profile page back to the initials avatar
- [ ] Re-uploading a new photo replaces the old file on disk rather than
      accumulating orphaned files
- [ ] All new SQL in `database/db.py` uses `?` parameterized queries
- [ ] `pytest` passes with no regressions to existing login/profile tests
