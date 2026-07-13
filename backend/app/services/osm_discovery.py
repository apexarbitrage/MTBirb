"""Discover MTB trails directly from OSM/Overpass and add them to the catalog.

TrailAPI is sparse - often a bare trailhead point with none of the surrounding network - so this
complements it: one Overpass bbox call fetches every *named* ridable way in the area, same-named
ways are stitched into per-trail lines, and each becomes a full `CatalogTrail` row with
`source="osm"` and `line_geom` already set - so an OSM-discovered trail never needs the per-trail
Overpass assembly (`ensure_line` fast-paths on an existing line) and is immediately a
route-builder candidate.

Dataflow is the inverse of `catalog_geometry` (which attaches lines to rows that already exist):
here geometry comes first and rows are created from it. The planner (`plan_discovery`) is pure so
it can be tested hermetically; only `discover_trails`/`discover_grid` touch the network/DB.

Dedup against the existing catalog is by name similarity + trailhead proximity. When the match is
a *line-less* row (the classic bare TrailAPI trailhead), discovery **donates** its stitched line
to that row instead of skipping - directly fixing "trailhead with no surrounding trail" at no
extra Overpass cost. A lined match wins outright (first wins; TrailAPI metadata is preserved).

Overpass safety: callers are gated and paced (see routers/catalog.py's per-cell attempted set and
`discover_grid`'s sleep); this module itself makes exactly one Overpass call per `discover_trails`.
"""

import asyncio
import logging

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.osm import OverpassBusy, OverpassClient, _scale_rank, summarize_surface
from app.models import CatalogTrail
from app.services.catalog_geometry import (
    _MIN_ASSEMBLED_M,
    _bbox,
    _haversine_m,
    _line_length_m,
    _name_match,
    _norm,
    stitch_ways,
)
from app.services.trail_catalog import count_nearby

logger = logging.getLogger(__name__)

# Half-side of the discovery bbox: one Overpass call covers a 16 km square. Small enough that a
# named-only response stays modest even over a dense network, big enough that a handful of calls
# covers a riding area.
_DISCOVERY_RADIUS_KM = 8.0
# A same-named existing catalog row with a trailhead within this of the discovered trail's start
# is treated as the same trail (TrailAPI and OSM trailheads rarely coincide exactly).
_DEDUP_RADIUS_M = 2_000.0
# Fewer OSM-sourced rows than this near a browsed point marks the area "sparse" -> discover.
_MIN_OSM_NEARBY = 5
# Sanity cap on rows created from one pathological bbox.
_MAX_ROWS_PER_CALL = 300
# When Overpass says it's busy (429, or a read timeout from sitting in its overload queue), wait
# at least this long before the one retry (a Retry-After header wins when longer). Busy again on
# the retry means the server truly can't take us now - stop the sweep; skip-gates make a later
# re-run resume where this one ended.
_RATE_LIMIT_COOLDOWN_S = 60.0
# A run of consecutive failures (Overpass outage, network loss) aborts the sweep instead of
# churning through the whole call budget on errors.
_MAX_CONSECUTIVE_FAILURES = 5


def group_named_ways(ways: list[dict]) -> dict[str, list[dict]]:
    """Group ways by exact normalized name, dropping unnamed ways.

    Deliberately NOT fuzzy (`_name_match`) here: within one bbox a trail's split ways carry the
    identical name string, and fuzzy grouping would glue "Ridge Trail" onto "Bay Ridge Trail".
    Fuzzy matching is reserved for dedup against *existing* rows, where TrailAPI spellings drift.
    """
    groups: dict[str, list[dict]] = {}
    for way in ways:
        name = (way.get("name") or "").strip()
        if not name:
            continue
        groups.setdefault(_norm(name), []).append(way)
    return groups


def _external_id(group: list[dict]) -> str:
    """A stable catalog id for a discovered trail: the smallest OSM way id in its group. Stable
    across way ordering and re-discovery, and the "osm-" namespace can't collide with TrailAPI's
    numeric ids."""
    return f"osm-{min(w['osm_id'] for w in group)}"


def _difficulty_from_scale(mtb_scale: str | None) -> str | None:
    """Map OSM's mtb:scale (0..6 technical rating) onto the catalog's difficulty buckets. The
    strings match `normalizeDifficulty` in the frontend exactly, so markers/pills just work."""
    if mtb_scale is None:
        return None
    rank = _scale_rank(str(mtb_scale))
    if rank < 0:
        return None
    if rank <= 1:
        return "Easy"
    if rank <= 3:
        return "Intermediate"
    return "Advanced"


