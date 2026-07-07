"""Hermetic tests for multi-trail routes: line concatenation/orientation, stat summing, the
enrichment gate, schema mapping, GPX over a combined line, and router validation wiring.

The spatial queries (candidates/connectivity) need PostGIS and are exercised live; everything
pure or pydantic-level is covered here (no DB, no network).
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from xml.etree import ElementTree

from fastapi.testclient import TestClient

from app.main import app
from app.models import CatalogTrail, TrailRoute, Trip
from app.schemas.trail_route import RouteTrailLite, TrailRouteDetailOut, TrailRouteSummaryOut
from app.schemas.trip import TripCreate, TripOut
from app.services.gpx import build_gpx
from app.services.trail_routes import concat_member_lines, pick_enrich_targets, route_stats

# [lon, lat] segments on a meridian: 0.001 deg of latitude is ~111 m, so joints/gaps below are
# in easy-to-reason meters. A runs north 0-111 m.
_A = [[0.0, 0.0], [0.0, 0.001]]


# --- concat_member_lines -------------------------------------------------------------------


def test_concat_single_and_empty() -> None:
    assert concat_member_lines([]) == []
    assert concat_member_lines([_A]) == _A


def test_concat_dedupes_a_shared_joint_vertex() -> None:
    b = [[0.0, 0.00102], [0.0, 0.002]]  # starts ~2 m from A's tail -> joint vertex dropped
    chain = concat_member_lines([_A, b])
    assert chain == [[0.0, 0.0], [0.0, 0.001], [0.0, 0.002]]


def test_concat_keeps_both_vertices_across_a_small_gap() -> None:
    b = [[0.0, 0.0012], [0.0, 0.002]]  # ~22 m gap: beyond joint dedupe, becomes a connector
    chain = concat_member_lines([_A, b])
    assert chain == [[0.0, 0.0], [0.0, 0.001], [0.0, 0.0012], [0.0, 0.002]]


def test_concat_flips_a_backwards_second_segment() -> None:
    b_reversed = [[0.0, 0.002], [0.0, 0.0012]]  # drawn away from the chain -> must flip
    chain = concat_member_lines([_A, b_reversed])
    assert chain == [[0.0, 0.0], [0.0, 0.001], [0.0, 0.0012], [0.0, 0.002]]


def test_concat_flips_a_backwards_first_segment() -> None:
    a_reversed = [[0.0, 0.001], [0.0, 0.0]]  # its *start* faces member 2 -> must flip
    b = [[0.0, 0.0012], [0.0, 0.002]]
    chain = concat_member_lines([a_reversed, b])
    assert chain == [[0.0, 0.0], [0.0, 0.001], [0.0, 0.0012], [0.0, 0.002]]


def test_concat_bridges_a_100m_gap_with_a_straight_connector() -> None:
    b = [[0.0, 0.0019], [0.0, 0.003]]  # ~100 m gap (the chain tolerance) - still one line
    chain = concat_member_lines([_A, b])
    assert len(chain) == 4
    assert chain[0] == [0.0, 0.0] and chain[-1] == [0.0, 0.003]


def test_concat_skips_degenerate_segments() -> None:
    assert concat_member_lines([[[0.0, 0.0]], _A]) == _A  # a 1-point fragment can't be a leg


# --- route_stats ---------------------------------------------------------------------------


def _member(metric=None, nominal=None, ascent=None, descent=None, ride=None, high=None, low=None):
    return SimpleNamespace(
        metric_length_mi=metric,
        length_mi=nominal,
        ascent_ft=ascent,
        descent_ft=descent,
        ride_time_min=ride,
        high_point_ft=high,
        low_point_ft=low,
    )


def test_route_stats_sums_and_extremes() -> None:
    stats = route_stats(
        [
            _member(metric=6.0, ascent=300, descent=250, ride=60, high=900, low=200),
            _member(metric=4.0, ascent=700, descent=600, ride=45, high=1500, low=400),
        ]
    )
    assert stats == {
        "trail_count": 2,
        "mapped_count": 2,
        "miles": 10.0,
        "ascent_ft": 1000,
        "descent_ft": 850,
        "ride_time_min": 105,
        "high_point_ft": 1500,
        "low_point_ft": 200,
    }


def test_route_stats_falls_back_to_nominal_length_and_counts_mapped_honestly() -> None:
    stats = route_stats([_member(metric=6.0, ascent=300), _member(nominal=3.5)])
    assert stats["miles"] == 9.5  # unmapped member still contributes its catalog length
    assert stats["mapped_count"] == 1 and stats["trail_count"] == 2
    assert stats["ascent_ft"] == 300  # summed over the members that have it
    assert stats["high_point_ft"] is None


def test_route_stats_all_unknown_is_none_not_zero() -> None:
    stats = route_stats([_member(), _member()])
    assert stats["miles"] is None and stats["ascent_ft"] is None and stats["ride_time_min"] is None
    assert stats["trail_count"] == 2 and stats["mapped_count"] == 0


def test_route_stats_empty() -> None:
    assert route_stats([])["trail_count"] == 0


# --- pick_enrich_targets -------------------------------------------------------------------


def test_pick_enrich_targets_skips_attempted_and_in_flight_and_caps() -> None:
    ids = [f"t{i}" for i in range(12)]
    picks = pick_enrich_targets(ids, attempted={"t0", "t3"}, in_flight={"t1"}, limit=8)
    assert picks == ["t2", "t4", "t5", "t6", "t7", "t8", "t9", "t10"]  # order kept, capped at 8
    assert pick_enrich_targets(ids, attempted=set(ids), in_flight=set()) == []


# --- schema mapping ------------------------------------------------------------------------


def _catalog(ext: str, name: str, lat: float, lon: float, **kw) -> CatalogTrail:
    return CatalogTrail(external_id=ext, name=name, lat=lat, lon=lon, **kw)


def test_route_trail_lite_maps_camel_case() -> None:
    t = _catalog("287262", "Sawyer Camp Trail", 37.531, -122.364,
                 difficulty="Easy", length_mi=12.0, metric_length_mi=6.2, ascent_ft=301,
                 ride_time_min=41)
    lite = RouteTrailLite.from_model(t, line=[[-122.36, 37.53], [-122.37, 37.54]])
    assert lite.id == "287262" and lite.metricLengthMi == 6.2 and lite.ascentFt == 301
    assert lite.linePoints == [[-122.36, 37.53], [-122.37, 37.54]]
    assert RouteTrailLite.from_model(t).linePoints is None


def test_summary_and_detail_out_mapping() -> None:
    route = TrailRoute(id=7, name="Sawyer + Crystal loop",
                       trail_external_ids=["a", "b"], created_at=datetime.now(UTC))
    members = [
        RouteTrailLite.from_model(_catalog("a", "A", 37.5, -122.4, metric_length_mi=6.0)),
        RouteTrailLite.from_model(_catalog("b", "B", 37.6, -122.5)),
    ]
    stats = {
        "trail_count": 2, "mapped_count": 1, "miles": 6.0, "ascent_ft": None,
        "descent_ft": None, "ride_time_min": None, "high_point_ft": None, "low_point_ft": None,
    }
    summary = TrailRouteSummaryOut.from_model(route, stats, wildlife_score=84)
    assert summary.trailCount == 2 and summary.mappedCount == 1 and summary.wildlifeScore == 84

    detail = TrailRouteDetailOut.from_detail(
        route, stats, 84, members, missing=["c"], line_points=[[0.0, 0.0], [0.0, 0.001]]
    )
    assert detail.missingTrailIds == ["c"]
    assert detail.startLat == 37.5 and detail.startLon == -122.4  # the first member's trailhead
    assert detail.members[1].linePoints is None


# --- GPX over a combined line --------------------------------------------------------------


def test_gpx_over_concatenated_route_line() -> None:
    combined = concat_member_lines([_A, [[0.0, 0.0012], [0.0, 0.002]]])
    xml = build_gpx("Sawyer + Crystal loop", combined, desc="2 trails · 10.0 mi")
    root = ElementTree.fromstring(xml)
    ns = "{http://www.topografix.com/GPX/1/1}"
    pts = root.findall(f"{ns}trk/{ns}trkseg/{ns}trkpt")
    assert len(pts) == 4  # both members included
    assert len(root.findall(f"{ns}trk/{ns}trkseg")) == 1  # one continuous segment
    assert root.find(f"{ns}trk/{ns}desc").text == "2 trails · 10.0 mi"


# --- router validation wiring (fires before any DB use) -------------------------------------


def test_create_rejects_too_few_trails() -> None:
    client = TestClient(app)
    assert client.post("/api/trail-routes", json={"name": "x", "trailIds": []}).status_code == 422
    assert client.post("/api/trail-routes", json={"name": "x", "trailIds": ["a"]}).status_code == 422


def test_create_rejects_blank_name_and_duplicates() -> None:
    client = TestClient(app)
    assert client.post("/api/trail-routes", json={"name": "   ", "trailIds": ["a", "b"]}).status_code == 422
    resp = client.post("/api/trail-routes", json={"name": "x", "trailIds": ["a", "a"]})
    assert resp.status_code == 422
    assert "once" in resp.json()["detail"]


def test_candidates_requires_ids() -> None:
    client = TestClient(app)
    assert client.get("/api/trail-routes/candidates").status_code == 422


# --- trips carry the route link -------------------------------------------------------------


def test_trip_route_id_round_trip() -> None:
    body = TripCreate(trailExternalId=None, routeId=7, trailName="Sawyer + Crystal loop")
    assert body.routeId == 7 and body.trailExternalId is None
    t = Trip(id=1, trail_external_id=None, route_id=7, trail_name="Sawyer + Crystal loop",
             ridden_on=datetime.now(UTC).date(), birds=[], created_at=datetime.now(UTC))
    assert TripOut.from_model(t, lifers=0).routeId == 7
