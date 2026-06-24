"""Hermetic tests for the first-pass wildlife score + its presentation (no DB, no network)."""

from datetime import UTC, datetime, timedelta

from app.schemas.catalog import CatalogTrailOut
from app.services.trail_catalog import record_to_catalog
from app.services.wildlife_likelihood import _score_from_richness

RECORD = {
    "id": 287262,
    "name": "Sawyer Camp Trail",
    "lat": "37.531",
    "lon": "-122.364",
    "difficulty": "Easy",
    "length": "12.0",
}


def test_score_from_richness_monotonic_and_bounded() -> None:
    assert _score_from_richness(0) == 0
    assert _score_from_richness(-3) == 0
    # More species -> higher score, saturating below 100.
    scores = [_score_from_richness(n) for n in (5, 15, 30, 60, 200)]
    assert scores == sorted(scores)
    assert scores[-1] <= 98
    assert _score_from_richness(60) > _score_from_richness(15)


def test_from_model_attaches_wildlife_overlay() -> None:
    c = record_to_catalog(RECORD)
    now = datetime.now(UTC)
    score_info = {
        "score": 88,
        "species_count": 58,
        "top_species": [
            {"species_code": "acowoo", "common_name": "Acorn Woodpecker", "last_observed": now},
            {"species_code": "stejay", "common_name": "Steller's Jay", "last_observed": now},
            {"species_code": "annhum", "common_name": "Anna's Hummingbird", "last_observed": now},
            {"species_code": "amerob", "common_name": "American Robin", "last_observed": now},
        ],
    }
    out = CatalogTrailOut.from_model(c, score_info, lookback_days=30, with_factors=True)
    assert out.score == 88
    assert out.likelyBirds == ["Acorn Woodpecker", "Steller's Jay", "Anna's Hummingbird"]  # top 3
    assert out.metaBird == "Acorn Woodpecker"
    assert out.peak == "Acorn Woodpecker, Steller's Jay"  # top 2
    assert "58 species" in out.sightingHeadline
    # Factors are built from real signals and labelled by score/recency.
    labels = {f.label for f in out.factors}
    assert {"Species nearby", "Most recent report", "Top species"} <= labels
    species_factor = next(f for f in out.factors if f.label == "Species nearby")
    assert species_factor.value == "58 in 30d"
    assert species_factor.tone == "terracotta"  # score >= 70


def test_from_model_without_score_has_empty_overlay() -> None:
    out = CatalogTrailOut.from_model(record_to_catalog(RECORD))
    assert out.score is None
    assert out.likelyBirds == []
    assert out.factors == []


def test_from_model_no_recent_reports_headline() -> None:
    out = CatalogTrailOut.from_model(
        record_to_catalog(RECORD),
        {"score": 0, "species_count": 0, "top_species": []},
        with_factors=True,
    )
    assert out.score == 0
    assert out.sightingHeadline == "No recent eBird reports nearby"
    assert out.factors[1].value == "—"  # most-recent report when there are none


def test_recency_humanizes_days() -> None:
    week_ago = datetime.now(UTC) - timedelta(days=7)
    out = CatalogTrailOut.from_model(
        record_to_catalog(RECORD),
        {
            "score": 50,
            "species_count": 10,
            "top_species": [
                {"species_code": "x", "common_name": "Test Bird", "last_observed": week_ago}
            ],
        },
        with_factors=True,
    )
    assert out.factors[1].value == "7 days ago"
