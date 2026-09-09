"""Tests for the Add Expense feature (Step 7): GET/POST /expenses/add and
the insert_expense query helper. Based strictly on .claude/specs/07-add-expense.md."""

from datetime import date

import pytest

from database import queries
from database.db import get_db

CATEGORIES = [
    "Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other",
]


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _valid_payload(**overrides):
    payload = {
        "amount": "50.0",
        "category": "Food",
        "date": "2026-03-20",
        "description": "Lunch",
    }
    payload.update(overrides)
    return payload


# --- Unit tests: database/queries.py insert_expense ---

def test_insert_expense_valid_all_fields_row_exists(fresh_user):
    queries.insert_expense(fresh_user, 50.0, "Food", "2026-03-20", "Lunch")

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ?", (fresh_user,)
    ).fetchone()
    conn.close()

    assert row is not None, "Expected a row to be inserted"
    assert row["amount"] == 50.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"


def test_insert_expense_description_none_stored_as_null(fresh_user):
    queries.insert_expense(fresh_user, 20.0, "Bills", "2026-03-21", None)

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ?", (fresh_user,)
    ).fetchone()
    conn.close()

    assert row is not None, "Expected a row to be inserted"
    assert row["description"] is None, "Expected description to be stored as NULL"


# --- Route tests: GET /expenses/add ---

def test_get_add_expense_unauthenticated_redirects_to_login(client):
    response = client.get("/expenses/add")
    assert response.status_code == 302, "Expected redirect for unauthenticated access"
    assert "/login" in response.headers["Location"]


def test_get_add_expense_authenticated_returns_200_with_form(client, fresh_user):
    _login(client, fresh_user)
    response = client.get("/expenses/add")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "<select" in body, "Expected a category <select> element"
    for category in CATEGORIES:
        assert category in body, f"Expected category option {category!r} in form"
    assert "<form" in body, "Expected a <form element"
    assert 'method="POST"' in body or 'method="post"' in body, "Expected form method POST"


# --- Route tests: POST /expenses/add ---

def test_post_add_expense_unauthenticated_redirects_to_login(client):
    response = client.post("/expenses/add", data=_valid_payload())
    assert response.status_code == 302, "Expected redirect for unauthenticated access"
    assert "/login" in response.headers["Location"]


def test_post_add_expense_authenticated_valid_redirects_and_inserts_row(client, fresh_user):
    _login(client, fresh_user)
    response = client.post("/expenses/add", data=_valid_payload())

    assert response.status_code == 302, "Expected redirect to /profile on success"
    assert "/profile" in response.headers["Location"]

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ?", (fresh_user,)
    ).fetchone()
    conn.close()

    assert row is not None, "Expected the new expense row to exist in the DB"
    assert row["amount"] == 50.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"


def test_post_add_expense_missing_amount_rerenders_with_error(client, fresh_user):
    _login(client, fresh_user)
    payload = _valid_payload()
    del payload["amount"]
    response = client.post("/expenses/add", data=payload)
    body = response.get_data(as_text=True)

    assert response.status_code == 200, "Expected form to be re-rendered"
    assert "error" in body.lower(), "Expected an error message in the response body"


def test_post_add_expense_amount_zero_rerenders_with_error(client, fresh_user):
    _login(client, fresh_user)
    response = client.post("/expenses/add", data=_valid_payload(amount="0"))
    body = response.get_data(as_text=True)

    assert response.status_code == 200, "Expected form to be re-rendered"
    assert "error" in body.lower(), "Expected an error message in the response body"


def test_post_add_expense_non_numeric_amount_rerenders_with_error(client, fresh_user):
    _login(client, fresh_user)
    response = client.post("/expenses/add", data=_valid_payload(amount="not-a-number"))
    body = response.get_data(as_text=True)

    assert response.status_code == 200, "Expected form to be re-rendered"
    assert "error" in body.lower(), "Expected an error message in the response body"


def test_post_add_expense_invalid_category_rerenders_with_error(client, fresh_user):
    _login(client, fresh_user)
    response = client.post("/expenses/add", data=_valid_payload(category="Not A Real Category"))
    body = response.get_data(as_text=True)

    assert response.status_code == 200, "Expected form to be re-rendered"
    assert "error" in body.lower(), "Expected an error message in the response body"


def test_post_add_expense_invalid_date_rerenders_with_error(client, fresh_user):
    _login(client, fresh_user)
    response = client.post("/expenses/add", data=_valid_payload(date="not-a-date"))
    body = response.get_data(as_text=True)

    assert response.status_code == 200, "Expected form to be re-rendered"
    assert "error" in body.lower(), "Expected an error message in the response body"


def test_post_add_expense_no_description_redirects_and_inserts_null(client, fresh_user):
    _login(client, fresh_user)
    payload = _valid_payload()
    del payload["description"]
    response = client.post("/expenses/add", data=payload)

    assert response.status_code == 302, "Expected redirect to /profile on success"
    assert "/profile" in response.headers["Location"]

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ?", (fresh_user,)
    ).fetchone()
    conn.close()

    assert row is not None, "Expected the new expense row to exist in the DB"
    assert row["description"] is None, "Expected description to be stored as NULL when omitted"
