# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Spendly is a Flask-based personal expense tracker built incrementally as a learning project. Many features are intentionally unimplemented — routes exist as placeholders that return plain strings (e.g. "Logout — coming in Step 3") until their corresponding step is built. `database/db.py` is currently an empty stub with a comment describing what students will implement (`get_db()`, `init_db()`, `seed_db()`) — don't assume database functionality exists until that file has real code.

## Commands

```bash
# activate the venv (Windows)
.venv\Scripts\activate

# install dependencies
pip install -r requirements.txt

# run the dev server (http://localhost:5001)
python app.py

# run tests
pytest
```

There is no build step, linter, or bundler configured — this is server-rendered Flask with vanilla CSS/JS (no framework, no npm).

## Architecture

- `app.py` — single-file Flask app; all routes are defined directly here (no blueprints). Routes are grouped into "implemented" (landing, register, login, terms, privacy) and "placeholder" (logout, profile, expenses CRUD) sections — keep that grouping/comment structure when adding routes until the corresponding feature is actually built.
- `database/db.py` — will hold the SQLite access layer (`get_db()`, `init_db()`, `seed_db()`). SQLite connections should use `row_factory` and have foreign keys enabled per the stub's own documentation.
- `templates/` — Jinja2 templates. `base.html` defines the shared shell (nav + footer) with `{% block title %}`, `{% block head %}`, `{% block content %}`, and `{% block scripts %}`. New pages should extend `base.html` rather than duplicating the nav/footer markup, matching the pattern already used by `terms.html`/`privacy.html`.
- `static/css/style.css` — single global stylesheet for the whole site (no per-page CSS files, despite what old prompts may reference).
- `static/js/main.js` — currently empty; vanilla JS only, no external JS dependencies/frameworks are used anywhere in this project.
- `prompt.txt` — a running log of the prompts used to build prior features via Claude Code. Useful as historical context for *why* something looks the way it does, but not something to keep updating yourself.

## Conventions worth preserving

- No JS frameworks or build tooling — plain `<script>` includes and vanilla JS/CSS only.
- New pages/routes follow the existing pattern: add a route in `app.py` that renders a template extending `base.html`, and match the visual style already established in `landing.html`/`terms.html`/`privacy.html`.
- Commit messages follow `area: short description` (e.g. `landing: add privacy policy page and route`).
