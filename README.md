# Spendly 

Spendly is a lightweight personal expense tracker built with **Flask** and **SQLite**. It lets users register, log in, record expenses, and review their spending through a profile dashboard with date filtering and category breakdowns — all with a vanilla HTML/CSS/JS frontend and no external frameworks.

---

## Features

- **Authentication** — register, login, and logout with hashed passwords (Werkzeug `generate_password_hash`/`check_password_hash`) and session-based auth
- **Profile dashboard** — summary stats, recent transactions, and a category breakdown for the logged-in user
- **Date filtering** — filter the dashboard by preset ranges (this month, last 3 months, last 6 months) or a custom date range
- **Add expense** — log a new expense with amount, category, date, and an optional description, with full server-side validation
- **Edit expense** — update an existing expense, scoped to the owning user
- **Delete expense** — remove an expense, scoped to the owning user
- **Profile photo upload** — upload (`.jpg`/`.jpeg`/`.png`, 2MB max) or remove a profile photo, with server-side content-length and extension validation
- **Appearance / theme preference** — switch between system, light, and dark themes, persisted per user
- **Analytics page** — dedicated analytics view for the logged-in user
- **Static pages** — landing, terms, and privacy pages

---

## Tech stack

- **Backend:** Flask (single `app.py`, no blueprints)
- **Database:** SQLite via the standard library `sqlite3` module (no ORM)
- **Frontend:** Jinja2 templates + vanilla CSS/JS (no React, no jQuery, no npm packages)
- **Testing:** pytest + pytest-flask

---

## Project structure

```
spendly/
├── app.py                  # All Flask routes
├── database/
│   ├── db.py                # Connection, schema, seeding, and user helpers
│   └── queries.py            # Profile/expense query and mutation helpers
├── templates/
│   ├── base.html              # Shared layout
│   └── *.html                 # One template per page
├── static/
│   ├── css/                   # Global and page-specific styles
│   ├── js/main.js             # Vanilla JS
│   └── uploads/profile_photos/# Uploaded profile photos
├── tests/                    # pytest test suite
└── requirements.txt
```

---

## Getting started

```bash
# Clone the repo
git clone <your-repo-url>
cd expense-tracker

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

The app runs at **http://localhost:5001** (not the Flask default 5000). The SQLite database and tables are created automatically on startup, and a demo account is seeded if the database is empty:

- **Email:** `demo@spendly.com`
- **Password:** `demo123`

---

## Running tests

```bash
pytest                       # run the full suite
pytest tests/test_foo.py     # run a specific test file
pytest -k "test_name"        # run a specific test by name
pytest -s                    # run with output visible
```

---

## Routes

| Route | Methods | Description |
|---|---|---|
| `/` | GET | Landing page (redirects to profile if logged in) |
| `/register` | GET, POST | Create a new account |
| `/login` | GET, POST | Sign in |
| `/logout` | GET | Clear session and sign out |
| `/profile` | GET | Dashboard — stats, transactions, category breakdown, date filters |
| `/analytics` | GET | Analytics page |
| `/expenses/add` | GET, POST | Add a new expense |
| `/expenses/<id>/edit` | GET, POST | Edit an existing expense |
| `/expenses/<id>/delete` | POST | Delete an expense |
| `/profile/photo` | GET, POST | Upload a profile photo |
| `/profile/photo/remove` | POST | Remove the current profile photo |
| `/profile/appearance` | POST | Update theme preference (system/light/dark) |
| `/terms` | GET | Terms of service |
| `/privacy` | GET | Privacy policy |

---

## Database schema

**users**
`id`, `name`, `email` (unique), `password_hash`, `created_at`, `photo_filename`, `theme_preference`

**expenses**
`id`, `user_id` (FK → `users.id`), `amount`, `category`, `date`, `description`, `created_at`

Foreign key enforcement is enabled explicitly on every connection (`PRAGMA foreign_keys = ON`), since SQLite has it off by default.

---

## Security notes

- Passwords are hashed with Werkzeug's PBKDF2-based hashing — never stored in plaintext
- All SQL queries use parameterized placeholders (`?`) — no string interpolation
- Expense lookups, edits, and deletes are always scoped to the logged-in user's `user_id`
- Uploaded photos are validated by extension and real byte size (not trusted client headers), and redirects after theme changes are restricted to same-site paths

---

## Notes

This project was built incrementally as a learning exercise, with each feature (login, profile dashboard, date filtering, add/edit/delete expense, profile photos, dark mode) implemented and tested as a separate step.
