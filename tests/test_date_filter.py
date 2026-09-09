import html
import re
from datetime import date, timedelta

import pytest

from database import queries


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _preset_href(body, label):
    match = re.search(rf'href="([^"]+)"[^>]*>{re.escape(label)}<', body)
    assert match, f"missing preset link for {label!r}"
    return html.unescape(match.group(1))


# --- Unit tests: database/queries.py date-range params ---

def test_queries_filtered_by_date_range(multi_month_user):
    date_from = (date.today() - timedelta(days=70)).isoformat()
    date_to = date.today().isoformat()

    transactions = queries.get_recent_transactions(multi_month_user, date_from=date_from, date_to=date_to)
    descriptions = {t["description"] for t in transactions}
    assert descriptions == {
        "Within Last 3 Months and Last 6 Months",
        "Within every preset (today)",
    }

    stats = queries.get_summary_stats(multi_month_user, date_from, date_to)
    assert stats["transaction_count"] == 2
    assert stats["total_spent"] == pytest.approx(55.00)

    breakdown = queries.get_category_breakdown(multi_month_user, date_from, date_to)
    assert {cat["name"] for cat in breakdown} == {"Transport", "Health"}
    assert sum(cat["percent"] for cat in breakdown) == 100


def test_queries_unfiltered_when_dates_none(multi_month_user):
    assert queries.get_recent_transactions(multi_month_user) == queries.get_recent_transactions(
        multi_month_user, date_from=None, date_to=None
    )
    assert queries.get_summary_stats(multi_month_user) == queries.get_summary_stats(multi_month_user, None, None)
    assert queries.get_category_breakdown(multi_month_user) == queries.get_category_breakdown(
        multi_month_user, None, None
    )


def test_queries_no_match_in_range_returns_empty(seed_user):
    date_from = "2099-01-01"
    date_to = "2099-01-31"
    assert queries.get_recent_transactions(seed_user, date_from=date_from, date_to=date_to) == []
    stats = queries.get_summary_stats(seed_user, date_from, date_to)
    assert stats["total_spent"] == 0
    assert stats["transaction_count"] == 0
    assert stats["top_category"] == "—"
    assert queries.get_category_breakdown(seed_user, date_from, date_to) == []


# --- Route tests: /profile with date filter query params ---

def test_profile_all_time_no_params_shows_everything(client, multi_month_user):
    _login(client, multi_month_user)
    body = client.get("/profile").get_data(as_text=True)
    for description in (
        "Outside every preset but All Time",
        "Within Last 6 Months only",
        "Within Last 3 Months and Last 6 Months",
        "Within every preset (today)",
    ):
        assert description in body


def test_profile_this_month_preset(client, multi_month_user):
    _login(client, multi_month_user)
    home_body = client.get("/profile").get_data(as_text=True)
    href = _preset_href(home_body, "This Month")

    body = client.get(href).get_data(as_text=True)
    assert "Within every preset (today)" in body
    assert "Within Last 3 Months and Last 6 Months" not in body
    assert "Within Last 6 Months only" not in body
    assert "Outside every preset but All Time" not in body
    assert "filter-preset--active" in body


def test_profile_last_3_months_preset(client, multi_month_user):
    _login(client, multi_month_user)
    home_body = client.get("/profile").get_data(as_text=True)
    href = _preset_href(home_body, "Last 3 Months")

    body = client.get(href).get_data(as_text=True)
    assert "Within every preset (today)" in body
    assert "Within Last 3 Months and Last 6 Months" in body
    assert "Within Last 6 Months only" not in body
    assert "Outside every preset but All Time" not in body


def test_profile_last_6_months_preset(client, multi_month_user):
    _login(client, multi_month_user)
    home_body = client.get("/profile").get_data(as_text=True)
    href = _preset_href(home_body, "Last 6 Months")

    body = client.get(href).get_data(as_text=True)
    assert "Within every preset (today)" in body
    assert "Within Last 3 Months and Last 6 Months" in body
    assert "Within Last 6 Months only" in body
    assert "Outside every preset but All Time" not in body


def test_profile_custom_range_valid(client, seed_user):
    _login(client, seed_user)
    response = client.get("/profile?date_from=2026-08-04&date_to=2026-08-15")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Start date must be before end date." not in body
    assert "₹" in body
    assert "filter-custom--active" in body


def test_profile_reversed_range_flashes_and_falls_back(client, seed_user):
    _login(client, seed_user)
    response = client.get("/profile?date_from=2026-08-20&date_to=2026-08-02")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Start date must be before end date." in body
    assert "₹289.14" in body


def test_profile_malformed_date_falls_back_silently(client, seed_user):
    _login(client, seed_user)
    response = client.get("/profile?date_from=not-a-date&date_to=2026-08-20")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Start date must be before end date." not in body
    assert "₹289.14" in body


def test_profile_no_expenses_in_range_shows_zero_state(client, seed_user):
    _login(client, seed_user)
    response = client.get("/profile?date_from=2099-01-01&date_to=2099-01-31")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "₹0.00" in body
    assert "filter-custom--active" in body
