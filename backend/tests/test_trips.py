"""Hermetic tests for trip lifer keys and serialization (no DB, no network)."""

from datetime import UTC, date, datetime

from app.models import Trip
from app.routers.trips import _bird_key
from app.schemas.trip import TripOut


def test_bird_key_prefers_code_then_normalized_name() -> None:
    assert _bird_key({"species_code": "normoc", "common_name": "Northern Mockingbird"}) == "normoc"
    assert _bird_key({"species_code": None, "common_name": "Wild Turkey"}) == "wild turkey"
    assert _bird_key({"common_name": "  Heron "}) == "heron"


def test_tripout_maps_birds_and_lifers() -> None:
    t = Trip(
        id=1,
        trail_external_id="287262",
        trail_name="Sawyer Camp Trail",
        difficulty="Easy",
        miles=6.0,
        ridden_on=date(2026, 6, 20),
        birds=[
            {"species_code": "normoc", "common_name": "Northern Mockingbird"},
            {"species_code": None, "common_name": "Wild Turkey"},
        ],
        created_at=datetime.now(UTC),
    )
    out = TripOut.from_model(t, lifers=2)
    assert out.trailName == "Sawyer Camp Trail"
    assert out.riddenOn == date(2026, 6, 20)
    assert out.lifers == 2
    assert out.birds[0].speciesCode == "normoc"
    assert out.birds[1].speciesCode is None
    assert [b.commonName for b in out.birds] == ["Northern Mockingbird", "Wild Turkey"]
