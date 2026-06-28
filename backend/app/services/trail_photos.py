"""Rider-supplied hero photos for catalog trails.

No accounts yet, so this is one global photo per trail (the latest upload wins), keyed by the
catalog `external_id`. The image is stored as bytes and served from a dedicated endpoint; the
JSON catalog responses carry only a small `photoVersion` token (derived from `updated_at`) so the
image URL can be long-cached yet bust on change.
"""

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TrailPhoto


def photo_version(dt: datetime | None) -> str | None:
    """A compact cache-busting token for a photo's URL, or None when there's no photo."""
    return str(int(dt.timestamp())) if dt is not None else None


def get_photo(db: Session, external_id: str) -> TrailPhoto | None:
    return db.scalar(select(TrailPhoto).where(TrailPhoto.trail_external_id == external_id))


def upsert_photo(db: Session, external_id: str, image: bytes, content_type: str) -> TrailPhoto:
    """Create or replace the trail's photo, returning the persisted row (with a fresh version)."""
    photo = get_photo(db, external_id)
    if photo is None:
        photo = TrailPhoto(trail_external_id=external_id, image=image, content_type=content_type)
        db.add(photo)
    else:
        photo.image = image
        photo.content_type = content_type
    db.commit()
    db.refresh(photo)
    return photo


def delete_photo(db: Session, external_id: str) -> bool:
    """Remove the trail's photo if present; returns whether a row was deleted."""
    photo = get_photo(db, external_id)
    if photo is None:
        return False
    db.delete(photo)
    db.commit()
    return True


def versions_for(db: Session, external_ids: Iterable[str]) -> dict[str, str | None]:
    """Map each external id that has a photo to its version token (one query, for list responses)."""
    ids = list(external_ids)
    if not ids:
        return {}
    rows = db.execute(
        select(TrailPhoto.trail_external_id, TrailPhoto.updated_at).where(
            TrailPhoto.trail_external_id.in_(ids)
        )
    ).all()
    return {ext: photo_version(dt) for ext, dt in rows}
