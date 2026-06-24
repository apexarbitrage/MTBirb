"""Hermetic tests for the recency-decayed + notable wildlife score and its presentation."""

from datetime import UTC, datetime, timedelta

from app.schemas.catalog import CatalogTrailOut
from app.services.trail_catalog import record_to_catalog
from app.services.wildlife_likelihood import (
    _recency_weight,
    _saturating_score,
    _score_from_richness,
)

RECORD = {
    "id": 287262,
    "name": "Sawyer Camp Trail",
    "lat": "37.531",
    "lon": "-122.364",
    "difficulty": "Easy",
    "length": "12.0",
}


def _species(name, days_ago, notable=False):
    now = datetime.now(UTC)
    last = now - timedelta(days=days_ago)
    return {
        "species_code": name[:6].lower(),
        "common_name": name,
        "last_observed": last,
        "notable": notable,
        "weight": _recency_weight(last, now),
    }


def test_saturating_score_bounds_and_monotonic() -> None:
    assert _saturating_score(0, 10) == 0
    assert _saturating_score(-1, 10) == 0
    vals = [_saturating_score(x, 10) for x in (1, 5, 20, 100)]
    assert vals == sorted(vals)
    assert vals[-1] <= 98


def test_recency_weight_decays_with_age() -> None:
    now = datetime.now(UTC)
    fresh = _recency_weight(now, now)
    week = _recency_weight(now - timedelta(days=7), now)
    month = _recency_weight(now - timedelta(days=30), now)
    assert fresh > week > month
    assert abs(fresh - 1.0) < 1e-6  # seen "now" -> full weight
    assert month < 0.3  # a month stale -> faded
    assert _recency_weight(None, now) == 0.3  # unknown date -> small floor


def test_score_from_richness_still_saturates() -> None:
    assert _score_from_richness(0) == 0
    assert _score_from_richness(60) > _score_from_richness(15)


def test_overlay_prefers_notable_for_peak_and_headline() -> None:
    c = record_to_catalog(RECORD)
    score_info = {
        "score": 84,
        "notable_score": 61,
        "species_count": 40,
        "notable_count": 2,
        "top_species": [
            _species("Northern Mockingbird", 0),
            _species("Rock Pigeon", 1),
            _species("Acorn Woodpecker", 2),
        ],
        "top_notable": [_species("Northern Gannet", 1, True), _species("Laughing Gull", 3, True)],
    }
    out = CatalogTrailOut.from_model(c, score_info, with_factors=True)
    assert out.score == 84
    assert out.notableScore == 61
    # likely = common recent species; notable = the rare hook
    assert out.likelyBirds[0] == "Northern Mockingbird"
    assert out.notableBirds == ["Northern Gannet", "Laughing Gull"]
    assert out.peak == "Northern Gannet, Laughing Gull"  # peak draws from notable, not pigeons
    assert out.metaBird == "Northern Gannet"
    assert "Northern Gannet" in out.sightingHeadline and "notable" in out.sightingHeadline
    labels = [f.label for f in out.factors]
    assert labels == ["Notable nearby", "Species activity", "Most recent report"]
    assert out.factors[0].value == "2 species"


def test_overlay_falls_back_to_likely_when_no_notable() -> None:
    out = CatalogTrailOut.from_model(
        record_to_catalog(RECORD),
        {
            "score": 70,
            "notable_score": 0,
            "species_count": 12,
            "notable_count": 0,
            "top_species": [_species("Mallard", 0), _species("Canada Goose", 1)],
            "top_notable": [],
        },
        with_factors=True,
    )
    assert out.notableBirds == []
    assert out.peak == "Mallard, Canada Goose"  # no notable -> likely
    assert "12 species reported nearby recently" == out.sightingHeadline
    assert out.factors[0].value == "0 species"  # notable nearby


def test_overlay_empty_without_score() -> None:
    out = CatalogTrailOut.from_model(record_to_catalog(RECORD))
    assert out.score is None
    assert out.notableScore is None
    assert out.likelyBirds == [] and out.notableBirds == []
    assert out.factors == []
