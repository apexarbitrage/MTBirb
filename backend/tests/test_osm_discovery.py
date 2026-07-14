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


# --- Overpass 429 handling -------------------------------------------------------------------


def test_check_rate_limit_raises_with_retry_after() -> None:
    import httpx
    import pytest

    from app.integrations.osm import OverpassRateLimited, _check_rate_limit

    with pytest.raises(OverpassRateLimited) as exc:
        _check_rate_limit(httpx.Response(429, headers={"Retry-After": "30"}))
    assert exc.value.retry_after == 30.0

    with pytest.raises(OverpassRateLimited) as exc:
        _check_rate_limit(httpx.Response(429))  # no header -> caller picks its own cooldown
    assert exc.value.retry_after is None

    with pytest.raises(OverpassRateLimited) as exc:
        _check_rate_limit(httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}))
    assert exc.value.retry_after is None  # HTTP-date form ignored

    _check_rate_limit(httpx.Response(200))  # non-429 passes through untouched
    _check_rate_limit(httpx.Response(504))  # other errors stay raise_for_status's job


def test_overpass_url_comes_from_settings(monkeypatch) -> None:
    from app.integrations import osm

    monkeypatch.setattr(
        osm, "get_settings", lambda: SimpleNamespace(overpass_url="https://mirror.example/api")
    )
    assert osm.OverpassClient()._url == "https://mirror.example/api"
    # A blank env value must not disable the client.
    monkeypatch.setattr(osm, "get_settings", lambda: SimpleNamespace(overpass_url=""))
    assert osm.OverpassClient()._url == osm.OVERPASS_URL
    # An explicit URL always wins.
    assert osm.OverpassClient(url="http://x")._url == "http://x"


def _grid_harness(monkeypatch, fetch_behavior, lat_range=(0.0, 0.35)):
    """Run discover_grid over an N x 1-cell box (default 2 cells at the 0.15 pitch) with a
    scripted fetch and recorded sleeps."""
    import asyncio

    from app.services import osm_discovery

    sleeps: list[float] = []

    async def fake_sleep(s):
        sleeps.append(s)

    class FakeClient:
        def __init__(self):
            self.fetches = 0
            self.url = "fake://overpass"

        async def fetch_ways(self, *a, **kw):
            self.fetches += 1
            return fetch_behavior(self.fetches)

    monkeypatch.setattr(osm_discovery, "count_nearby", lambda *a, **kw: 0)
    monkeypatch.setattr(osm_discovery, "_existing_rows", lambda *a: [])
    monkeypatch.setattr(osm_discovery.asyncio, "sleep", fake_sleep)
    client = FakeClient()

    class FakeDb:
        def add(self, obj): ...
        def get(self, model, row_id): ...
        def commit(self): ...

    result = asyncio.run(
        osm_discovery.discover_grid(
            FakeDb(), lat_range, (0.0, 0.1), max_calls=10, client=client
        )
    )
    return result, client, sleeps


def test_grid_cools_down_and_retries_on_rate_limit(monkeypatch) -> None:
    from app.integrations.osm import OverpassRateLimited

    def behavior(n):
        if n == 1:
            raise OverpassRateLimited(retry_after=90.0)
        return []  # retry + later cells succeed (empty area)

    result, client, sleeps = _grid_harness(monkeypatch, behavior)
    assert result["rateLimited"] is False
    assert 90.0 in sleeps  # honored the (longer) Retry-After as the cooldown
    assert client.fetches == 3  # cell 1 twice (429 then ok) + cell 2 once


def test_grid_stops_when_rate_limit_persists(monkeypatch) -> None:
    from app.integrations.osm import OverpassRateLimited

    def behavior(n):
        raise OverpassRateLimited(retry_after=None)

    result, client, sleeps = _grid_harness(monkeypatch, behavior)
    assert result["rateLimited"] is True
    assert client.fetches == 2  # one cell, two attempts - remaining cells untouched
    assert result["calls"] == 2
    assert 60.0 in sleeps  # default cooldown when no Retry-After


def test_grid_aborts_after_consecutive_failures(monkeypatch) -> None:
    def behavior(n):
        raise RuntimeError("overpass melted")

    # 7 cells available; the sweep must stop at the 5-failure threshold, not churn through all.
    result, client, sleeps = _grid_harness(monkeypatch, behavior, lat_range=(0.0, 1.0))
    assert result["aborted"] is True and client.fetches == 5


