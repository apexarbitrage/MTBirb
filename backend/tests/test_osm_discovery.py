"""Hermetic tests for OSM catalog discovery: grouping, stitching guards, id stability, the
difficulty mapping, row building, and the pure dedup/donation planner. No network, no DB - the
Overpass fetch is exercised through a fake client (`discover_trails`'s DB writes are thin and
covered by the live smoke test, like enrich_region)."""

from types import SimpleNamespace

from app.services.osm_discovery import (
    _MAX_ROWS_PER_CALL,
    _difficulty_from_scale,
    _external_id,
    grid_cells,
    group_named_ways,
    group_to_catalog,
    plan_discovery,
)

# Ways on a meridian: 0.001 deg latitude ~ 111 m. Two connected ways forming ~444 m of "Coyote
# Ridge Trail" (comfortably above the 250 m fragment floor).
def _way(osm_id, name, points, tags=None):
    return {"osm_id": osm_id, "name": name, "tags": {**(tags or {}), **({"name": name} if name else {})}, "points": points}


def _ridge_ways():
    return [
        _way(101, "Coyote Ridge Trail", [(0.0, 0.0), (0.0, 0.002)], {"surface": "dirt"}),
        _way(102, "Coyote Ridge Trail", [(0.0, 0.002), (0.0, 0.004)], {"mtb:scale": "2"}),
    ]


# --- grouping -------------------------------------------------------------------------------


def test_grouping_drops_unnamed_and_groups_norm_equal_names() -> None:
    ways = _ridge_ways() + [
        _way(103, None, [(0.1, 0.0), (0.1, 0.004)]),
        _way(104, "  ", [(0.2, 0.0), (0.2, 0.004)]),
        _way(105, "COYOTE-RIDGE trail", [(0.0, 0.004), (0.0, 0.006)]),  # norm-equal variant
        _way(106, "Bay Ridge Trail", [(0.3, 0.0), (0.3, 0.004)]),  # distinct name stays separate
    ]
    groups = group_named_ways(ways)
    assert set(groups) == {"coyote ridge trail", "bay ridge trail"}
    assert {w["osm_id"] for w in groups["coyote ridge trail"]} == {101, 102, 105}


# --- external id ----------------------------------------------------------------------------


def test_external_id_stable_under_ordering() -> None:
    group = _ridge_ways()
    assert _external_id(group) == _external_id(list(reversed(group))) == "osm-101"
    assert len(_external_id(group)) <= 50


# --- difficulty mapping ---------------------------------------------------------------------


def test_difficulty_from_scale_buckets() -> None:
    assert _difficulty_from_scale("0") == "Easy"
    assert _difficulty_from_scale("1") == "Easy"
    assert _difficulty_from_scale("1+") == "Easy"  # leading-digit rank
    assert _difficulty_from_scale("2") == "Intermediate"
    assert _difficulty_from_scale("3") == "Intermediate"
    assert _difficulty_from_scale("4") == "Advanced"
    assert _difficulty_from_scale("6") == "Advanced"
    assert _difficulty_from_scale("weird") is None
    assert _difficulty_from_scale(None) is None


# --- row building ---------------------------------------------------------------------------


def test_group_to_catalog_builds_full_row() -> None:
    group = _ridge_ways()
    chain = [(0.0, 0.0), (0.0, 0.002), (0.0, 0.004)]
    row = group_to_catalog("Coyote Ridge Trail", group, chain)
    assert row.source == "osm"
    assert row.external_id == "osm-101"
    assert row.name == "Coyote Ridge Trail"
    assert (row.lon, row.lat) == (0.0, 0.0)  # trailhead = chain start
    assert "POINT(0.0 0.0)" in str(row.geom)
    assert str(row.line_geom).startswith("LINESTRING(0.0 0.0, 0.0 0.002")
    assert row.length_mi == 0.3  # ~444 m
    assert row.surface == "Dirt" and row.mtb_scale == "2"
    assert row.difficulty == "Intermediate"
    assert row.url == "https://www.openstreetmap.org/way/101"


def test_group_to_catalog_truncates_long_names() -> None:
    row = group_to_catalog("x" * 300, _ridge_ways(), [(0.0, 0.0), (0.0, 0.004)])
    assert len(row.name) == 200


# --- planner: fragments, dedup, donation ----------------------------------------------------


def _existing(id=1, external_id="287262", name="Coyote Ridge Trail", lat=0.001, lon=0.0, has_line=False):
    return SimpleNamespace(id=id, external_id=external_id, name=name, lat=lat, lon=lon, has_line=has_line)


def test_plan_skips_fragments() -> None:
    scrap = [_way(201, "Tiny Spur", [(0.5, 0.0), (0.5, 0.001)])]  # ~111 m < 250 m floor
    plan = plan_discovery(scrap, [])
    assert plan["new_trails"] == [] and plan["skipped"] == 1


def test_plan_keeps_largest_component_of_a_split_group() -> None:
    # Two same-named pieces 5+ km apart: stitching from the longest keeps it, drops the far spur.
    ways = _ridge_ways() + [_way(300, "Coyote Ridge Trail", [(0.0, 0.05), (0.0, 0.052)])]
    plan = plan_discovery(ways, [])
    assert len(plan["new_trails"]) == 1
    assert plan["new_trails"][0].length_mi == 0.3  # the ~444 m component, not the spur


