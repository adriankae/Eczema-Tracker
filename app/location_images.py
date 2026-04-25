from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import utc_now
from app.models import Account, BodyLocation
from app.services import get_location


ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


@dataclass(frozen=True)
class StoredLocationImage:
    path: Path
    mime_type: str


def _storage_root() -> Path:
    root = Path(settings.location_image_dir).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _safe_storage_path(storage_key: str) -> Path:
    root = _storage_root()
    candidate = (root / storage_key).resolve()
    if root != candidate and root not in candidate.parents:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="invalid image storage path")
    return candidate


def _magic_matches(mime_type: str, data: bytes) -> bool:
    if mime_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if mime_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/webp":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return False


def _validate_image(upload: UploadFile, data: bytes) -> str:
    mime_type = upload.content_type or ""
    if mime_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="unsupported image type")
    if not data:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="image is empty")
    if len(data) > settings.location_image_max_bytes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="image is too large")
    if not _magic_matches(mime_type, data):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="image content does not match type")
    return mime_type


def _generate_storage_key(location: BodyLocation, mime_type: str) -> str:
    extension = ALLOWED_IMAGE_TYPES[mime_type]
    return f"account-{location.account_id}/location-{location.id}/{uuid.uuid4().hex}{extension}"


def _delete_key_best_effort(storage_key: str | None) -> None:
    if not storage_key:
        return
    try:
        _safe_storage_path(storage_key).unlink(missing_ok=True)
    except OSError:
        pass


async def store_location_image(db: Session, account: Account, location_id: int, upload: UploadFile) -> BodyLocation:
    location = get_location(db, account, location_id)
    data = await upload.read()
    mime_type = _validate_image(upload, data)
    storage_key = _generate_storage_key(location, mime_type)
    path = _safe_storage_path(storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

    old_storage_key = location.image_storage_key
    location.image_storage_key = storage_key
    location.image_mime_type = mime_type
    location.image_size_bytes = len(data)
    location.image_sha256 = hashlib.sha256(data).hexdigest()
    location.image_original_filename = Path(upload.filename or "").name[:255] or None
    location.image_uploaded_at = utc_now()
    db.add(location)
    try:
        db.commit()
    except Exception:
        db.rollback()
        _delete_key_best_effort(storage_key)
        raise
    db.refresh(location)
    _delete_key_best_effort(old_storage_key)
    return location


def get_location_image_file(db: Session, account: Account, location_id: int) -> StoredLocationImage:
    location = get_location(db, account, location_id)
    if not location.image_storage_key or not location.image_mime_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="location image not found")
    path = _safe_storage_path(location.image_storage_key)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="location image not found")
    return StoredLocationImage(path=path, mime_type=location.image_mime_type)


def remove_location_image(db: Session, account: Account, location_id: int) -> BodyLocation:
    location = get_location(db, account, location_id)
    if not location.image_storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="location image not found")

    old_storage_key = location.image_storage_key
    location.image_storage_key = None
    location.image_mime_type = None
    location.image_size_bytes = None
    location.image_sha256 = None
    location.image_original_filename = None
    location.image_uploaded_at = None
    db.add(location)
    db.commit()
    db.refresh(location)
    _delete_key_best_effort(old_storage_key)
    return location