def group_to_catalog(name: str, group: list[dict], chain: list[tuple[float, float]]) -> CatalogTrail:
    """Build a full catalog row from a stitched group: trailhead point at the chain start, the
    line itself, surface/difficulty from way tags, and length measured off the chain."""
    lon, lat = chain[0]
    coords = ", ".join(f"{p_lon} {p_lat}" for p_lon, p_lat in chain)
    summary = summarize_surface(group)
    return CatalogTrail(
        source="osm",
        external_id=_external_id(group),
        name=name[:200],
        difficulty=_difficulty_from_scale(summary["mtb_scale"]),
        length_mi=round(_line_length_m(chain) / 1609.344, 1),
        url=f"https://www.openstreetmap.org/way/{min(w['osm_id'] for w in group)}",
        lat=lat,
        lon=lon,
        geom=WKTElement(f"POINT({lon} {lat})", srid=4326),
        line_geom=WKTElement(f"LINESTRING({coords})", srid=4326),
        surface=summary["surface"],
        mtb_scale=summary["mtb_scale"],
    )


def plan_discovery(ways: list[dict], existing: list) -> dict:
    """The pure planner: parsed bbox ways + lightweight existing-row facts -> what to do.

    `existing` items need `.name`, `.lat`, `.lon`, `.external_id`, `.has_line`, `.id` (a Row or
    SimpleNamespace works). Returns {"new_trails": [CatalogTrail...],
    "donations": [(existing_row_id, chain, group)...], "skipped": int}.
    """
    known_ids = {e.external_id for e in existing}
    new_trails: list[CatalogTrail] = []
    donations: list[tuple[int, list[tuple[float, float]], list[dict]]] = []
    skipped = 0

    for norm_name, group in group_named_ways(ways).items():
        if _external_id(group) in known_ids:
            skipped += 1
            continue
        # Seed stitching from the longest way so a group holding disconnected same-named pieces
        # keeps its largest component (the far spur is left out and dropped for v1).
        longest = max(group, key=lambda w: _line_length_m(w["points"]))
        chain = stitch_ways(group, *longest["points"][0])
        if not chain or _line_length_m(chain) < _MIN_ASSEMBLED_M:
            skipped += 1  # fragment - don't fabricate a trail from a scrap
            continue

        # Dedup vs existing rows: same-ish name with a trailhead near the chain start.
        raw_name = (group[0].get("name") or "").strip()
        match = next(
            (
                e
                for e in existing
                if _name_match(_norm(e.name), norm_name)
                and _haversine_m((e.lon, e.lat), chain[0]) <= _DEDUP_RADIUS_M
            ),
            None,
        )
        if match is not None:
            if match.has_line:
                skipped += 1  # already have this trail with geometry - first wins
            else:
                # A bare trailhead (usually TrailAPI): donate the stitched line to it.
                donations.append((match.id, chain, group))
            continue

        if len(new_trails) >= _MAX_ROWS_PER_CALL:
            skipped += 1
            continue
        new_trails.append(group_to_catalog(raw_name, group, chain))

    return {"new_trails": new_trails, "donations": donations, "skipped": skipped}


def _existing_rows(db: Session, south: float, west: float, north: float, east: float) -> list:
    """Existing catalog rows in (a margin around) the bbox, trimmed to the dedup facts the
    planner needs. Plain lat/lon range filter - cheap, no geography join."""
    margin_lat = _DEDUP_RADIUS_M / 111_000
    rows = db.execute(
        select(
            CatalogTrail.id,
            CatalogTrail.external_id,
            CatalogTrail.name,
            CatalogTrail.lat,
            CatalogTrail.lon,
            CatalogTrail.line_geom.is_not(None).label("has_line"),
        ).where(
            CatalogTrail.lat.between(south - margin_lat, north + margin_lat),
            CatalogTrail.lon.between(west - margin_lat, east + margin_lat),
        )
    ).all()
    return list(rows)


