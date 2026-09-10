"""Tests for the Edit Expense feature (Step 10): GET/POST /expenses/<id>/edit
and the get_expense_by_id / update_expense query helpers.
Based strictly on .claude/specs/10-edit-expense.md."""

import pytest

from database import queries
from database.db import get_db

CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _valid_payload(**overrides):
    payload = {
        "amount": "99.0",
        "category": "Bills",
        "date": "2026-03-25",
        "description": "Updated description",
    }
    payload.update(overrides)
    return payload


def _first_expense_id(user_id):
    """Return the id of the first seeded expense for a user (ordered stably by id)."""
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM expenses WHERE user_id = ? ORDER BY id ASC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return row["id"]


def _fetch_expense(expense_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    return row


# --- Unit tests: database/queries.py get_expense_by_id ---


def test_get_expense_by_id_correct_user_returns_row(seed_user):
    expense_id = _first_expense_id(seed_user)

    row = queries.get_expense_by_id(expense_id, seed_user)

    assert row is not None, "Expected the matching expense row to be returned"
    assert row["id"] == expense_id
    assert row["user_id"] == seed_user


def test_get_expense_by_id_wrong_user_returns_none(seed_user, fresh_user):
    expense_id = _first_expense_id(seed_user)

    row = queries.get_expense_by_id(expense_id, fresh_user)

    assert row is None, "Expected None when the expense belongs to a different user"


def test_get_expense_by_id_nonexistent_id_returns_none(fresh_user):
    row = queries.get_expense_by_id(999999, fresh_user)

    assert row is None, "Expected None for a non-existent expense id"


# --- Unit tests: database/queries.py update_expense ---


def test_update_expense_correct_user_updates_row(seed_user):
    expense_id = _first_expense_id(seed_user)

    queries.update_expense(
        expense_id, seed_user, 99.0, "Bills", "2026-03-25", "Changed"
    )

    row = _fetch_expense(expense_id)
    assert row["amount"] == 99.0, "Expected the amount to be updated in the DB"
    assert row["category"] == "Bills"
    assert row["date"] == "2026-03-25"
    assert row["description"] == "Changed"


def test_update_expense_wrong_user_leaves_row_unchanged(seed_user, fresh_user):
    expense_id = _first_expense_id(seed_user)
    original = _fetch_expense(expense_id)

    # Should not raise, and should affect zero rows because user_id doesn't match.
    queries.update_expense(
        expense_id, fresh_user, 99.0, "Bills", "2026-03-25", "Changed"
    )

    row = _fetch_expense(expense_id)
    assert row["amount"] == original["amount"], "Expected amount to remain unchanged"
    assert (
        row["category"] == original["category"]
    ), "Expected category to remain unchanged"
    assert row["date"] == original["date"], "Expected date to remain unchanged"
    assert (
        row["description"] == original["description"]
    ), "Expected description to remain unchanged"


# --- Route tests: GET /expenses/<id>/edit ---


def test_get_edit_expense_unauthenticated_redirects_to_login(client, seed_user):
    expense_id = _first_expense_id(seed_user)

    response = client.get(f"/expenses/{expense_id}/edit")

    assert response.status_code == 302, "Expected redirect for unauthenticated access"
    assert "/login" in response.headers["Location"]


def test_get_edit_expense_authenticated_own_expense_returns_prefilled_form(
    client, seed_user
):
    expense_id = _first_expense_id(seed_user)
    expense = _fetch_expense(expense_id)
    _login(client, seed_user)

    response = client.get(f"/expenses/{expense_id}/edit")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "<form" in body, "Expected a <form> element"
    assert "<select" in body, "Expected a category <select> element"
    assert (
        str(expense["amount"]) in body or f'{expense["amount"]:.2f}' in body
    ), "Expected the expense's current amount to be pre-filled"
    assert (
        expense["date"] in body
    ), "Expected the expense's current date to be pre-filled"
    if expense["description"]:
        assert expense["description"] in body, "Expected description to be pre-filled"


def test_get_edit_expense_authenticated_own_expense_correct_category_preselected(
    client, seed_user
):
    expense_id = _first_expense_id(seed_user)
    expense = _fetch_expense(expense_id)
    _login(client, seed_user)

    response = client.get(f"/expenses/{expense_id}/edit")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    # The current category's <option> should carry a "selected" marker.
    category = expense["category"]
    assert category in body, "Expected the current category to appear in the form"
    assert "selected" in body, "Expected some option to be marked selected"


def test_get_edit_expense_other_users_expense_returns_404(
    client, seed_user, fresh_user
):
    expense_id = _first_expense_id(seed_user)
    _login(client, fresh_user)

    response = client.get(f"/expenses/{expense_id}/edit")

    assert (
        response.status_code == 404
    ), "Expected 404 when editing another user's expense"


def test_get_edit_expense_nonexistent_id_returns_404(client, fresh_user):
    _login(client, fresh_user)

    response = client.get("/expenses/999999/edit")

    assert response.status_code == 404, "Expected 404 for a non-existent expense id"


# --- Route tests: POST /expenses/<id>/edit ---


def test_post_edit_expense_unauthenticated_redirects_to_login(client, seed_user):
    expense_id = _first_expense_id(seed_user)

    response = client.post(f"/expenses/{expense_id}/edit", data=_valid_payload())

    assert response.status_code == 302, "Expected redirect for unauthenticated access"
    assert "/login" in response.headers["Location"]


def test_post_edit_expense_authenticated_valid_redirects_and_updates_row(
    client, seed_user
):
    expense_id = _first_expense_id(seed_user)
    _login(client, seed_user)

    response = client.post(f"/expenses/{expense_id}/edit", data=_valid_payload())

    assert response.status_code == 302, "Expected redirect to /profile on success"
    assert "/profile" in response.headers["Location"]

    row = _fetch_expense(expense_id)
    assert row["amount"] == 99.0
    assert row["category"] == "Bills"
    assert row["date"] == "2026-03-25"
    assert row["description"] == "Updated description"


def test_post_edit_expense_other_users_expense_returns_404(
    client, seed_user, fresh_user
):
    expense_id = _first_expense_id(seed_user)
    original = _fetch_expense(expense_id)
    _login(client, fresh_user)

    response = client.post(f"/expenses/{expense_id}/edit", data=_valid_payload())

    assert (
        response.status_code == 404
    ), "Expected 404 when editing another user's expense"

    row = _fetch_expense(expense_id)
    assert (
        row["amount"] == original["amount"]
    ), "Expected the other user's expense to remain unchanged"


def test_post_edit_expense_missing_amount_rerenders_with_error(client, seed_user):
    expense_id = _first_expense_id(seed_user)
    original = _fetch_expense(expense_id)
    _login(client, seed_user)

    payload = _valid_payload()
    del payload["amount"]
    response = client.post(f"/expenses/{expense_id}/edit", data=payload)
    body = response.get_data(as_text=True)

    assert response.status_code == 200, "Expected form to be re-rendered"
    assert "error" in body.lower(), "Expected an error message in the response body"

    row = _fetch_expense(expense_id)
    assert (
        row["amount"] == original["amount"]
    ), "Expected the row to remain unchanged on validation error"


def test_post_edit_expense_amount_zero_rerenders_with_error(client, seed_user):
    expense_id = _first_expense_id(seed_user)
    original = _fetch_expense(expense_id)
    _login(client, seed_user)

    response = client.post(
        f"/expenses/{expense_id}/edit", data=_valid_payload(amount="0")
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200, "Expected form to be re-rendered"
    assert "error" in body.lower(), "Expected an error message in the response body"

    row = _fetch_expense(expense_id)
    assert (
        row["amount"] == original["amount"]
    ), "Expected the row to remain unchanged on validation error"


def test_post_edit_expense_non_numeric_amount_rerenders_with_error(client, seed_user):
    expense_id = _first_expense_id(seed_user)
    original = _fetch_expense(expense_id)
    _login(client, seed_user)

    response = client.post(
        f"/expenses/{expense_id}/edit", data=_valid_payload(amount="not-a-number")
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200, "Expected form to be re-rendered"
    assert "error" in body.lower(), "Expected an error message in the response body"

    row = _fetch_expense(expense_id)
    assert (
        row["amount"] == original["amount"]
    ), "Expected the row to remain unchanged on validation error"


def test_post_edit_expense_invalid_category_rerenders_with_error(client, seed_user):
    expense_id = _first_expense_id(seed_user)
    original = _fetch_expense(expense_id)
    _login(client, seed_user)

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data=_valid_payload(category="Not A Real Category"),
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200, "Expected form to be re-rendered"
    assert "error" in body.lower(), "Expected an error message in the response body"

    row = _fetch_expense(expense_id)
    assert (
        row["category"] == original["category"]
    ), "Expected the row to remain unchanged on validation error"


def test_post_edit_expense_invalid_date_rerenders_with_error(client, seed_user):
    expense_id = _first_expense_id(seed_user)
    original = _fetch_expense(expense_id)
    _login(client, seed_user)

    response = client.post(
        f"/expenses/{expense_id}/edit", data=_valid_payload(date="not-a-date")
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200, "Expected form to be re-rendered"
    assert "error" in body.lower(), "Expected an error message in the response body"

    row = _fetch_expense(expense_id)
    assert (
        row["date"] == original["date"]
    ), "Expected the row to remain unchanged on validation error"


def test_post_edit_expense_validation_error_repopulates_submitted_values(
    client, seed_user
):
    expense_id = _first_expense_id(seed_user)
    _login(client, seed_user)

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data=_valid_payload(amount="0", description="My submitted description"),
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert (
        "My submitted description" in body
    ), "Expected the submitted (not original) values to be pre-filled after a validation error"


def test_post_edit_expense_no_description_redirects_and_saves_null(client, seed_user):
    expense_id = _first_expense_id(seed_user)
    _login(client, seed_user)

    payload = _valid_payload()
    del payload["description"]
    response = client.post(f"/expenses/{expense_id}/edit", data=payload)

    assert response.status_code == 302, "Expected redirect to /profile on success"
    assert "/profile" in response.headers["Location"]

    row = _fetch_expense(expense_id)
    assert (
        row["description"] is None
    ), "Expected description to be stored as NULL when omitted"


def test_post_edit_expense_blank_description_redirects_and_saves_null(
    client, seed_user
):
    expense_id = _first_expense_id(seed_user)
    _login(client, seed_user)

    response = client.post(
        f"/expenses/{expense_id}/edit", data=_valid_payload(description="   ")
    )

    assert response.status_code == 302, "Expected redirect to /profile on success"
    assert "/profile" in response.headers["Location"]

    row = _fetch_expense(expense_id)
    assert (
        row["description"] is None
    ), "Expected a whitespace-only description to be stored as NULL"


def test_post_edit_expense_nonexistent_id_returns_404(client, fresh_user):
    _login(client, fresh_user)

    response = client.post("/expenses/999999/edit", data=_valid_payload())

    assert response.status_code == 404, "Expected 404 for a non-existent expense id"


# --- Template test: profile.html Edit link ---


def test_profile_page_contains_edit_link_for_each_transaction(client, seed_user):
    expense_id = _first_expense_id(seed_user)
    _login(client, seed_user)

    response = client.get("/profile")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert (
        f"/expenses/{expense_id}/edit" in body
    ), "Expected an Edit link pointing to the correct URL for each transaction"
