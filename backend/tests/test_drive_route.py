"""Hermetic tests for the drive-route geometry (no network, no database)."""

from app.services.drive_route import curviness, sample_waypoints


def _straight_north(n: int = 20) -> list[list[float]]:
    return [[-122.0, 37.0 + i * 0.002] for i in range(n)]


def _zigzag(n: int = 20) -> list[list[float]]:
    # Alternate east/west while creeping north -> a hard turn at every point.
    pts = []
    for i in range(n):
        lon = -122.0 + (0.003 if i % 2 else 0.0)
        pts.append([lon, 37.0 + i * 0.001])
    return pts


def test_curviness_straight_line_is_mellow() -> None:
    c = curviness(_straight_north())
    assert c["curve_count"] == 0
    assert c["score"] == 0
    assert c["label"] == "Mellow"


def test_curviness_zigzag_is_twisty() -> None:
    c = curviness(_zigzag())
    assert c["curve_count"] > 10
    assert c["score"] >= 50
    assert c["label"] in {"Twisty", "Very twisty"}


def test_curviness_handles_degenerate() -> None:
    assert curviness([])["score"] == 0
    assert curviness([[-122.0, 37.0], [-122.0, 37.1]])["curve_count"] == 0


def test_sample_waypoints_count_and_interior() -> None:
    points = _straight_north(50)
    wps = sample_waypoints(points, n=8)
    assert len(wps) == 8
    # None coincide with the start or end.
    assert points[0] not in wps and points[-1] not in wps
    # Latitudes strictly increasing and bounded inside the route.
    lats = [lat for _lon, lat in wps]
    assert lats == sorted(lats)
    assert points[0][1] < lats[0] and lats[-1] < points[-1][1]


def test_sample_waypoints_degenerate() -> None:
    assert sample_waypoints([[-122.0, 37.0], [-122.0, 37.1]], n=8) == []
    assert sample_waypoints(_straight_north(), n=0) == []
