"""Replace seeded trails' placeholder geometry with real OSM line geometry.

The seeded trails shipped with short synthetic LineStrings that didn't coincide with where
eBird checklists actually cluster, so the wildlife buffer/intersect found nothing nearby.
This pulls real ridable ways near each trail's locale from OSM and assigns the most
prominent one's geometry, so the spatial queries run against real trail lines.
"""

from __future__ import annotations

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.osm import OverpassClient
from app.models import Trail

# Locale center per seeded trail slug (lon, lat). Mirrors the named places in the seed.
_LOCALES: dict[str, tuple[float, float]] = {
    "raptor": (-122.4030, 48.7258),  # Galbraith Mtn
    "owl": (-122.4440, 48.7045),  # Lake Padden
    "cedar": (-122.3312, 48.7201),  # Stewart Mtn
    "marsh": (-122.5852, 48.8235),  # Tennant Lake
}
_HALF_DEG = 0.012  # bbox half-size (~1.3 km) around the locale center


def _best_way(ways: list[dict]) -> dict | None:
    """Prefer a named way; among the candidates pick the one with the most geometry points."""
    if not ways:
        return None
    named = [w for w in ways if w.get("name")]
    return max(named or ways, key=lambda w: len(w["points"]))


def _wkt(points: list[tuple[float, float]]) -> WKTElement:
    coords = ", ".join(f"{lon} {lat}" for lon, lat in points)
    return WKTElement(f"LINESTRING({coords})", srid=4326)


async def assign_real_geometry(db: Session, client: OverpassClient | None = None) -> list[dict]:
    """For each seeded trail, fetch nearby OSM ways and adopt the best line's geometry."""
    client = client or OverpassClient()
    summary: list[dict] = []
    for slug, (lon, lat) in _LOCALES.items():
        trail = db.scalar(select(Trail).where(Trail.slug == slug))
        if trail is None:
            continue
        ways = await client.fetch_ways(lat - _HALF_DEG, lon - _HALF_DEG, lat + _HALF_DEG, lon + _HALF_DEG)
        way = _best_way(ways)
        if way is None:
            summary.append({"slug": slug, "assigned": False, "osm_ways_found": 0})
            continue
        trail.geom = _wkt(way["points"])
        trail.external_id = f"osm:{way['osm_id']}"
        summary.append(
            {
                "slug": slug,
                "assigned": True,
                "osm_ways_found": len(ways),
                "osm_id": way["osm_id"],
                "osm_name": way.get("name"),
                "points": len(way["points"]),
            }
        )
    db.commit()
    return summary
