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

from app.integrations.osm import OverpassClient
from app.models import CatalogTrail

_SEARCH_RADIUS_M = 700


def _bbox(lat: float, lon: float, radius_m: float) -> tuple[float, float, float, float]:
    dlat = radius_m / 111_000
    dlon = radius_m / (111_000 * max(math.cos(math.radians(lat)), 0.01))
    return (lat - dlat, lon - dlon, lat + dlat, lon + dlon)


def _norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


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


async def ensure_line(
    db: Session, trail: CatalogTrail, client: OverpassClient | None = None
) -> bool:
    """Fetch + store an OSM line for a catalog trail if it doesn't have one. Returns True if set."""
    if trail.line_geom is not None:
        return True
    client = client or OverpassClient()
    ways = await client.fetch_ways(*_bbox(trail.lat, trail.lon, _SEARCH_RADIUS_M))
    points = best_line_for(trail.name, trail.lon, trail.lat, ways)
    if not points:
        return False
    coords = ", ".join(f"{lon} {lat}" for lon, lat in points)
    trail.line_geom = WKTElement(f"LINESTRING({coords})", srid=4326)
    db.commit()
    return True


async def enrich_region(
    db: Session,
    lat_range: tuple[float, float],
    lon_range: tuple[float, float],
    max_calls: int = 40,
    client: OverpassClient | None = None,
) -> dict:
    """Batch-match OSM lines for catalog trails in a bbox that don't have one yet."""
    client = client or OverpassClient()
    trails = list(
        db.scalars(
            select(CatalogTrail).where(
                CatalogTrail.lat.between(*lat_range),
                CatalogTrail.lon.between(*lon_range),
                CatalogTrail.line_geom.is_(None),
            )
        )
    )
    calls = 0
    matched = 0
    for trail in trails:
        if calls >= max_calls:
            break
        try:
            ok = await ensure_line(db, trail, client)
        except Exception:  # noqa: BLE001 - keep going if one Overpass call fails
            continue
        calls += 1
        matched += int(ok)
        await asyncio.sleep(0.7)  # be polite to the shared Overpass instance
    return {"pending": len(trails), "calls": calls, "matched": matched}
