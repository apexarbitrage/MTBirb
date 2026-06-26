"""Hermetic tests for slope aspect / sun-exposure and OSM surface summary (no network, no DB)."""

import asyncio

from app.integrations.osm import summarize_surface
from app.services.trail_surface import aspect_from_neighbors, compute_aspect


def test_summarize_surface_most_common_and_hardest_scale() -> None:
    ways = [
        {"tags": {"surface": "ground", "mtb:scale": "2"}},
        {"tags": {"surface": "ground"}},
        {"tags": {"surface": "gravel", "mtb:scale": "4"}},
    ]
    s = summarize_surface(ways)
    assert s["surface"] == "Ground"  # most common
    assert s["mtb_scale"] == "4"  # hardest


def test_summarize_surface_titlecases_and_handles_missing() -> None:
    assert summarize_surface([{"tags": {"surface": "fine_gravel"}}])["surface"] == "Fine Gravel"
    empty = summarize_surface([{"tags": {}}, {}])
    assert empty["surface"] is None
    assert empty["mtb_scale"] is None


def test_aspect_south_facing_is_sunny_north_hemisphere() -> None:
    # Higher to the north -> the hillside faces south (sunny in the N hemisphere).
    a = aspect_from_neighbors(north=110, south=90, east=100, west=100, offset_m=50, lat=37)
    assert a["aspect"] == "S"
    assert a["sun_exposure"] > 0.95


def test_aspect_north_facing_is_shaded() -> None:
    a = aspect_from_neighbors(north=90, south=110, east=100, west=100, offset_m=50, lat=37)
    assert a["aspect"] == "N"
    assert a["sun_exposure"] < 0.05


def test_aspect_east_uphill_faces_west() -> None:
    a = aspect_from_neighbors(north=100, south=100, east=110, west=90, offset_m=50, lat=37)
    assert a["aspect"] == "W"


def test_aspect_flat_is_neutral() -> None:
    a = aspect_from_neighbors(100, 100, 100, 100, 50, 37)
    assert a["slope"] == 0.0
    assert a["sun_exposure"] == 0.5


def test_aspect_southern_hemisphere_flips_exposure() -> None:
    # A south-facing slope is the *shaded* one below the equator.
    a = aspect_from_neighbors(north=110, south=90, east=100, west=100, offset_m=50, lat=-33)
    assert a["aspect"] == "S"
    assert a["sun_exposure"] < 0.05


class _PlanarClient:
    """Elevation rises steeply to the north -> the whole trail faces south."""

    source = "usgs"

    async def lookup(self, points: list[tuple[float, float]]) -> list[float]:
        return [(lat - 37.0) * 100_000.0 for lat, _lon in points]


def test_compute_aspect_planar_south_facing() -> None:
    samples = [(37.0 + i * 0.001, -122.0) for i in range(6)]
    result = asyncio.run(compute_aspect(_PlanarClient(), samples, "usgs"))
    assert result["aspect"] == "S"
    assert result["sun_exposure"] > 0.9


def test_compute_aspect_flat_returns_none() -> None:
    class _FlatClient:
        source = "usgs"

        async def lookup(self, points):
            return [100.0 for _ in points]

    samples = [(37.0 + i * 0.001, -122.0) for i in range(6)]
    result = asyncio.run(compute_aspect(_FlatClient(), samples, "usgs"))
    assert result["aspect"] is None
    assert result["sun_exposure"] is None
