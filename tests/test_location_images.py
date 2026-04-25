from __future__ import annotations

from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.models import Account, BodyLocation


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG_BYTES = b"\xff\xd8\xff" + b"\x00" * 16


def _location(client, headers, *, code: str = "left_elbow") -> dict:
    response = client.post("/locations", headers=headers, json={"code": code, "display_name": "Left elbow"})
    assert response.status_code == 201
    return response.json()["location"]


def test_location_create_without_image_has_null_image(client, auth_headers):
    location = _location(client, auth_headers)
    assert location["image"] is None

    listing = client.get("/locations", headers=auth_headers)
    assert listing.status_code == 200
    assert listing.json()["locations"][0]["image"] is None


def test_upload_get_replace_and_delete_location_image(client, auth_headers):
    location = _location(client, auth_headers)

    uploaded = client.post(
        f"/locations/{location['id']}/image",
        headers=auth_headers,
        files={"image": ("left-elbow.png", PNG_BYTES, "image/png")},
    )
    assert uploaded.status_code == 200
    payload = uploaded.json()["location"]
    assert payload["image"]["mime_type"] == "image/png"
    assert payload["image"]["size_bytes"] == len(PNG_BYTES)
    assert payload["image"]["original_filename"] == "left-elbow.png"
    assert payload["image"]["url"] == f"/locations/{location['id']}/image"

    db = SessionLocal()
    try:
        stored = db.get(BodyLocation, location["id"])
        old_storage_key = stored.image_storage_key
        assert old_storage_key is not None
    finally:
        db.close()

    downloaded = client.get(f"/locations/{location['id']}/image", headers=auth_headers)
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"].startswith("image/png")
    assert downloaded.content == PNG_BYTES

    replaced = client.post(
        f"/locations/{location['id']}/image",
        headers=auth_headers,
        files={"image": ("left-elbow.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert replaced.status_code == 200
    replacement = replaced.json()["location"]["image"]
    assert replacement["mime_type"] == "image/jpeg"
    assert replacement["sha256"] != payload["image"]["sha256"]

    db = SessionLocal()
    try:
        stored = db.get(BodyLocation, location["id"])
        assert stored.image_storage_key != old_storage_key
    finally:
        db.close()

    deleted = client.delete(f"/locations/{location['id']}/image", headers=auth_headers)
    assert deleted.status_code == 200
    assert deleted.json()["location"]["image"] is None

    missing = client.get(f"/locations/{location['id']}/image", headers=auth_headers)
    assert missing.status_code == 404


def test_invalid_type_magic_mismatch_and_oversized_images_are_rejected(client, auth_headers, monkeypatch):
    location = _location(client, auth_headers)

    invalid_type = client.post(
        f"/locations/{location['id']}/image",
        headers=auth_headers,
        files={"image": ("bad.txt", b"hello", "text/plain")},
    )
    assert invalid_type.status_code == 422

    mismatch = client.post(
        f"/locations/{location['id']}/image",
        headers=auth_headers,
        files={"image": ("bad.png", b"not-a-png", "image/png")},
    )
    assert mismatch.status_code == 422

    from app.core.config import settings

    monkeypatch.setattr(settings, "location_image_max_bytes", 4)
    oversized = client.post(
        f"/locations/{location['id']}/image",
        headers=auth_headers,
        files={"image": ("big.png", PNG_BYTES, "image/png")},
    )
    assert oversized.status_code == 422


def test_unknown_and_cross_account_location_image_access_returns_404(client, auth_headers):
    unknown = client.get("/locations/9999/image", headers=auth_headers)
    assert unknown.status_code == 404

    db = SessionLocal()
    try:
        other = Account(username="other", password_hash=hash_password("other"), is_active=True)
        db.add(other)
        db.flush()
        location = BodyLocation(account_id=other.id, code="other_elbow", display_name="Other elbow")
        db.add(location)
        db.flush()
        other_location_id = location.id
        other_token = create_access_token(subject=str(other.id), account_id=other.id)
        db.commit()
    finally:
        db.close()

    blocked = client.post(
        f"/locations/{other_location_id}/image",
        headers=auth_headers,
        files={"image": ("left-elbow.png", PNG_BYTES, "image/png")},
    )
    assert blocked.status_code == 404

    allowed = client.post(
        f"/locations/{other_location_id}/image",
        headers={"Authorization": f"Bearer {other_token}"},
        files={"image": ("left-elbow.png", PNG_BYTES, "image/png")},
    )
    assert allowed.status_code == 200
