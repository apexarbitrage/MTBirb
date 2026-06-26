"""Attach real OSM ridable-line geometry to catalog trails.

A catalog trail arrives from TrailAPI as a trailhead point. This matches it to the best
nearby OSM way - by name where possible, else the nearest ridable line - and stores that as
`line_geom`, so catalog trails get real lines like the curated trails. Lines are fetched on
demand when a trail's detail is opened; `enrich_region` can pre-fill a region in a batch.
"""

from __future__ import annotations

import asyncio
import math
import re

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.osm import OverpassClient, summarize_surface
from app.models import CatalogTrail

_SEARCH_RADIUS_M = 700
# Tokens too generic to identify a trail; dropped when building the name-search regex.
_GENERIC_TOKENS = {
    "trail", "trails", "loop", "path", "park", "open", "space", "preserve",
    "the", "to", "of", "and", "mtb", "area", "recreation",
}
# OSM splits a trail into many same-named ways; chain segments whose endpoints are within this
# far (they usually share an exact node, so this only bridges small gaps).
_STITCH_GAP_M = 70.0
# A reassembled line must beat this to be trusted over the small-radius fallback.
_MIN_ASSEMBLED_M = 250.0


def _bbox(lat: float, lon: float, radius_m: float) -> tuple[float, float, float, float]:
    dlat = radius_m / 111_000
    dlon = radius_m / (111_000 * max(math.cos(math.radians(lat)), 0.01))
    return (lat - dlat, lon - dlon, lat + dlat, lon + dlon)


def _norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _name_core(name: str | None) -> str:
    """The distinctive part of a trail name as a loose Overpass regex (tokens joined by `.*`).

    Drops generic words ("Trail", "Park"...) so "Sawyer Camp Trail" -> "sawyer.*camp", which
    matches every OSM way of that trail. Tokens are alphanumeric (via `_norm`), so the result is
    safe to embed in the Overpass query without further escaping.
    """
    tokens = [t for t in _norm(name).split() if t not in _GENERIC_TOKENS]
    tokens = tokens or _norm(name).split()
    return ".*".join(tokens[:3])


def _assembly_radius_m(length_mi: float | None) -> float:
    """A search radius sized to the trail: long trails need a wide bbox to be reassembled."""
    if not length_mi or length_mi <= 0:
        return 3000.0
    return max(2000.0, min(length_mi * 1609.344 * 0.7, 16000.0))


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    (lon1, lat1), (lon2, lat2) = a, b
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _line_length_m(points: list[tuple[float, float]]) -> float:
    return sum(_haversine_m(points[i - 1], points[i]) for i in range(1, len(points)))


def _name_match(a: str, b: str) -> bool:
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    common = set(a.split()) & set(b.split())
    return bool(common) and len(common) >= min(len(a.split()), len(b.split())) / 2


def _min_dist2(lon0: float, lat0: float, points: list[tuple[float, float]]) -> float:
    return min((lon - lon0) ** 2 + (lat - lat0) ** 2 for lon, lat in points)


def best_line_for(
    name: str, lon: float, lat: float, ways: list[dict]
) -> list[tuple[float, float]] | None:
    """Pick the best OSM way for a trail: a name match if any, else the nearest way."""
    if not ways:
        return None
    tnorm = _norm(name)
    named = [w for w in ways if w.get("name") and _name_match(tnorm, _norm(w["name"]))]
    pool = named or ways
    best = min(pool, key=lambda w: _min_dist2(lon, lat, w["points"]))
    return best["points"]


def stitch_ways(
    ways: list[dict], seed_lon: float, seed_lat: float, gap_tol_m: float = _STITCH_GAP_M
) -> list[tuple[float, float]] | None:
    """Chain OSM ways into one ordered polyline starting from the way nearest the trailhead.

    Greedily extends both ends of the chain with whichever remaining way connects closest
    (within `gap_tol_m`), reversing segments as needed and dropping the duplicated joint vertex.
    Ways that don't connect to the trailhead's component are left out (avoids grabbing spurs).
    """
    segments = [list(w["points"]) for w in ways if len(w.get("points", [])) >= 2]
    if not segments:
        return None
    seed_i = min(range(len(segments)), key=lambda i: _min_dist2(seed_lon, seed_lat, segments[i]))
    chain = segments.pop(seed_i)

    extended = True
    while extended and segments:
        extended = False
        head, tail = chain[0], chain[-1]
        best: tuple[int, str, list, float] | None = None  # (idx, end, oriented_seg, dist)
        for i, seg in enumerate(segments):
            options = [
                ("tail", seg, _haversine_m(tail, seg[0])),
                ("tail", seg[::-1], _haversine_m(tail, seg[-1])),
                ("head", seg, _haversine_m(head, seg[-1])),
                ("head", seg[::-1], _haversine_m(head, seg[0])),
            ]
            for end, oriented, dist in options:
                if dist <= gap_tol_m and (best is None or dist < best[3]):
                    best = (i, end, oriented, dist)
        if best is not None:
            i, end, oriented, _ = best
            segments.pop(i)
            chain = chain + oriented[1:] if end == "tail" else oriented[:-1] + chain
            extended = True
    return chain


