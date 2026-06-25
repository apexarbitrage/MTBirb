"""Hermetic tests for OSM way parsing/selection (no network, no database)."""

from app.integrations.osm import parse_ways
from app.services.trail_geometry import _best_way


def test_parse_ways_keeps_only_ways_with_geometry() -> None:
    elements = [
        {"type": "node", "id": 1, "lat": 48.7, "lon": -122.4},  # dropped: not a way
        {"type": "way", "id": 2, "tags": {"name": "Olé"}},  # dropped: no geometry
        {"type": "way", "id": 3, "geometry": [{"lat": 48.7, "lon": -122.4}]},  # dropped: 1 pt
        {
            "type": "way",
            "id": 4,
            "tags": {"name": "Karma", "highway": "path"},
            "geometry": [{"lat": 48.7, "lon": -122.4}, {"lat": 48.71, "lon": -122.41}],
        },
    ]
    ways = parse_ways(elements)
    assert len(ways) == 1
    assert ways[0]["osm_id"] == 4
    assert ways[0]["name"] == "Karma"
    assert ways[0]["points"] == [(-122.4, 48.7), (-122.41, 48.71)]


def test_best_way_prefers_named_then_most_points() -> None:
    ways = [
        {"name": None, "points": [(0, 0)] * 10},
        {"name": "Olé", "points": [(0, 0)] * 5},
        {"name": "Karma", "points": [(0, 0)] * 8},
    ]
    assert _best_way(ways)["name"] == "Karma"


def test_best_way_falls_back_to_unnamed() -> None:
    ways = [{"name": None, "points": [(0, 0)] * 3}, {"name": None, "points": [(0, 0)] * 7}]
    assert len(_best_way(ways)["points"]) == 7


def test_best_way_empty() -> None:
    assert _best_way([]) is None
