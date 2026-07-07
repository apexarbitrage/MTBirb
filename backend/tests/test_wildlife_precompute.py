"""The precomputed (stored-on-row) wildlife score: trimming a live score dict to the JSON subset
the trail LIST reads, and confirming that trimmed dict still drives the list overlay correctly.

This is the safety net for the list precompute: the list must render from `_score_to_json`'s output
exactly as it did from the full live dict, so we don't have to keep scoring live per request.
"""

from datetime import UTC, datetime, timedelta

from app.schemas.catalog import CatalogTrailOut
from app.services.trail_catalog import record_to_catalog
from app.services.wildlife_likelihood import _STORED_TOP_N, _recency_weight, _score_to_json

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
        "species_code": name[:6].lower().replace(" ", ""),
        "common_name": name,
        "last_observed": last,
        "notable": notable,
        "season": 1.0,
        "weight": _recency_weight(last, now),
    }


def _live_info():
    """A dict shaped exactly like one entry of score_catalog_trails' result."""
    return {
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


def test_score_to_json_keeps_only_the_list_facing_subset() -> None:
    stored = _score_to_json(_live_info())
    # Scalars carried through verbatim.
    assert stored["score"] == 84
    assert stored["notable_score"] == 61
    assert stored["species_count"] == 40
    assert stored["notable_count"] == 2
    # Species trimmed to name + code only - no datetimes or weights (not JSON-serializable / unused).
    assert stored["top_species"][0] == {"species_code": "northe", "common_name": "Northern Mockingbird"}
    for s in stored["top_species"] + stored["top_notable"]:
        assert set(s.keys()) == {"species_code", "common_name"}
        assert "last_observed" not in s and "weight" not in s
    assert [s["common_name"] for s in stored["top_notable"]] == ["Northern Gannet", "Laughing Gull"]


def test_score_to_json_caps_the_species_lists() -> None:
    info = {
        "score": 50,
        "notable_score": 0,
        "species_count": 30,
        "notable_count": 0,
        "top_species": [_species(f"Bird {i}", i) for i in range(30)],
        "top_notable": [],
    }
    stored = _score_to_json(info)
    assert len(stored["top_species"]) == _STORED_TOP_N  # bounded so the JSON blob stays small
    assert stored["top_notable"] == []


def test_stored_dict_drives_the_list_overlay_like_the_live_dict() -> None:
    """The whole point: the list (with_factors=False) reads the trimmed stored dict and produces
    the same overlay it would from the full live dict - species counts come from the stored ints,
    not list length, so trimming to 5 names doesn't change the headline."""
    stored = _score_to_json(_live_info())
    out = CatalogTrailOut.from_model(record_to_catalog(RECORD), stored)  # with_factors defaults False
    assert out.score == 84
    assert out.notableScore == 61
    assert out.likelyBirds[0] == "Northern Mockingbird"
    assert out.notableBirds == ["Northern Gannet", "Laughing Gull"]
    assert out.peak == "Northern Gannet, Laughing Gull"
    assert out.metaBird == "Northern Gannet"
    # notable_count (2) survives trimming, so the headline still counts both.
    assert "Northern Gannet" in out.sightingHeadline
    assert out.factors == []  # the list carries no factors


def test_stored_empty_area_renders_no_reports() -> None:
    """A trail with no nearby sightings stores a zero score (not null), and the list shows the
    honest 'no reports' overlay rather than an empty one."""
    empty = _score_to_json(
        {
            "score": 0,
            "notable_score": 0,
            "species_count": 0,
            "notable_count": 0,
            "top_species": [],
            "top_notable": [],
        }
    )
    out = CatalogTrailOut.from_model(record_to_catalog(RECORD), empty)
    assert out.score == 0
    assert out.likelyBirds == []
    assert out.sightingHeadline == "No recent eBird reports nearby"
