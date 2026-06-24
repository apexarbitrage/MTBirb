"""Hermetic tests for the eBird -> WildlifeSighting mapping (no network, no database)."""

from datetime import datetime, timezone

from app.services.wildlife_sync import _parse_obs_dt, observation_to_sighting

SAMPLE = {
    "speciesCode": "grhowl",
    "comName": "Great Horned Owl",
    "sciName": "Bubo virginianus",
    "obsDt": "2026-06-23 14:54",
    "lat": 48.8222,
    "lng": -122.5870,
    "subId": "S362332545",
    "locationPrivate": True,
}


def test_parse_obs_dt_with_time() -> None:
    assert _parse_obs_dt("2026-06-23 14:54") == datetime(2026, 6, 23, 14, 54, tzinfo=timezone.utc)


def test_parse_obs_dt_date_only() -> None:
    assert _parse_obs_dt("2026-06-23") == datetime(2026, 6, 23, tzinfo=timezone.utc)


def test_observation_to_sighting_maps_fields() -> None:
    s = observation_to_sighting(SAMPLE)
    assert s is not None
    assert s.source == "ebird"
    assert s.species_code == "grhowl"
    assert s.common_name == "Great Horned Owl"
    assert s.checklist_id == "S362332545"
    assert s.is_obscured is False
    assert s.observed_at == datetime(2026, 6, 23, 14, 54, tzinfo=timezone.utc)
    assert s.geom is not None


def test_observation_without_coordinates_is_skipped() -> None:
    obscured = {k: v for k, v in SAMPLE.items() if k not in ("lat", "lng")}
    assert observation_to_sighting(obscured) is None