async def assemble_line(
    client: OverpassClient, name: str, lon: float, lat: float, length_mi: float | None
) -> tuple[list[tuple[float, float]] | None, list[dict]]:
    """Reassemble a trail's full line from OSM: pull every same-named way across a length-sized
    bbox and stitch them, falling back to the nearest single way in a small radius. Also returns
    the ways that informed the chosen line (for the surface summary)."""
    tnorm = _norm(name)
    core = _name_core(name)
    if core:
        ways = await client.fetch_named_ways(core, *_bbox(lat, lon, _assembly_radius_m(length_mi)))
        named = [w for w in ways if w.get("name") and _name_match(tnorm, _norm(w["name"]))]
        chain = stitch_ways(named or ways, lon, lat)
        if chain and _line_length_m(chain) >= _MIN_ASSEMBLED_M:
            return chain, (named or ways)

    ways = await client.fetch_ways(*_bbox(lat, lon, _SEARCH_RADIUS_M))
    named = [w for w in ways if w.get("name") and _name_match(tnorm, _norm(w["name"]))]
    chain = stitch_ways(named, lon, lat) if named else None
    return chain or best_line_for(name, lon, lat, ways), (named or ways)


async def ensure_line(
    db: Session, trail: CatalogTrail, client: OverpassClient | None = None, force: bool = False
) -> bool:
    """Fetch + store an OSM line for a catalog trail if it doesn't have one. Returns True if set.

    `force` re-assembles even when a line already exists (e.g. to replace an older fragment with
    a fuller stitched line); the trail's elevation metrics are cleared so they get recomputed.
    """
    has_line = trail.line_geom is not None
    if has_line and not force and trail.surface is not None:
        return True
    client = client or OverpassClient()
    points, ways_used = await assemble_line(client, trail.name, trail.lon, trail.lat, trail.length_mi)

    surface = summarize_surface(ways_used)
    trail.surface = surface["surface"]
    trail.mtb_scale = surface["mtb_scale"]

    if has_line and not force:
        # Geometry is already good - this pass only backfills the surface summary.
        db.commit()
        return True
    if not points:
        db.commit()  # persist any surface we did learn, even without a usable line
        return False
    coords = ", ".join(f"{lon} {lat}" for lon, lat in points)
    trail.line_geom = WKTElement(f"LINESTRING({coords})", srid=4326)
    if force:
        trail.elev_source = None  # geometry changed; metrics are stale
    db.commit()
    return True


async def enrich_region(
    db: Session,
    lat_range: tuple[float, float],
    lon_range: tuple[float, float],
    max_calls: int = 40,
    client: OverpassClient | None = None,
    force: bool = False,
) -> dict:
    """Batch-match OSM lines for catalog trails in a bbox. By default only fills trails without
    a line; `force` re-assembles every trail (e.g. to upgrade older fragment lines)."""
    client = client or OverpassClient()
    query = select(CatalogTrail).where(
        CatalogTrail.lat.between(*lat_range),
        CatalogTrail.lon.between(*lon_range),
    )
    if not force:
        query = query.where(CatalogTrail.line_geom.is_(None))
    trails = list(db.scalars(query))
    calls = 0
    matched = 0
    for trail in trails:
        if calls >= max_calls:
            break
        try:
            ok = await ensure_line(db, trail, client, force=force)
        except Exception:  # noqa: BLE001 - keep going if one Overpass call fails
            continue
        calls += 1
        matched += int(ok)
        await asyncio.sleep(0.7)  # be polite to the shared Overpass instance
    return {"pending": len(trails), "calls": calls, "matched": matched}
