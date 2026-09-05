import pytest

from database import queries


# --- Subagent 1 tests: get_recent_transactions ---

def test_recent_transactions_newest_first(seed_user):
    transactions = queries.get_recent_transactions(seed_user)
    dates = [t["date"] for t in transactions]
    assert dates == sorted(dates, reverse=True)


def test_recent_transactions_fields(seed_user):
    transactions = queries.get_recent_transactions(seed_user)
    assert len(transactions) > 0
    for txn in transactions:
        assert isinstance(txn, dict)
        assert set(txn.keys()) == {"date", "description", "category", "amount"}


def test_recent_transactions_empty_for_no_expenses(fresh_user):
    assert queries.get_recent_transactions(fresh_user) == []


# --- Subagent 2 tests: get_summary_stats ---

def test_summary_stats_with_expenses(seed_user):
    stats = queries.get_summary_stats(seed_user)
    assert stats["total_spent"] == pytest.approx(289.14)
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"


def test_summary_stats_no_expenses(fresh_user):
    stats = queries.get_summary_stats(fresh_user)
    assert stats["total_spent"] == 0
    assert stats["transaction_count"] == 0
    assert stats["top_category"] == "—"


# --- Subagent 3 tests: get_category_breakdown ---

def test_category_breakdown_with_expenses(seed_user):
    breakdown = queries.get_category_breakdown(seed_user)
    assert len(breakdown) == 7
    totals = [cat["total"] for cat in breakdown]
    assert totals == sorted(totals, reverse=True)
    assert breakdown[0]["name"] == "Bills"
    assert breakdown[-1]["name"] == "Other"
    for cat in breakdown:
        assert set(cat.keys()) == {"name", "total", "percent"}


def test_category_breakdown_percentages_sum_to_100(seed_user):
    breakdown = queries.get_category_breakdown(seed_user)
    assert sum(cat["percent"] for cat in breakdown) == 100


def test_category_breakdown_empty_for_no_expenses(fresh_user):
    assert queries.get_category_breakdown(fresh_user) == []


# --- Route tests (integration step) ---

def test_profile_redirects_when_not_logged_in(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_authenticated_shows_real_data(client, seed_user):
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user

    response = client.get("/profile")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "₹" in body
    assert "₹289.14" in body
    assert ">8<" in body or "8" in body
    assert "Bills" in body

    first_tx_index = body.index("2026-08-20")
    last_tx_index = body.index("2026-08-02")
    assert first_tx_index < last_tx_index

    for category in ("Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"):
        assert category in body
