"""Ingest and serve the TrailAPI catalog.

TrailAPI returns at most 50 trails per call (the nearest within the radius) and the plan has
a limited request quota, so the catalog is built by caching: seed some regions up front, then
fetch-and-cache the nearest trails for any area as it's browsed. Everything is deduped by the
TrailAPI id (`external_id`).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from geoalchemy2.elements import WKTElement
from geoalchemy2.types import Geography
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.integrations.trailapi import TrailApiClient
from app.models import CatalogTrail, WildlifeSighting


def _safe_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def record_to_catalog(rec: dict) -> CatalogTrail | None:
    """Map a TrailAPI record to a CatalogTrail, or None if it has no id/coordinates."""
    ext_id = rec.get("id")
    lat, lon = _safe_float(rec.get("lat")), _safe_float(rec.get("lon"))
    if not ext_id or lat is None or lon is None:
        return None
    name = (rec.get("name") or "").strip()
    if not name or name.lower() == "no name":  # TrailAPI uses the literal string "no name"
        name = "Unnamed trail"
    return CatalogTrail(
        source="trailapi",
        external_id=str(ext_id),
        name=name[:200],
        difficulty=(rec.get("difficulty") or None),
        length_mi=_safe_float(rec.get("length")),
        city=rec.get("city"),
        region=rec.get("region"),
        country=rec.get("country"),
        url=rec.get("url"),
        lat=lat,
        lon=lon,
        geom=WKTElement(f"POINT({lon} {lat})", srid=4326),
    )


def upsert_catalog(db: Session, records: list[dict]) -> int:
    """Insert catalog trails not already cached (dedup on external_id). Returns rows added."""
    mapped = [c for rec in records if (c := record_to_catalog(rec)) is not None]
    if not mapped:
        return 0
    ext_ids = {c.external_id for c in mapped}
    existing = {
        row[0]
        for row in db.execute(
            select(CatalogTrail.external_id).where(CatalogTrail.external_id.in_(ext_ids))
        )
    }
    added = 0
    for ct in mapped:
        if ct.external_id in existing:
            continue
        db.add(ct)
        existing.add(ct.external_id)  # guard against dups within this batch
        added += 1
    db.commit()
    return added


async def cache_trails_near(
    db: Session, lat: float, lon: float, radius: int = 25, client: TrailApiClient | None = None
) -> int:
    """Fetch the nearest TrailAPI trails around a point and cache the new ones."""
    client = client or TrailApiClient()
    records = await client.explore(lat, lon, radius)
    return upsert_catalog(db, records)


def _point_geog(lat: float, lon: float):
    return func.cast(func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326), Geography)


def count_nearby(db: Session, lat: float, lon: float, radius_km: float) -> int:
    return db.scalar(
        select(func.count())
        .select_from(CatalogTrail)
        .where(
            func.ST_DWithin(
                func.cast(CatalogTrail.geom, Geography), _point_geog(lat, lon), radius_km * 1000
            )
        )
    ) or 0


def nearby_trails(
    db: Session, lat: float, lon: float, radius_km: float = 40, limit: int = 50
) -> list[CatalogTrail]:
    """Cached catalog trails within radius_km of a point, nearest first."""
    point = _point_geog(lat, lon)
    geog = func.cast(CatalogTrail.geom, Geography)
    return list(
        db.scalars(
            select(CatalogTrail)
            .where(func.ST_DWithin(geog, point, radius_km * 1000))
            .order_by(func.ST_Distance(geog, point))
            .limit(limit)
        )
    )


def sightings_near_count(db: Session, lat: float, lon: float, radius_km: float) -> int:
    return db.scalar(
        select(func.count())
        .select_from(WildlifeSighting)
        .where(func.ST_DWithin(func.cast(WildlifeSighting.geom, Geography), _point_geog(lat, lon), radius_km * 1000))
    ) or 0


def recent_species_near_catalog(
    db: Session, catalog_id: int, buffer_m: float = 800, lookback_days: int = 14, limit: int = 8
) -> list[dict]:
    """Species recently reported to eBird near a catalog trail (its line if matched, else point)."""
    geom = func.coalesce(CatalogTrail.line_geom, CatalogTrail.geom)
    trail_geog = (
        select(func.cast(geom, Geography)).where(CatalogTrail.id == catalog_id).scalar_subquery()
    )
    buffered = func.ST_Buffer(trail_geog, buffer_m)
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    rows = db.execute(
        select(
            WildlifeSighting.species_code,
            WildlifeSighting.common_name,
            func.count().label("observations"),
            func.max(WildlifeSighting.observed_at).label("last_observed"),
        )
        .where(WildlifeSighting.observed_at >= cutoff)
        .where(func.ST_Intersects(func.cast(WildlifeSighting.geom, Geography), buffered))
        .group_by(WildlifeSighting.species_code, WildlifeSighting.common_name)
        .order_by(func.count().desc(), func.max(WildlifeSighting.observed_at).desc())
        .limit(limit)
    ).all()
    return [
        {
            "species_code": r.species_code,
            "common_name": r.common_name,
            "observations": r.observations,
            "last_observed": r.last_observed,
        }
        for r in rows
    ]


def search_catalog_trails(
    db: Session, query: str, lat: float, lon: float, limit: int = 20
) -> list[tuple[CatalogTrail, float]]:
    """Name search across all cached trails, nearest first. Returns (trail, distance_mi) pairs.
    Only matches trails already in the cache; new regions populate as they're browsed."""
    q = query.strip()
    if len(q) < 2:
        return []
    point = _point_geog(lat, lon)
    geog = func.cast(CatalogTrail.geom, Geography)
    rows = db.execute(
        select(
            CatalogTrail,
            (func.ST_Distance(geog, point) / 1609.344).label("distance_mi"),
        )
        .where(CatalogTrail.name.ilike(f"%{q}%"))
        .order_by(func.ST_Distance(geog, point))
        .limit(limit)
    ).all()
    return [(row.CatalogTrail, float(row.distance_mi)) for row in rows]


def line_points(db: Session, catalog_id: int) -> list[list[float]] | None:
    """The catalog trail's OSM line as [[lon, lat], ...], or None if it has no line yet."""
    geojson = db.scalar(
        select(func.ST_AsGeoJSON(CatalogTrail.line_geom)).where(CatalogTrail.id == catalog_id)
    )
    if not geojson:
        return None
    return json.loads(geojson)["coordinates"]
