"""Unit tests for the trail API mapping and seed data.

These deliberately avoid a live database: they exercise the column -> response mapping and
the seed fixture's shape, which is the logic added when wiring the frontend to the backend.
Endpoint behavior against Postgres/PostGIS is covered by the app's manual/integration runs.
"""

from app.models import Trail
from app.schemas.trail import TrailOut
from app.seed import TRAIL_SEED

VALID_TONES = {"terracotta", "sage"}


def _make_trail() -> Trail:
    return Trail(
        slug="raptor",
        name="Raptor Ridge",
        source="seed",
        difficulty="Advanced",
        miles=8.4,
        effort=8.7,
        features=["Rock garden", "Drops"],
        ride_time_min=65,
        location="Galbraith Mtn · Bellingham, WA",
        gain_ft=2050,
        climb_ft=2050,
        descent_ft=2180,
        avg_up_grade="9.2%",
        avg_down_grade="7.8%",
        elevation=[0.1, 0.5, 0.2],
        derived={
            "score": 94,
            "likelyBirds": ["Northern Goshawk"],
            "sightingHeadline": "94% chance of a notable encounter this morning",
            "factors": [{"label": "Seasonality", "value": "Peak", "pct": 90, "tone": "terracotta"}],
            "bestWindow": "6:10 – 8:30 AM",
        },
    )


def test_trail_out_maps_columns_and_derived() -> None:
    out = TrailOut.from_model(_make_trail())

    # slug is exposed as the client-facing id; snake_case columns become camelCase
    assert out.id == "raptor"
    assert out.diff == "Advanced"
    assert out.rideTime == 65
    assert out.gainFt == 2050
    assert out.avgDownGrade == "7.8%"

    # fields from the derived overlay are spread onto the response
    assert out.score == 94
    assert out.likelyBirds == ["Northern Goshawk"]
    assert out.factors[0].tone == "terracotta"
    assert out.bestWindow == "6:10 – 8:30 AM"


def test_trail_out_tolerates_empty_derived() -> None:
    trail = _make_trail()
    trail.derived = None
    out = TrailOut.from_model(trail)
    assert out.score is None
    assert out.likelyBirds == []
    assert out.factors == []


def test_seed_data_is_well_formed() -> None:
    slugs = [t["slug"] for t in TRAIL_SEED]
    assert slugs == ["raptor", "owl", "cedar", "marsh"]
    assert len(set(slugs)) == len(slugs)

    for entry in TRAIL_SEED:
        derived = entry["derived"]
        assert isinstance(derived["score"], int)
        assert derived["likelyBirds"], f"{entry['slug']} should list likely birds"
        for factor in derived["factors"]:
            assert factor["tone"] in VALID_TONES
            assert 0 <= factor["pct"] <= 100
