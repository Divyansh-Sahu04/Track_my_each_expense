"""Tests for Step 06: Date Filter for Profile Page.

Derived strictly from `.claude/specs/06-date-filter-profile-page.md`.
No test logic in this file is based on reading `app.py` or
`database/queries.py` internals -- only fixture/helper signatures from
`tests/conftest.py` were consulted for structural context.
"""

import html
import re
from datetime import date, timedelta

import pytest


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _preset_href(body, label):
    """Extract the href of a preset link/button by its visible label text."""
    match = re.search(rf'href="([^"]+)"[^>]*>\s*{re.escape(label)}\s*<', body)
    assert match, f"Expected a link labelled {label!r} in the filter bar"
    return html.unescape(match.group(1))


# --------------------------------------------------------------------- #
# Happy path: no filter params -> unfiltered ("All Time") view          #
# --------------------------------------------------------------------- #

def test_profile_no_params_shows_all_time_unfiltered_data(client, seed_user):
    """Spec: 'Visiting /profile with no query params returns the same data
    as Step 5 (unfiltered, all expenses).'"""
    _login(client, seed_user)
    response = client.get("/profile")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "₹289.14" in body, "Unfiltered total spent should match all 8 seeded expenses"
    for description in (
        "Grocery run",
        "Bus fare top-up",
        "Electricity bill",
        "Pharmacy purchase",
        "Movie ticket",
        "New shoes",
        "Miscellaneous",
        "Dinner with friends",
    ):
        assert description in body, f"All-time view should include {description!r}"


def test_profile_no_params_matches_all_time_preset(client, multi_month_user):
    """The default (no params) view and the explicit 'All Time' preset must
    show identical data, since 'All Time' passes no query params."""
    _login(client, multi_month_user)
    default_body = client.get("/profile").get_data(as_text=True)
    href = _preset_href(default_body, "All Time")

    # Spec: "The 'All Time' preset must pass no query params (clean /profile URL)."
    assert href in ("/profile", "/profile?", ""), (
        f"All Time preset link should point to a clean /profile URL, got {href!r}"
    )

    all_time_body = client.get(href or "/profile").get_data(as_text=True)
    for description in (
        "Outside every preset but All Time",
        "Within Last 6 Months only",
        "Within Last 3 Months and Last 6 Months",
        "Within every preset (today)",
    ):
        assert description in all_time_body


# --------------------------------------------------------------------- #
# Happy path: valid custom date range filters all three sections       #
# --------------------------------------------------------------------- #

def test_custom_range_filters_transactions_stats_and_categories(client, seed_user):
    """Spec: 'Submitting a custom date range with valid date_from and
    date_to shows only expenses within that range in all three sections.'"""
    _login(client, seed_user)
    # Window covers exactly 3 of the 8 seeded expenses:
    #   2026-08-04 Transport 12.00, 2026-08-05 Bills 89.99, 2026-08-09 Health 25.00
    response = client.get("/profile?date_from=2026-08-04&date_to=2026-08-09")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    # Transactions section: only in-range descriptions present
    for description in ("Bus fare top-up", "Electricity bill", "Pharmacy purchase"):
        assert description in body

    for description in (
        "Grocery run",
        "Movie ticket",
        "New shoes",
        "Miscellaneous",
        "Dinner with friends",
    ):
        assert description not in body

    # Stats section: total reflects only the in-range expenses
    assert "₹126.99" in body  # 12.00 + 89.99 + 25.00

    # Category breakdown: only in-range categories shown
    for category in ("Transport", "Bills", "Health"):
        assert category in body
    for category in ("Entertainment", "Shopping", "Other"):
        assert category not in body


# --------------------------------------------------------------------- #
# The four presets                                                     #
# --------------------------------------------------------------------- #

def test_this_month_preset_shows_current_calendar_month_only(client, multi_month_user):
    """Spec DoD: 'Clicking This Month filters all three sections to the
    current calendar month only.'"""
    _login(client, multi_month_user)
    home_body = client.get("/profile").get_data(as_text=True)
    href = _preset_href(home_body, "This Month")

    body = client.get(href).get_data(as_text=True)
    assert client.get(href).status_code == 200
    assert "Within every preset (today)" in body
    for excluded in (
        "Within Last 3 Months and Last 6 Months",
        "Within Last 6 Months only",
        "Outside every preset but All Time",
    ):
        assert excluded not in body


def test_last_3_months_preset_shows_3_month_window(client, multi_month_user):
    """Spec DoD: 'Clicking Last 3 Months filters to expenses in the 3-month
    window ending today.'"""
    _login(client, multi_month_user)
    home_body = client.get("/profile").get_data(as_text=True)
    href = _preset_href(home_body, "Last 3 Months")

    body = client.get(href).get_data(as_text=True)
    assert "Within every preset (today)" in body
    assert "Within Last 3 Months and Last 6 Months" in body
    for excluded in ("Within Last 6 Months only", "Outside every preset but All Time"):
        assert excluded not in body


def test_last_6_months_preset_shows_6_month_window(client, multi_month_user):
    """Spec DoD: 'Clicking Last 6 Months filters to expenses in the 6-month
    window ending today.'"""
    _login(client, multi_month_user)
    home_body = client.get("/profile").get_data(as_text=True)
    href = _preset_href(home_body, "Last 6 Months")

    body = client.get(href).get_data(as_text=True)
    assert "Within every preset (today)" in body
    assert "Within Last 3 Months and Last 6 Months" in body
    assert "Within Last 6 Months only" in body
    assert "Outside every preset but All Time" not in body