async def discover_trails(
    db: Session,
    lat: float,
    lon: float,
    radius_km: float = _DISCOVERY_RADIUS_KM,
    client: OverpassClient | None = None,
) -> dict:
    """One discovery pass around a point: exactly one Overpass call, then plan + apply.

    New trails are inserted with their lines; line-less same-named existing rows receive a
    donated line (plus surface/mtb_scale from the way tags). One commit at the end.
    """
    client = client or OverpassClient()
    south, west, north, east = _bbox(lat, lon, radius_km * 1000)
    ways = await client.fetch_ways(south, west, north, east, named_only=True)
    plan = plan_discovery(ways, _existing_rows(db, south, west, north, east))

    for trail in plan["new_trails"]:
        db.add(trail)
    for row_id, chain, group in plan["donations"]:
        target = db.get(CatalogTrail, row_id)
        if target is None or target.line_geom is not None:
            continue  # deleted or lined since planning; nothing to donate
        coords = ", ".join(f"{p_lon} {p_lat}" for p_lon, p_lat in chain)
        target.line_geom = WKTElement(f"LINESTRING({coords})", srid=4326)
        summary = summarize_surface(group)
        target.surface = summary["surface"]
        target.mtb_scale = summary["mtb_scale"]
    db.commit()

    return {
        "ways": len(ways),
        "groups": len(group_named_ways(ways)),
        "added": len(plan["new_trails"]),
        "donated": len(plan["donations"]),
        "skipped": plan["skipped"],
    }


def grid_cells(
    lat_range: tuple[float, float], lon_range: tuple[float, float], step: float = 0.15
) -> list[tuple[float, float]]:
    """Cell centers covering a lat/lon box at ~the discovery bbox pitch (0.15 deg ~ 16 km of
    latitude; the slight longitudinal overlap at higher latitudes is deliberate - safer than
    gaps, and the per-cell skip gate absorbs it)."""
    cells: list[tuple[float, float]] = []
    lat = min(lat_range) + step / 2
    while lat <= max(lat_range) + 1e-9:
        lon = min(lon_range) + step / 2
        while lon <= max(lon_range) + 1e-9:
            cells.append((round(lat, 4), round(lon, 4)))
            lon += step
        lat += step
    return cells


async def discover_grid(
    db: Session,
    lat_range: tuple[float, float],
    lon_range: tuple[float, float],
    *,
    max_calls: int,
    client: OverpassClient | None = None,
    sleep_s: float = 5.0,
    skip_at: int = _MIN_OSM_NEARBY,
) -> dict:
    """Sweep a box cell-by-cell (the admin endpoint + seeder path). Cells that already have
    OSM-sourced rows are skipped, so runs are resumable and re-runs are near-free; each real
    Overpass call is followed by a polite sleep.

    Overpass "busy" signals are first-class: a 429 or an overload read-timeout cools down
    (Retry-After or 60s) and retries the cell once; busy again means the server truly can't take
    us now, so the sweep stops gracefully (`rateLimited: true`) rather than burning the remaining
    budget - re-running later resumes via the skip-gates. A run of other consecutive failures
    (outage, network) aborts the same way (`aborted: true`)."""
    client = client or OverpassClient()
    endpoint = getattr(client, "url", "unknown")
    logger.info("OSM discovery sweep via %s", endpoint)
    calls = added = donated = skipped_cells = 0
    consecutive_failures = 0
    rate_limited = aborted = False
    for lat, lon in grid_cells(lat_range, lon_range):
        if calls >= max_calls:
            break
        if count_nearby(db, lat, lon, _DISCOVERY_RADIUS_KM, source="osm") >= skip_at:
            skipped_cells += 1
            continue
        for attempt in (1, 2):
            calls += 1
            try:
                result = await discover_trails(db, lat, lon, client=client)
                added += result["added"]
                donated += result["donated"]
                consecutive_failures = 0
            except OverpassBusy as exc:
                if attempt == 1:
                    cooldown = max(exc.retry_after or 0.0, _RATE_LIMIT_COOLDOWN_S)
                    logger.info("Overpass busy (%s); cooling down %.0fs then retrying cell", exc, cooldown)
                    await asyncio.sleep(cooldown)
                    continue
                logger.warning(
                    "Overpass still busy after cooldown (%s via %s); stopping sweep", exc, endpoint
                )
                rate_limited = True
            except Exception:  # noqa: BLE001 - keep sweeping past one bad cell / Overpass hiccup
                logger.warning("OSM discovery failed for cell (%s, %s)", lat, lon, exc_info=True)
                consecutive_failures += 1
                if consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                    logger.warning(
                        "%d consecutive discovery failures; stopping sweep", consecutive_failures
                    )
                    aborted = True
            break
        if rate_limited or aborted:
            break
        await asyncio.sleep(sleep_s)
    return {
        "endpoint": endpoint,
        "calls": calls,
        "added": added,
        "donated": donated,
        "skippedCells": skipped_cells,
        "rateLimited": rate_limited,
        "aborted": aborted,
    }