def test_plan_dedups_against_lined_existing_row() -> None:
    plan = plan_discovery(_ridge_ways(), [_existing(has_line=True)])
    assert plan["new_trails"] == [] and plan["donations"] == [] and plan["skipped"] == 1


def test_plan_donates_line_to_lineless_existing_row() -> None:
    plan = plan_discovery(_ridge_ways(), [_existing(id=42, has_line=False)])
    assert plan["new_trails"] == []
    assert len(plan["donations"]) == 1
    row_id, chain, group = plan["donations"][0]
    assert row_id == 42
    assert len(chain) >= 3 and {w["osm_id"] for w in group} == {101, 102}


def test_plan_far_same_name_row_is_a_new_trail() -> None:
    far = _existing(lat=0.05, lon=0.0)  # ~5.5 km away - beyond the 2 km dedup radius
    plan = plan_discovery(_ridge_ways(), [far])
    assert len(plan["new_trails"]) == 1 and plan["donations"] == []


def test_plan_skips_already_known_external_id() -> None:
    plan = plan_discovery(_ridge_ways(), [_existing(external_id="osm-101", lat=0.9, lon=0.9)])
    assert plan["new_trails"] == [] and plan["skipped"] == 1


def test_plan_caps_rows_per_call() -> None:
    # Distinct, well-separated named ways; each long enough to pass the fragment floor.
    ways = [
        _way(1000 + i, f"Trail Number {i}", [(i * 0.1, 0.0), (i * 0.1, 0.004)])
        for i in range(_MAX_ROWS_PER_CALL + 5)
    ]
    plan = plan_discovery(ways, [])
    assert len(plan["new_trails"]) == _MAX_ROWS_PER_CALL
    assert plan["skipped"] == 5


# --- grid sweep math ------------------------------------------------------------------------


def test_grid_cells_cover_box() -> None:
    cells = grid_cells((37.0, 37.3), (-122.3, -122.0), step=0.15)
    assert len(cells) == 4  # 2 x 2 at 0.15 pitch over a 0.3-degree box
    lats = {lat for lat, _ in cells}
    assert all(37.0 <= lat <= 37.3 for lat in lats)


# --- fake-client end-to-end (no HTTP, no DB) ------------------------------------------------


def test_discover_trails_wires_fetch_and_inserts(monkeypatch) -> None:
    import asyncio

    from app.services import osm_discovery

    class FakeOverpass:
        def __init__(self):
            self.calls = []

        async def fetch_ways(self, south, west, north, east, timeout=25, named_only=False):
            self.calls.append({"bbox": (south, west, north, east), "named_only": named_only})
            return _ridge_ways()

    class FakeDb:
        def __init__(self):
            self.added = []
            self.committed = False

        def add(self, obj):
            self.added.append(obj)

        def get(self, model, row_id):
            raise AssertionError("no donations expected")

        def commit(self):
            self.committed = True

    monkeypatch.setattr(osm_discovery, "_existing_rows", lambda *a: [])
    client, db = FakeOverpass(), FakeDb()
    result = asyncio.run(osm_discovery.discover_trails(db, 0.002, 0.0, client=client))

    assert len(client.calls) == 1 and client.calls[0]["named_only"] is True
    south, west, north, east = client.calls[0]["bbox"]
    assert south < 0.002 < north and west < 0.0 < east  # bbox brackets the request point
    assert result["added"] == 1 and result["donated"] == 0
    assert db.committed and db.added[0].external_id == "osm-101"


# --- browse-gate cell key + admin gate wiring ------------------------------------------------


def test_osm_cell_buckets_points() -> None:
    from app.routers.catalog import _osm_cell

    assert _osm_cell(37.531, -122.364) == _osm_cell(37.529, -122.361)  # ~same area, one cell
    assert _osm_cell(37.531, -122.364) != _osm_cell(37.72, -122.364)  # ~20 km apart, new cell


def test_discover_osm_endpoint_is_admin_gated() -> None:
    """503 (fail-closed, ADMIN_TOKEN unset) even with valid params - the guard fires before any
    Overpass/DB work, mirroring test_admin_guard's discipline."""
    from fastapi.testclient import TestClient

    from app.main import app

    resp = TestClient(app).post(
        "/api/catalog/discover-osm?south=37.0&west=-122.5&north=37.3&east=-122.2"
    )
    assert resp.status_code == 503


# --- source surfacing ------------------------------------------------------------------------


def test_catalog_out_carries_source() -> None:
    from app.schemas.catalog import CatalogTrailOut
    from app.services.trail_catalog import record_to_catalog

    osm_row = group_to_catalog("Coyote Ridge Trail", _ridge_ways(), [(0.0, 0.0), (0.0, 0.004)])
    assert CatalogTrailOut.from_model(osm_row).source == "osm"

    trailapi_row = record_to_catalog({"id": 1, "name": "Sawyer Camp", "lat": "37.5", "lon": "-122.4"})
    assert CatalogTrailOut.from_model(trailapi_row).source == "trailapi"