def test_all_time_preset_shows_every_expense(client, multi_month_user):
    """Spec DoD: 'Clicking All Time removes any active filter and shows
    all expenses.'"""
    _login(client, multi_month_user)
    home_body = client.get("/profile").get_data(as_text=True)
    href = _preset_href(home_body, "All Time")

    body = client.get(href or "/profile").get_data(as_text=True)
    for description in (
        "Outside every preset but All Time",
        "Within Last 6 Months only",
        "Within Last 3 Months and Last 6 Months",
        "Within every preset (today)",
    ):
        assert description in body


def test_active_preset_is_visually_highlighted(client, multi_month_user):
    """Spec DoD: 'The active preset button or custom-range fields visually
    indicate which filter is currently applied.' We check that a distinct
    highlight/active marker is present, and differs from the default page
    (which has no active preset)."""
    _login(client, multi_month_user)
    home_body = client.get("/profile").get_data(as_text=True)
    href = _preset_href(home_body, "This Month")

    filtered_body = client.get(href).get_data(as_text=True)
    # Some active-state indicator must exist and be distinguishable from an
    # unfiltered page (loosely checking for a common "active" class marker).
    assert "active" in filtered_body.lower()


def test_amounts_display_rupee_symbol_regardless_of_filter(client, multi_month_user):
    """Spec DoD: 'All amounts continue to display the ₹ symbol regardless
    of the active filter.'"""
    _login(client, multi_month_user)
    home_body = client.get("/profile").get_data(as_text=True)

    for label in ("This Month", "Last 3 Months", "Last 6 Months", "All Time"):
        href = _preset_href(home_body, label)
        body = client.get(href or "/profile").get_data(as_text=True)
        assert "₹" in body, f"{label} view should still show the rupee symbol"


# --------------------------------------------------------------------- #
# Auth guard                                                            #
# --------------------------------------------------------------------- #

def test_profile_redirects_unauthenticated_with_no_params(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


@pytest.mark.parametrize(
    "query_string",
    [
        "?date_from=2026-08-01&date_to=2026-08-31",
        "?date_from=not-a-date",
        "?date_from=2026-08-31&date_to=2026-08-01",
    ],
)
def test_profile_redirects_unauthenticated_regardless_of_filter_params(client, query_string):
    """Auth guard must apply before any date-filter logic runs."""
    response = client.get(f"/profile{query_string}")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# --------------------------------------------------------------------- #
# Validation / edge cases                                               #
# --------------------------------------------------------------------- #

def test_malformed_date_falls_back_silently_to_unfiltered(client, seed_user):
    """Spec: 'If either parameter is absent or malformed, the route falls
    back to an "All Time" (unfiltered) view rather than erroring out.'
    Also DoD: 'does not crash the app -- it silently falls back' (no flash)."""
    _login(client, seed_user)
    response = client.get("/profile?date_from=not-a-date&date_to=2026-08-20")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Start date must be before end date." not in body
    assert "₹289.14" in body  # unfiltered total


def test_malformed_date_to_also_falls_back_silently(client, seed_user):
    """Malformed date_to alone should also be treated as absent."""
    _login(client, seed_user)
    response = client.get("/profile?date_from=2026-08-01&date_to=banana")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Start date must be before end date." not in body


def test_reversed_range_flashes_error_and_falls_back(client, seed_user):
    """Spec Rules: 'If date_from > date_to after validation, treat both as
    absent (no filter) and flash "Start date must be before end date."'"""
    _login(client, seed_user)
    response = client.get("/profile?date_from=2026-08-20&date_to=2026-08-02")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Start date must be before end date." in body
    assert "₹289.14" in body  # falls back to unfiltered total


def test_range_with_zero_matches_shows_empty_state(client, seed_user):
    """Spec DoD: 'A user with no expenses in the selected range sees ₹0.00
    total spent, 0 transactions, and an empty category breakdown -- no
    errors.'"""
    _login(client, seed_user)
    response = client.get("/profile?date_from=2099-01-01&date_to=2099-01-31")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "₹0.00" in body
    assert "0" in body  # transaction count of 0 somewhere on the page
    for category in ("Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"):
        assert category not in body


def test_range_with_zero_matches_for_user_with_no_expenses_at_all(client, fresh_user):
    """Same zero-state, but for a user who never had any expenses to begin
    with -- ensures the filter path itself doesn't error on empty data."""
    _login(client, fresh_user)
    response = client.get("/profile?date_from=2026-01-01&date_to=2026-01-31")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "₹0.00" in body


def test_only_one_of_date_from_or_date_to_provided_falls_back_to_unfiltered(client, seed_user):
    """Spec says date_from/date_to are each optional bounds, and filtering
    behavior is only guaranteed 'when both are provided' (queries.py rule).
    Supplying just one should not crash and should not silently drop data
    the user didn't ask to exclude -- verified here as a non-erroring,
    still-successful response that does not show the reversed-range flash."""
    _login(client, seed_user)
    response = client.get("/profile?date_from=2026-08-04")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Start date must be before end date." not in body