def test_grid_success_resets_failure_streak(monkeypatch) -> None:
    def behavior(n):
        if n == 3:
            return []  # one success mid-run breaks the streak
        raise RuntimeError("flaky")

    result, client, sleeps = _grid_harness(monkeypatch, behavior, lat_range=(0.0, 1.0))
    # Failures: cells 1,2 (streak 2) - success cell 3 resets - failures 4..7 (streak 4) < 5.
    assert result["aborted"] is False and client.fetches == 7


# --- Overpass timeouts are "busy" signals ----------------------------------------------------


def test_run_translates_read_timeout_to_busy(monkeypatch) -> None:
    import asyncio

    import httpx
    import pytest

    from app.integrations import osm

    class FakeAsyncClient:
        def __init__(self, *a, **kw): ...
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **kw):
            raise httpx.ReadTimeout("queued past the read timeout")

    monkeypatch.setattr(osm.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        osm, "get_settings", lambda: SimpleNamespace(overpass_url="", weather_user_agent="t")
    )
    with pytest.raises(osm.OverpassBusy) as exc:
        asyncio.run(osm.OverpassClient().fetch_ways(0, 0, 1, 1))
    assert exc.value.retry_after is None
    assert not isinstance(exc.value, osm.OverpassRateLimited)  # busy, but not an explicit 429


def test_grid_cools_down_on_timeout_busy(monkeypatch) -> None:
    from app.integrations.osm import OverpassBusy

    def behavior(n):
        if n == 1:
            raise OverpassBusy(reason="timing out under load")
        return []

    result, client, sleeps = _grid_harness(monkeypatch, behavior)
    assert result["rateLimited"] is False
    assert 60.0 in sleeps  # default cooldown (timeouts carry no Retry-After)
    assert client.fetches == 3  # cell 1 retried after the cooldown, cell 2 clean


# --- endpoint visibility + dead-host classification ------------------------------------------


def test_connect_failure_is_not_classified_as_busy(monkeypatch) -> None:
    """A dead/unreachable endpoint (dead mirror, DNS typo) must surface as a real error, not
    'busy' - otherwise a misconfigured OVERPASS_URL reads as rate-limiting forever."""
    import asyncio

    import httpx
    import pytest

    from app.integrations import osm

    class FakeAsyncClient:
        def __init__(self, *a, **kw): ...
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **kw):
            raise httpx.ConnectError("host unreachable")

    monkeypatch.setattr(osm.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        osm, "get_settings", lambda: SimpleNamespace(overpass_url="", weather_user_agent="t")
    )
    with pytest.raises(httpx.ConnectError):
        asyncio.run(osm.OverpassClient().fetch_ways(0, 0, 1, 1))
    with pytest.raises(osm.OverpassBusy):
        raise osm.OverpassBusy()  # sanity: the busy type itself is unrelated to connect errors


def test_grid_summary_reports_endpoint(monkeypatch) -> None:
    def behavior(n):
        return []

    result, client, sleeps = _grid_harness(monkeypatch, behavior)
    assert result["endpoint"] == "fake://overpass"


# --- OVERPASS_ENABLED kill switch ------------------------------------------------------------


def test_overpass_enabled_defaults_true() -> None:
    from app.config import Settings

    assert Settings(_env_file=None).overpass_enabled is True


def test_disabled_overpass_503s_admin_endpoints(monkeypatch) -> None:
    """With a valid admin token but OVERPASS_ENABLED=false, the Overpass ops endpoints refuse
    with a clear 503 (before any Overpass/DB work)."""
    from fastapi.testclient import TestClient

    from app import security
    from app.main import app
    from app.routers import catalog

    monkeypatch.setattr(security, "get_settings", lambda: SimpleNamespace(admin_token="tok"))
    monkeypatch.setattr(
        catalog, "get_settings", lambda: SimpleNamespace(overpass_enabled=False)
    )
    client = TestClient(app)
    for path in ("/api/catalog/discover-osm", "/api/catalog/enrich-geometry"):
        resp = client.post(
            f"{path}?south=37.0&west=-122.5&north=37.3&east=-122.2",
            headers={"X-Admin-Token": "tok"},
        )
        assert resp.status_code == 503
        assert "OVERPASS_ENABLED" in resp.json()["detail"]
