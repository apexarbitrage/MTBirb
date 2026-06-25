"""Trail-data source endpoints: OSM geometry ingestion and the TrailAPI catalog.

Kept under their own prefix (not /trails/...) so source operations never collide with the
/trails/{slug} routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.integrations.trailapi import TrailApiClient
from app.services.trail_geometry import assign_real_geometry

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("/osm/sync-geometry")
async def sync_osm_geometry(db: Session = Depends(get_db)) -> dict:
    """Replace seeded trails' placeholder lines with real OSM geometry near each locale."""
    summary = await assign_real_geometry(db)
    return {"trails": summary}


@router.get("/trailapi/catalog")
async def trailapi_catalog(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius: int = Query(25, ge=1, le=100),
) -> dict:
    """Curated nearby trails from TrailAPI (name, trailhead point, difficulty, length)."""
    if not get_settings().rapidapi_key:
        raise HTTPException(status_code=503, detail="RAPIDAPI_KEY is not configured")
    records = await TrailApiClient().explore(lat, lon, radius)
    trails = [
        {
            "id": r.get("id"),
            "name": r.get("name"),
            "lat": float(r["lat"]) if r.get("lat") else None,
            "lon": float(r["lon"]) if r.get("lon") else None,
            "difficulty": r.get("difficulty") or None,
            "length": r.get("length") or None,
            "city": r.get("city"),
            "region": r.get("region"),
            "url": r.get("url"),
        }
        for r in records
    ]
    return {"count": len(trails), "trails": trails}
