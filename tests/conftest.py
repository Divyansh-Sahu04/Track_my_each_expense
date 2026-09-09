import os
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import database.db as db

# app.py runs init_db()/seed_db() as a module-level side effect on first import.
# Point DB_PATH at a disposable bootstrap file *before* that first import so the
# one-time seeding lands somewhere harmless, not inside a test's temp DB where it
# could collide with a fixture's own seed data (e.g. duplicate demo@spendly.com).
db.DB_PATH = os.path.join(tempfile.mkdtemp(), "bootstrap.db")
import app as flask_app_module  # noqa: E402  (import after DB_PATH bootstrap)


SEED_EXPENSES = [
    (45.50, "Food", "2026-08-02", "Grocery run"),
    (12.00, "Transport", "2026-08-04", "Bus fare top-up"),
    (89.99, "Bills", "2026-08-05", "Electricity bill"),
    (25.00, "Health", "2026-08-09", "Pharmacy purchase"),
    (15.75, "Entertainment", "2026-08-12", "Movie ticket"),
    (60.20, "Shopping", "2026-08-15", "New shoes"),
    (8.30, "Other", "2026-08-18", "Miscellaneous"),
    (32.40, "Food", "2026-08-20", "Dinner with friends"),
]


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_expense_tracker.db")
    monkeypatch.setattr(db, "DB_PATH", db_path)
    db.init_db()
    yield db_path


@pytest.fixture
def seed_user(temp_db):
    """A user with 8 known expenses (total 289.14 -- matches spec's 8 txns)."""
    from werkzeug.security import generate_password_hash

    conn = db.get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = cursor.lastrowid
    conn.executemany(
        """
        INSERT INTO expenses (user_id, amount, category, date, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        [(user_id, *row) for row in SEED_EXPENSES],
    )
    conn.commit()
    conn.close()
    return user_id


@pytest.fixture
def fresh_user(temp_db):
    """A user with zero expenses."""
    from werkzeug.security import generate_password_hash

    conn = db.get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("New User", "new@spendly.com", generate_password_hash("newpass123")),
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def _days_before(days):
    """Return an ISO date string `days` before today."""
    return (date.today() - timedelta(days=days)).isoformat()


@pytest.fixture
def multi_month_user(temp_db):
    """A user with expenses spread across ~8 months, for date-filter tests.
    Dates use generous day-offsets (not exact calendar months) relative to
    today, so preset boundary math staying off by a day or two never flips
    which preset an expense falls into."""
    from werkzeug.security import generate_password_hash

    expenses = [
        (50.00, "Food", _days_before(250), "Outside every preset but All Time"),
        (40.00, "Bills", _days_before(150), "Within Last 6 Months only"),
        (30.00, "Transport", _days_before(60), "Within Last 3 Months and Last 6 Months"),
        (25.00, "Health", _days_before(0), "Within every preset (today)"),
    ]

    conn = db.get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Multi Month User", "multimonth@spendly.com", generate_password_hash("test123")),
    )
    user_id = cursor.lastrowid
    conn.executemany(
        """
        INSERT INTO expenses (user_id, amount, category, date, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        [(user_id, *row) for row in expenses],
    )
    conn.commit()
    conn.close()
    return user_id


@pytest.fixture
def client(temp_db):
    flask_app_module.app.config["TESTING"] = True
    with flask_app_module.app.test_client() as client:
        yield client
