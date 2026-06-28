"""Hermetic tests for the custom trail-photo version token + schema wiring (no DB, no network)."""

from datetime import UTC, datetime

from app.models import CatalogTrail
from app.schemas.catalog import CatalogTrailOut
from app.services.trail_photos import photo_version


def test_photo_version_none_when_no_photo() -> None:
    assert photo_version(None) is None


def test_photo_version_is_compact_epoch_token() -> None:
    dt = datetime(2026, 6, 28, 12, 0, 0, tzinfo=UTC)
    assert photo_version(dt) == str(int(dt.timestamp()))


def test_photo_version_changes_with_timestamp() -> None:
    a = datetime(2026, 6, 28, 12, 0, 0, tzinfo=UTC)
    b = datetime(2026, 6, 28, 12, 0, 1, tzinfo=UTC)
    assert photo_version(a) != photo_version(b)


def test_catalog_out_carries_photo_version() -> None:
    trail = CatalogTrail(external_id="287262", name="Sawyer Camp Trail", lat=37.5, lon=-122.3)
    out = CatalogTrailOut.from_model(trail, None, photo_version="1750000000")
    assert out.photoVersion == "1750000000"


def test_catalog_out_photo_version_defaults_none() -> None:
    trail = CatalogTrail(external_id="287262", name="Sawyer Camp Trail", lat=37.5, lon=-122.3)
    assert CatalogTrailOut.from_model(trail, None).photoVersion is None
