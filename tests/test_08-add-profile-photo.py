"""Tests for the Add Profile Photo feature (Step 8): GET/POST /profile/photo
and POST /profile/photo/remove. Based strictly on
.claude/specs/08-add-profile-photo.md."""

import io
import os

import pytest

import app as flask_app_module
from database.db import get_db


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _photo_file(filename="photo.jpg", size=1024, content=b"\xff\xd8\xff"):
    """Build a multipart file payload of `size` bytes (content padded)."""
    body = content + b"0" * max(0, size - len(content))
    return {"photo": (io.BytesIO(body), filename)}


def _photo_filename(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT photo_filename FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row["photo_filename"] if row else None


@pytest.fixture
def upload_folder(tmp_path, monkeypatch):
    """Point app.UPLOAD_FOLDER at a disposable tmp directory so tests never
    read or write the real static/uploads/profile_photos/ directory."""
    folder = tmp_path / "profile_photos"
    monkeypatch.setattr(flask_app_module, "UPLOAD_FOLDER", str(folder), raising=False)
    return str(folder)


def _upload_folder_is_empty(upload_folder):
    return not os.path.isdir(upload_folder) or not os.listdir(upload_folder)


# --- GET /profile/photo ---

def test_get_profile_photo_unauthenticated_redirects_to_login(client):
    response = client.get("/profile/photo")
    assert response.status_code == 302, "Expected redirect for unauthenticated access"
    assert "/login" in response.headers["Location"]


def test_get_profile_photo_authenticated_no_photo_shows_initials_and_form(client, fresh_user):
    _login(client, fresh_user)
    response = client.get("/profile/photo")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "NE" in body, "Expected initials avatar for 'New User' (no photo yet)"
    assert "<form" in body, "Expected an upload form"
    assert 'type="file"' in body, "Expected a file input for the photo upload"


# --- POST /profile/photo — auth guard ---

def test_post_profile_photo_unauthenticated_redirects_to_login(client):
    response = client.post(
        "/profile/photo",
        data=_photo_file(),
        content_type="multipart/form-data",
    )
    assert response.status_code == 302, "Expected redirect for unauthenticated access"
    assert "/login" in response.headers["Location"]


# --- POST /profile/photo/remove — auth guard ---

def test_post_remove_photo_unauthenticated_redirects_to_login(client):
    response = client.post("/profile/photo/remove")
    assert response.status_code == 302, "Expected redirect for unauthenticated access"
    assert "/login" in response.headers["Location"]


# --- POST /profile/photo — valid uploads ---

def test_post_profile_photo_valid_jpg_redirects_updates_db_and_saves_file(
    client, fresh_user, upload_folder
):
    _login(client, fresh_user)
    response = client.post(
        "/profile/photo",
        data=_photo_file(filename="photo.jpg", size=1024),
        content_type="multipart/form-data",
    )

    assert response.status_code == 302, "Expected redirect to /profile on success"
    assert "/profile" in response.headers["Location"]

    filename = _photo_filename(fresh_user)
    assert filename is not None, "Expected photo_filename to be set in the DB"
    assert filename.endswith(".jpg")
    assert os.path.exists(os.path.join(upload_folder, filename)), (
        "Expected the uploaded file to be saved on disk"
    )


def test_post_profile_photo_valid_png_redirects_updates_db_and_saves_file(
    client, fresh_user, upload_folder
):
    _login(client, fresh_user)
    response = client.post(
        "/profile/photo",
        data=_photo_file(filename="photo.png", size=1024, content=b"\x89PNG\r\n"),
        content_type="multipart/form-data",
    )

    assert response.status_code == 302, "Expected redirect to /profile on success"

    filename = _photo_filename(fresh_user)
    assert filename is not None, "Expected photo_filename to be set in the DB"
    assert filename.endswith(".png")
    assert os.path.exists(os.path.join(upload_folder, filename)), (
        "Expected the uploaded file to be saved on disk"
    )


def test_get_profile_after_upload_shows_photo_not_initials(client, fresh_user, upload_folder):
    _login(client, fresh_user)
    client.post(
        "/profile/photo",
        data=_photo_file(filename="photo.jpg", size=1024),
        content_type="multipart/form-data",
    )

    response = client.get("/profile")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "<img" in body, "Expected an <img> tag once a photo has been uploaded"
    assert 'class="profile-avatar"' not in body, (
        "Expected the initials avatar to be replaced by the photo"
    )


# --- POST /profile/photo — validation errors ---

def test_post_profile_photo_non_image_txt_rejected_no_db_or_file_changes(
    client, fresh_user, upload_folder
):
    _login(client, fresh_user)
    response = client.post(
        "/profile/photo",
        data=_photo_file(filename="note.txt", size=100, content=b"just some text"),
        content_type="multipart/form-data",
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200, "Expected the upload form to be re-rendered, not a redirect"
    assert "error" in body.lower() or "only" in body.lower(), "Expected a flashed error message"
    assert _photo_filename(fresh_user) is None, "Expected no DB change on rejected upload"
    assert _upload_folder_is_empty(upload_folder), "Expected no file to be saved"


def test_post_profile_photo_pdf_rejected_no_db_or_file_changes(client, fresh_user, upload_folder):
    _login(client, fresh_user)
    response = client.post(
        "/profile/photo",
        data=_photo_file(filename="document.pdf", size=100, content=b"%PDF-1.4"),
        content_type="multipart/form-data",
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200, "Expected the upload form to be re-rendered, not a redirect"
    assert "error" in body.lower() or "only" in body.lower(), "Expected a flashed error message"
    assert _photo_filename(fresh_user) is None, "Expected no DB change on rejected upload"
    assert _upload_folder_is_empty(upload_folder), "Expected no file to be saved"


def test_post_profile_photo_oversized_rejected_no_db_or_file_changes(
    client, fresh_user, upload_folder
):
    _login(client, fresh_user)
    oversized = 2 * 1024 * 1024 + 1  # 1 byte over the spec's 2MB limit
    response = client.post(
        "/profile/photo",
        data=_photo_file(filename="big.jpg", size=oversized),
        content_type="multipart/form-data",
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200, "Expected the upload form to be re-rendered, not a redirect"
    assert (
        "error" in body.lower() or "size" in body.lower() or "2mb" in body.lower()
    ), "Expected a flashed error message about the file being too large"
    assert _photo_filename(fresh_user) is None, "Expected no DB change on rejected upload"
    assert _upload_folder_is_empty(upload_folder), "Expected no file to be saved"


def test_post_profile_photo_zero_byte_file_rejected(client, fresh_user, upload_folder):
    _login(client, fresh_user)
    response = client.post(
        "/profile/photo",
        data={"photo": (io.BytesIO(b""), "photo.jpg")},
        content_type="multipart/form-data",
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200, "Expected the upload form to be re-rendered, not a redirect"
    assert "error" in body.lower(), "Expected a flashed error message for an empty file"
    assert _photo_filename(fresh_user) is None, "Expected no DB change on rejected upload"
    assert _upload_folder_is_empty(upload_folder), "Expected no file to be saved"


# --- POST /profile/photo/remove ---

def test_post_remove_photo_clears_db_deletes_file_and_reverts_to_initials(
    client, fresh_user, upload_folder
):
    _login(client, fresh_user)
    client.post(
        "/profile/photo",
        data=_photo_file(filename="photo.jpg", size=1024),
        content_type="multipart/form-data",
    )
    filename = _photo_filename(fresh_user)
    assert filename is not None, "Sanity check: photo should be set before removal"
    saved_path = os.path.join(upload_folder, filename)
    assert os.path.exists(saved_path), "Sanity check: file should exist before removal"

    response = client.post("/profile/photo/remove")

    assert response.status_code == 302, "Expected redirect to /profile"
    assert "/profile" in response.headers["Location"]
    assert _photo_filename(fresh_user) is None, "Expected photo_filename to be cleared in the DB"
    assert not os.path.exists(saved_path), "Expected the stored file to be deleted"

    profile_response = client.get("/profile")
    profile_body = profile_response.get_data(as_text=True)
    assert 'class="profile-avatar"' in profile_body, "Expected the initials avatar to reappear"
    assert "profile-avatar-img" not in profile_body, "Expected no <img> avatar after removal"


# --- Re-uploading replaces the old file rather than orphaning it ---

def test_reupload_new_photo_replaces_old_file_on_disk(client, fresh_user, upload_folder):
    _login(client, fresh_user)
    client.post(
        "/profile/photo",
        data=_photo_file(filename="photo.jpg", size=1024),
        content_type="multipart/form-data",
    )
    old_filename = _photo_filename(fresh_user)
    old_path = os.path.join(upload_folder, old_filename)
    assert os.path.exists(old_path), "Sanity check: first upload should be saved"

    client.post(
        "/profile/photo",
        data=_photo_file(filename="photo.png", size=1024, content=b"\x89PNG\r\n"),
        content_type="multipart/form-data",
    )
    new_filename = _photo_filename(fresh_user)
    new_path = os.path.join(upload_folder, new_filename)

    assert new_filename != old_filename, "Expected the stored filename to change with the new extension"
    assert not os.path.exists(old_path), "Expected the old file to be removed, not left orphaned"
    assert os.path.exists(new_path), "Expected the new file to be saved"

    conn = get_db()
    row = conn.execute(
        "SELECT photo_filename FROM users WHERE id = ?", (fresh_user,)
    ).fetchone()
    conn.close()
    assert row["photo_filename"] == new_filename, "Expected the DB to reflect only the new filename"
