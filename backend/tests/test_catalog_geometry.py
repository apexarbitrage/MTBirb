"""Hermetic tests for catalog OSM line matching (no network, no database)."""

from app.services.catalog_geometry import (
    _name_core,
    _name_match,
    _norm,
    best_line_for,
    stitch_ways,
)


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


def test_name_core_drops_generic_words() -> None:
    assert _name_core("Sawyer Camp Trail") == "sawyer.*camp"
    assert _name_core("Coal Creek Open Space Preserve") == "coal.*creek"
    # All-generic name falls back to the raw tokens rather than an empty regex.
    assert _name_core("The Loop Trail") == "the.*loop.*trail"


def test_stitch_chains_segments_in_order() -> None:
    # Three ways of one trail, given out of order and with one reversed; share exact endpoints.
    ways = [
        {"points": [(0.002, 0.0), (0.003, 0.0)]},  # third
        {"points": [(0.001, 0.0), (0.0, 0.0)]},  # first, reversed
        {"points": [(0.001, 0.0), (0.002, 0.0)]},  # middle
    ]
    chain = stitch_ways(ways, seed_lon=0.0, seed_lat=0.0)
    xs = [round(lon, 4) for lon, _ in chain]
    # Contiguous with no duplicated joints; overall direction follows the seed way's orientation.
    assert xs in ([0.0, 0.001, 0.002, 0.003], [0.003, 0.002, 0.001, 0.0])


def test_stitch_skips_disconnected_segment() -> None:
    ways = [
        {"points": [(0.0, 0.0), (0.001, 0.0)]},
        {"points": [(0.001, 0.0), (0.002, 0.0)]},
        {"points": [(5.0, 5.0), (5.001, 5.0)]},  # far away, must be dropped
    ]
    chain = stitch_ways(ways, seed_lon=0.0, seed_lat=0.0)
    assert chain == [(0.0, 0.0), (0.001, 0.0), (0.002, 0.0)]
