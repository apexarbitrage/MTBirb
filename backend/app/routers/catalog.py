"""Browse the TrailAPI catalog with on-demand caching.

GET /catalog/trails returns the cached trails nearest a point; if that area is sparsely
cached it first fetches the nearest 50 from TrailAPI and caches them, so the catalog fills in
as areas are browsed (within the request quota).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.schemas.catalog import CatalogTrailOut
from app.services.trail_catalog import cache_trails_near, count_nearby, nearby_trails

router = APIRouter(prefix="/catalog", tags=["catalog"])

# Below this many cached trails within the search radius, trigger a one-off TrailAPI fetch.
_MIN_CACHED = 8


@router.get("/trails")
async def list_catalog_trails(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(40, ge=1, le=160),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    fetched_now = 0
    if count_nearby(db, lat, lon, radius_km) < _MIN_CACHED and get_settings().rapidapi_key:
        # TrailAPI radius is in miles; cap at its useful range.
        fetched_now = await cache_trails_near(db, lat, lon, radius=min(int(radius_km * 0.62) + 1, 100))

    trails = nearby_trails(db, lat, lon, radius_km, limit)
    return {
        "count": len(trails),
        "fetchedNow": fetched_now,
        "trails": [CatalogTrailOut.from_model(t) for t in trails],
    }


@router.post("/sync")
async def sync_catalog(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    """Explicitly prime the catalog around a point (used by the region seed)."""
    added = await cache_trails_near(db, lat, lon, radius)
    return {"added": added, "lat": lat, "lon": lon, "radius": radius}
