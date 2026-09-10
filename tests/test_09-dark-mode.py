"""Tests for the Dark Mode / Appearance Setting feature (Step 9):
POST /profile/appearance and the theme-preference contract it establishes.
Based strictly on .claude/specs/09-dark-mode.md.

Covers:
- Auth guard on the update endpoint
- HTTP semantics (POST-only, redirect targets, open-redirect protection)
- Validation of the `theme` value with a flashed error and no DB change
- DB side effects: theme_preference is persisted per-user and survives
  logout/login
- Template contract: data-theme-preference reflects the stored value for
  logged-in users and defaults to 'system' for logged-out visitors, with no
  DB dependency pre-login
- Stylesheet audit: no hardcoded hex colors outside CSS variable
  declarations (the spec's "CSS variables only" rule made load-bearing)
"""

import os
import re
import sqlite3

import pytest

import database.db as db
from database.db import get_db


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _theme_preference(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT theme_preference FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row["theme_preference"] if row else None


def _data_theme_preference(body):
    """Extract the data-theme-preference attribute value from an HTML body."""
    match = re.search(r'data-theme-preference="([^"]*)"', body)
    return match.group(1) if match else None


# --- Auth guard ---

def test_post_appearance_unauthenticated_redirects_to_login(client):
    response = client.post("/profile/appearance", data={"theme": "dark"})
    assert response.status_code == 302, "Expected redirect for unauthenticated access"
    assert "/login" in response.headers["Location"]


def test_post_appearance_unauthenticated_makes_no_db_change(client, fresh_user):
    client.post("/profile/appearance", data={"theme": "dark"})
    assert _theme_preference(fresh_user) == "system", (
        "Expected no DB change from an unauthenticated request"
    )


# --- HTTP semantics: POST-only endpoint ---

def test_get_appearance_not_allowed(client, fresh_user):
    _login(client, fresh_user)
    response = client.get("/profile/appearance")
    assert response.status_code in (404, 405), (
        "Spec defines /profile/appearance as a POST-only update endpoint"
    )


# --- Default value ---

def test_new_user_defaults_to_system_theme(fresh_user):
    assert _theme_preference(fresh_user) == "system", (
        "Expected users.theme_preference to default to 'system'"
    )


# --- Schema back-fill on a pre-existing database ---

def test_init_db_backfills_theme_preference_on_existing_users_table(tmp_path, monkeypatch):
    """CREATE TABLE IF NOT EXISTS is a no-op against a users table that
    predates theme_preference, so init_db() must add the column itself
    for anyone with an existing local database."""
    db_path = str(tmp_path / "pre_existing.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            photo_filename TEXT
        )
    """)
    conn.commit()
    conn.close()

    monkeypatch.setattr(db, "DB_PATH", db_path)
    db.init_db()

    conn = sqlite3.connect(db_path)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    conn.close()
    assert "theme_preference" in columns, (
        "Expected init_db() to back-fill theme_preference onto a pre-existing users table"
    )


# --- Happy path: valid theme values persist ---

@pytest.mark.parametrize("theme", ["system", "light", "dark"])
def test_post_valid_theme_redirects_and_persists(client, fresh_user, theme):
    _login(client, fresh_user)
    response = client.post("/profile/appearance", data={"theme": theme})

    assert response.status_code == 302, "Expected a redirect on a valid theme update"
    assert _theme_preference(fresh_user) == theme, (
        f"Expected theme_preference to be persisted as {theme!r}"
    )


def test_post_valid_theme_updates_from_existing_value(client, fresh_user):
    _login(client, fresh_user)
    client.post("/profile/appearance", data={"theme": "dark"})
    assert _theme_preference(fresh_user) == "dark"

    client.post("/profile/appearance", data={"theme": "light"})
    assert _theme_preference(fresh_user) == "light", (
        "Expected the preference to be overwritten by a subsequent valid update"
    )


# --- Redirect target ("next") handling ---

def test_post_appearance_without_next_redirects_to_profile(client, fresh_user):
    _login(client, fresh_user)
    response = client.post("/profile/appearance", data={"theme": "dark"})
    assert response.status_code == 302
    assert "/profile" in response.headers["Location"], (
        "Expected a fallback redirect to /profile when no 'next' is supplied"
    )


def test_post_appearance_with_safe_next_redirects_there(client, fresh_user):
    _login(client, fresh_user)
    response = client.post(
        "/profile/appearance", data={"theme": "dark", "next": "/analytics"}
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/analytics"), (
        "Expected redirect to honor a same-site 'next' path"
    )


def test_post_appearance_with_external_next_falls_back_to_profile(client, fresh_user):
    _login(client, fresh_user)
    response = client.post(
        "/profile/appearance",
        data={"theme": "dark", "next": "http://evil.example.com/steal"},
    )
    assert response.status_code == 302
    location = response.headers["Location"]
    assert "evil.example.com" not in location, (
        "Expected an absolute external URL to be rejected as a redirect target"
    )
    assert "/profile" in location


def test_post_appearance_with_protocol_relative_next_falls_back_to_profile(
    client, fresh_user
):
    _login(client, fresh_user)
    response = client.post(
        "/profile/appearance",
        data={"theme": "dark", "next": "//evil.example.com/steal"},
    )
    assert response.status_code == 302
    location = response.headers["Location"]
    assert "evil.example.com" not in location, (
        "Expected a protocol-relative '//' next value to be rejected"
    )
    assert "/profile" in location


def test_post_appearance_with_backslash_next_falls_back_to_profile(client, fresh_user):
    _login(client, fresh_user)
    response = client.post(
        "/profile/appearance",
        data={"theme": "dark", "next": "/\\evil.example.com/steal"},
    )
    assert response.status_code == 302
    location = response.headers["Location"]
    assert "evil.example.com" not in location, (
        "Expected a backslash-based next value to be rejected "
        "(browsers normalize '/\\' to '//', making it protocol-relative)"
    )
    assert "/profile" in location


# --- Validation errors ---

@pytest.mark.parametrize("bad_theme", ["blue", "SYSTEM", "Dark", "", "light ", "1"])
def test_post_invalid_theme_rejected_no_db_change(client, fresh_user, bad_theme):
    _login(client, fresh_user)
    response = client.post(
        "/profile/appearance",
        data={"theme": bad_theme, "next": "/profile"},
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200, "Expected the redirect target to render successfully"
    assert "flash-error" in body or "error" in body.lower(), (
        "Expected a flashed error message for an invalid theme value"
    )
    assert _theme_preference(fresh_user) == "system", (
        "Expected no DB change when the submitted theme is invalid"
    )


def test_post_missing_theme_field_rejected_no_db_change(client, fresh_user):
    _login(client, fresh_user)
    response = client.post("/profile/appearance", data={})
    assert response.status_code == 302, "Expected a redirect even on validation failure"
    assert _theme_preference(fresh_user) == "system", (
        "Expected no DB change when the theme field is absent"
    )


# --- Template contract: data-theme-preference reflects stored value ---

def test_logged_out_visitor_sees_system_theme_preference_attribute(client):
    response = client.get("/")
    body = response.get_data(as_text=True)
    assert _data_theme_preference(body) == "system", (
        "Expected logged-out visitors to get 'system' with no DB read"
    )


def test_logged_in_user_sees_persisted_dark_preference_on_profile_page(
    client, fresh_user
):
    _login(client, fresh_user)
    client.post("/profile/appearance", data={"theme": "dark"})

    response = client.get("/profile")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert _data_theme_preference(body) == "dark", (
        "Expected the rendered page to reflect the persisted 'dark' preference"
    )


def test_logged_in_user_sees_persisted_light_preference_on_profile_page(
    client, fresh_user
):
    _login(client, fresh_user)
    client.post("/profile/appearance", data={"theme": "light"})

    response = client.get("/profile")
    body = response.get_data(as_text=True)
    assert _data_theme_preference(body) == "light", (
        "Expected the rendered page to reflect the persisted 'light' preference"
    )


# --- Persistence across logout/login ---

def test_theme_preference_persists_across_logout_and_login(client, fresh_user):
    _login(client, fresh_user)
    client.post("/profile/appearance", data={"theme": "dark"})
    client.get("/logout")

    assert _theme_preference(fresh_user) == "dark", (
        "Expected the preference to remain in the DB after logout"
    )

    _login(client, fresh_user)
    response = client.get("/profile")
    body = response.get_data(as_text=True)
    assert _data_theme_preference(body) == "dark", (
        "Expected the preference to be re-applied after logging back in"
    )


def test_theme_preference_is_per_user_not_global(client, fresh_user, seed_user):
    _login(client, fresh_user)
    client.post("/profile/appearance", data={"theme": "dark"})

    assert _theme_preference(fresh_user) == "dark"
    assert _theme_preference(seed_user) == "system", (
        "Expected changing one user's theme to have no effect on another user's row"
    )


# --- Flash-of-wrong-theme avoidance: inline script runs before first paint ---

def test_base_html_resolves_theme_before_first_paint(client):
    response = client.get("/")
    body = response.get_data(as_text=True)
    head_section = body.split("</head>")[0] if "</head>" in body else body
    assert "prefers-color-scheme" in head_section, (
        "Expected the system-preference resolution logic to run inline in <head>, "
        "before first paint, to avoid a flash of the wrong theme"
    )
    assert "<script" in head_section


# --- Stylesheet audit: CSS-variables-only rule (spec DoD item) ---

def _read_stylesheet():
    css_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "static", "css", "style.css",
    )
    with open(css_path, "r", encoding="utf-8") as f:
        return f.read()


def test_stylesheet_has_no_hardcoded_hex_outside_variable_declarations():
    """Per spec: 'Every color in every stylesheet must be a CSS variable —
    no exceptions'. Hex values are only permitted where a custom property is
    being *defined* (e.g. `--ink: #0f0f0f;`); any hex value used directly in
    a regular property (e.g. `color: #0f0f0f;`) would break dark mode."""
    css = _read_stylesheet()

    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    offending_lines = []
    for line in css.splitlines():
        stripped = line.strip()
        if not hex_pattern.search(stripped):
            continue
        # A CSS custom-property *declaration* looks like `--name: #hex;`
        if re.match(r"^--[\w-]+\s*:\s*#[0-9a-fA-F]{3,8}\s*;?\s*$", stripped):
            continue
        offending_lines.append(stripped)

    assert not offending_lines, (
        "Expected no hardcoded hex colors outside CSS variable declarations "
        f"(dark mode would visibly break for these lines): {offending_lines}"
    )


def test_stylesheet_defines_dark_theme_variable_overrides():
    css = _read_stylesheet()
    assert '[data-theme="dark"]' in css, (
        "Expected a [data-theme=\"dark\"] block overriding CSS variables"
    )
