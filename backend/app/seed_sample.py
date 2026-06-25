"""Seed the catalog with a real sample of Bay Area trails - no TrailAPI calls.

For local/offline setup: loads ~68 trails (trailhead points, OSM lines, and elevation metrics
where we have them) straight from a committed fixture, so the app shows real trails using only
the free data sources (eBird, NWS weather, Open-Meteo/USGS elevation, Overpass). TrailAPI then
just fills in *other* regions on demand - it's not needed to get the app working locally.

Run with:  python -m app.seed_sample
"""

from __future__ import annotations

import json
from pathlib import Path

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import CatalogTrail

_FIXTURE = Path(__file__).parent / "data" / "catalog_sample.json"
_METRIC_FIELDS = (
    "metric_length_mi", "ascent_ft", "descent_ft", "avg_up_grade", "avg_down_grade",
    "elevation_profile", "ride_time_min", "effort", "elev_source",
)


def seed_sample(db: Session) -> int:
    """Upsert the fixture trails (dedup on external_id). Returns the number added."""
    rows = json.loads(_FIXTURE.read_text())
    existing = {row[0] for row in db.execute(select(CatalogTrail.external_id))}
    added = 0
    for r in rows:
        if r["external_id"] in existing:
            continue
        trail = CatalogTrail(
            external_id=r["external_id"],
            source=r.get("source") or "trailapi",
            name=r["name"],
            difficulty=r.get("difficulty"),
            length_mi=r.get("length_mi"),
            city=r.get("city"),
            region=r.get("region"),
            country=r.get("country"),
            url=r.get("url"),
            lat=r["lat"],
            lon=r["lon"],
            geom=WKTElement(f"POINT({r['lon']} {r['lat']})", srid=4326),
            line_geom=WKTElement(r["line_wkt"], srid=4326) if r.get("line_wkt") else None,
        )
        for field in _METRIC_FIELDS:
            setattr(trail, field, r.get(field))
        db.add(trail)
        existing.add(r["external_id"])
        added += 1
    db.commit()
    return added


def main() -> None:
    db = SessionLocal()
    try:
        count = seed_sample(db)
        print(f"seeded {count} sample catalog trails (skipped {68 - count} already present)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
