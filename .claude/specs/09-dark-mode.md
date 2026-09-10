# Spec: Dark Mode / Appearance Setting

## Overview
Spendly currently renders with a single, hardcoded light theme. This feature
adds a three-way **Appearance** setting (System / Light / Dark) — a segmented
icon control matching the standard OS-level pattern — that lets a logged-in
user choose how the app looks. The choice is persisted per-user and applied
across every page via CSS custom properties, which the project's existing
"never hardcode hex values" rule already makes straightforward.

## Depends on
- Step 3 (Login/Logout) — requires session-based auth to identify the user
- Step 5 (Profile Page Backend) — requires `profile.html` and the
  `current_user` context processor
- Existing CSS-variables-only rule for colors (already required project-wide,
  now becomes load-bearing rather than just style hygiene)

## Routes
- `GET /profile/appearance` — render the appearance settings section
  (can also be embedded directly in `/profile` instead of a separate route —
  see **Open question** below) — logged-in
- `POST /profile/appearance` — accept `theme` = `system` | `light` | `dark`,
  validate, and persist to `users.theme_preference` — logged-in

## Database changes
Add one column to `users` (same pattern as `photo_filename`):

- `users.theme_preference TEXT NOT NULL DEFAULT 'system'` — one of
  `'system'`, `'light'`, `'dark'`.

Add this to the `CREATE TABLE IF NOT EXISTS users` statement in `init_db()`.
No migration script needed, consistent with this project's
`CREATE TABLE IF NOT EXISTS` dev workflow.

## How theming is applied
- On every page render, `base.html` sets
  `<html data-theme="{{ current_user.theme_preference if current_user else 'system' }}">`.
- All colors in `style.css` (and any per-page CSS) are defined as CSS
  variables on `:root`, with a `[data-theme="dark"]` block overriding them.
- When `data-theme="system"`, a small inline `<script>` in `base.html` (or a
  `prefers-color-scheme` media query fallback in CSS) resolves the OS
  preference on load — this must work even before the settings POST returns,
  to avoid a flash of the wrong theme.
- Logged-out visitors (no `current_user`) get `system` behavior only, via the
  CSS media query — no DB read possible pre-login.

## Templates
- **Modify:** `templates/base.html` — add `data-theme` attribute to `<html>`,
  add the `prefers-color-scheme` fallback logic for system mode.
- **Modify:** `templates/profile.html` (or **create**
  `templates/profile_appearance.html` if kept as its own page — see open
  question) — add the three-icon segmented control (system/light/dark),
  showing the current selection as active.
- **Modify:** `static/css/style.css` — convert any remaining hardcoded colors
  to CSS variables (audit needed — this feature is the point at which that
  rule gets fully enforced), add the `[data-theme="dark"]` variable overrides.

## Files to change
- `database/db.py` — add `theme_preference` column + a `set_theme_preference()`
  / `get_theme_preference()` helper (or reuse the existing user-read helper)
- `app.py` — add the appearance route(s)
- `templates/base.html` — `data-theme` attribute + system-mode script
- `templates/profile.html` — link/section to appearance settings
- `static/css/style.css` — dark variable overrides

## Files to create
- `templates/profile_appearance.html` — only if kept as a separate page
  rather than a section on `/profile` (see open question)
- `static/css/profile_appearance.css` — only if the separate-page route is used

## New dependencies
None. Pure CSS variables + a small inline script for system-preference
detection; no theming library needed.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only (`?` placeholders)
- All DB logic (reading/writing `theme_preference`) belongs in
  `database/db.py`, never inline in `app.py` routes
- Reject any `theme` value outside `system` / `light` / `dark` server-side —
  flash an error and re-render rather than silently defaulting
- Every color in every stylesheet must be a CSS variable — no exceptions,
  since a single hardcoded hex value will visibly break dark mode
- Use `abort()` for HTTP errors (e.g. unauthenticated access), not bare
  `return "error string"`
- All templates extend `base.html`
- Avoid a flash-of-wrong-theme on load: the theme-resolving script must run
  before first paint (inline in `<head>`, not deferred)

## Open question (needs your decision before implementation)
Should Appearance be its own page (`/profile/appearance`, matching the
`/profile/photo` pattern from the photo-upload spec) or a section directly
inside `/profile`? A single toggle control is light enough that most apps
put it inline on the main settings/profile page rather than behind a link —
but a separate route keeps it consistent with how this project already
structured the photo feature.

## Definition of done
- [ ] Profile page (or `/profile/appearance`) shows the three-icon control
      with the current preference visually indicated
- [ ] Selecting Light / Dark immediately applies the theme and persists it
      (no page-refresh flash back to the old theme)
- [ ] Selecting System follows the OS preference, including live-updating
      if the OS theme changes while the tab is open (via
      `matchMedia('(prefers-color-scheme: dark)')` listener) or on next load
- [ ] Preference persists across logout/login and across devices (stored on
      `users`, not just a cookie)
- [ ] Logged-out pages respect OS `prefers-color-scheme` with no DB dependency
- [ ] No hardcoded hex colors remain anywhere in `static/css/` (audit passes)
- [ ] Posting an invalid `theme` value is rejected with a flashed error and
      no DB change occurs
- [ ] `pytest` passes with no regressions to existing login/profile tests