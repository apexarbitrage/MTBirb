"""Hermetic tests for TrailAPI catalog record mapping (no network, no database)."""

from app.schemas.catalog import CatalogTrailOut
from app.services.trail_catalog import _safe_float, record_to_catalog

RECORD = {
    "id": 280219,
    "name": "Bellingham DJ Park",
    "lat": "48.74620",
    "lon": "-122.45608",
    "difficulty": "Intermediate",
    "length": "1.0",
    "city": "Bellingham",
    "region": "Washington",
    "url": "https://example.com/dj-park",
}


def test_record_to_catalog_maps_fields() -> None:
    c = record_to_catalog(RECORD)
    assert c is not None
    assert c.external_id == "280219"
    assert (c.lat, c.lon) == (48.7462, -122.45608)
    assert c.length_mi == 1.0
    assert c.difficulty == "Intermediate"

    out = CatalogTrailOut.from_model(c)
    assert out.id == "280219"
    assert out.lengthMi == 1.0
    assert out.region == "Washington"


def test_record_without_coordinates_is_skipped() -> None:
    assert record_to_catalog({"id": 1, "name": "X", "lat": None, "lon": None}) is None
    assert record_to_catalog({"id": 1, "name": "X"}) is None


def test_record_without_id_is_skipped() -> None:
    assert record_to_catalog({"name": "X", "lat": "48", "lon": "-122"}) is None


def test_empty_difficulty_and_length_become_none() -> None:
    c = record_to_catalog({**RECORD, "difficulty": "", "length": ""})
    assert c is not None
    assert c.difficulty is None
    assert c.length_mi is None


def test_no_name_placeholder_is_normalized() -> None:
    assert record_to_catalog({**RECORD, "name": "no name"}).name == "Unnamed trail"
    assert record_to_catalog({**RECORD, "name": ""}).name == "Unnamed trail"
    assert record_to_catalog({**RECORD, "name": "Mrazek"}).name == "Mrazek"


def test_safe_float() -> None:
    assert _safe_float("1.0") == 1.0
    assert _safe_float(2) == 2.0
    assert _safe_float(None) is None
    assert _safe_float("") is None
    assert _safe_float("abc") is None
