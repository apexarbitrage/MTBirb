"""Hermetic tests for catalog OSM line matching (no network, no database)."""

from app.services.catalog_geometry import _name_match, _norm, best_line_for


def test_name_match() -> None:
    assert _name_match(_norm("Sawyer Camp Trail"), _norm("Sawyer Camp Trail"))
    assert _name_match(_norm("Interurban Tr"), _norm("Interurban Trail"))  # substring
    assert _name_match(_norm("Purisima Creek Trail"), _norm("Purisima Creek"))  # token overlap
    assert not _name_match(_norm("Sawyer Camp Trail"), _norm("Mrazek"))


def test_best_line_prefers_name_match_over_distance() -> None:
    ways = [
        {"name": "Random Path", "points": [(-122.0, 37.0), (-122.001, 37.001)]},  # nearest, wrong name
        {"name": "Sawyer Camp Trail", "points": [(-122.5, 37.5), (-122.501, 37.5)]},  # match, far
    ]
    assert best_line_for("Sawyer Camp Trail", -122.0, 37.0, ways) == ways[1]["points"]


def test_best_line_falls_back_to_nearest_unnamed() -> None:
    ways = [
        {"name": None, "points": [(-122.0, 37.0), (-122.001, 37.001)]},
        {"name": None, "points": [(-122.5, 37.5), (-122.501, 37.5)]},
    ]
    assert best_line_for("Whatever", -122.0, 37.0, ways) == ways[0]["points"]


def test_best_line_empty() -> None:
    assert best_line_for("X", 0.0, 0.0, []) is None
