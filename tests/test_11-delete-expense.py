"""Tests for the Delete Expense feature (Step 11): POST /expenses/<id>/delete
and the delete_expense query helper.
Based strictly on .claude/specs/11-delete-expense.md."""

import pytest

from database import queries
from database.db import get_db


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


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


def _count_expenses(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row["c"]


# --- Unit tests: database/queries.py delete_expense ---


def test_delete_expense_correct_owner_removes_row(seed_user):
    expense_id = _first_expense_id(seed_user)

    queries.delete_expense(expense_id, seed_user)

    row = _fetch_expense(expense_id)
    assert row is None, "Expected the expense row to be removed from the DB"


def test_delete_expense_wrong_user_affects_zero_rows_and_leaves_expense_intact(
    seed_user, fresh_user
):
    expense_id = _first_expense_id(seed_user)
    original = _fetch_expense(expense_id)

    # Should not raise, and should affect zero rows because user_id doesn't match.
    queries.delete_expense(expense_id, fresh_user)

    row = _fetch_expense(expense_id)
    assert row is not None, "Expected the expense to still exist"
    assert row["id"] == original["id"]
    assert row["amount"] == original["amount"]
    assert row["category"] == original["category"]


# --- Route tests: POST /expenses/<id>/delete ---


def test_post_delete_expense_unauthenticated_redirects_to_login(client, seed_user):
    expense_id = _first_expense_id(seed_user)

    response = client.post(f"/expenses/{expense_id}/delete")

    assert response.status_code == 302, "Expected redirect for unauthenticated access"
    assert "/login" in response.headers["Location"]

    row = _fetch_expense(expense_id)
    assert (
        row is not None
    ), "Expected the expense to remain untouched when unauthenticated"


def test_post_delete_expense_nonexistent_id_returns_404(client, fresh_user):
    _login(client, fresh_user)

    response = client.post("/expenses/999999/delete")

    assert response.status_code == 404, "Expected 404 for a non-existent expense id"


def test_post_delete_expense_other_users_expense_returns_404_and_does_not_delete(
    client, seed_user, fresh_user
):
    expense_id = _first_expense_id(seed_user)
    _login(client, fresh_user)

    response = client.post(f"/expenses/{expense_id}/delete")

    assert (
        response.status_code == 404
    ), "Expected 404 when deleting another user's expense"

    row = _fetch_expense(expense_id)
    assert row is not None, "Expected the other user's expense to remain in the DB"


def test_post_delete_expense_owner_deletes_row_and_redirects_to_profile(
    client, seed_user
):
    expense_id = _first_expense_id(seed_user)
    before_count = _count_expenses(seed_user)
    _login(client, seed_user)

    response = client.post(f"/expenses/{expense_id}/delete")

    assert response.status_code == 302, "Expected redirect to /profile on success"
    assert "/profile" in response.headers["Location"]

    row = _fetch_expense(expense_id)
    assert row is None, "Expected the expense to be deleted from the DB"

    after_count = _count_expenses(seed_user)
    assert after_count == before_count - 1, "Expected exactly one expense to be removed"


def test_deleted_expense_no_longer_appears_on_profile_page(client, seed_user):
    expense_id = _first_expense_id(seed_user)
    expense = _fetch_expense(expense_id)
    _login(client, seed_user)

    client.post(f"/expenses/{expense_id}/delete")
    response = client.get("/profile")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    if expense["description"]:
        assert (
            expense["description"] not in body
        ), "Expected the deleted expense's description to no longer appear on /profile"
    assert (
        f"/expenses/{expense_id}/edit" not in body
    ), "Expected no lingering edit link for the deleted expense"
    assert (
        f"/expenses/{expense_id}/delete" not in body
    ), "Expected no lingering delete form for the deleted expense"


def test_get_delete_expense_returns_405_not_a_confirmation_page(client, seed_user):
    expense_id = _first_expense_id(seed_user)
    _login(client, seed_user)

    response = client.get(f"/expenses/{expense_id}/delete")

    assert response.status_code == 405, (
        "Expected 405 Method Not Allowed for a bare GET -- there is no "
        "server-rendered confirmation page for this route"
    )

    row = _fetch_expense(expense_id)
    assert row is not None, "Expected GET to have no side effects on the expense"


# --- Template test: profile.html delete form ---


def test_profile_page_contains_delete_form_for_each_transaction(client, seed_user):
    expense_id = _first_expense_id(seed_user)
    _login(client, seed_user)

    response = client.get("/profile")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert (
        f"/expenses/{expense_id}/delete" in body
    ), "Expected a delete form/action pointing to the correct URL for each transaction"
    assert (
        "data-delete-form" in body
    ), "Expected the delete form to carry the data-delete-form attribute"
    assert (
        "data-delete-trigger" in body
    ), "Expected the delete button to carry the data-delete-trigger attribute"
    assert (
        'aria-label="Delete expense"' in body
    ), "Expected the icon-only delete button to have an accessible label"
