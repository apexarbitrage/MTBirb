"""Browse the TrailAPI catalog with on-demand caching.

GET /catalog/trails returns the cached trails nearest a point; if that area is sparsely
cached it first fetches the nearest 50 from TrailAPI and caches them, so the catalog fills in
as areas are browsed (within the request quota).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.integrations.elevation import OpenMeteoElevation, UsgsElevation
from app.integrations.weather import WeatherClient
from app.models import CatalogTrail
from app.schemas.catalog import CatalogTrailOut
from app.services.catalog_geometry import ensure_line, enrich_region
from app.services.trail_catalog import (
    cache_trails_near,
    count_nearby,
    line_points,
    nearby_trails,
    recent_species_near_catalog,
    sightings_near_count,
)
from app.services.trail_metrics import bulk_compute_metrics, ensure_metrics
from app.services.wildlife_sync import sync_recent_observations

router = APIRouter(prefix="/catalog", tags=["catalog"])

# Below this many cached trails within the search radius, trigger a one-off TrailAPI fetch.
_MIN_CACHED = 8
# Below this many cached eBird sightings near a trail, trigger a one-off eBird sync.
_MIN_SIGHTINGS = 20
# Catalog trails are points, so wildlife is reported as an area-level signal at this radius.
_AREA_BUFFER_M = 8000


def _get_catalog_or_404(db: Session, external_id: str) -> CatalogTrail:
    trail = db.scalar(select(CatalogTrail).where(CatalogTrail.external_id == external_id))
    if trail is None:
        raise HTTPException(status_code=404, detail="catalog trail not found")
    return trail


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


@router.get("/trails/{external_id}")
async def get_catalog_trail(external_id: str, db: Session = Depends(get_db)) -> dict:
    """A catalog trail's detail. Fetches its OSM line on demand, then refines its terrain
    metrics to the higher-resolution USGS 3DEP DEM (the initial pass uses Open-Meteo)."""
    trail = _get_catalog_or_404(db, external_id)
    try:
        await ensure_line(db, trail)
    except Exception:  # noqa: BLE001 - a line is a nice-to-have; never fail the detail on it
        pass
    try:
        await ensure_metrics(db, trail, UsgsElevation())
    except Exception:  # noqa: BLE001 - keep any existing (Open-Meteo) metrics on DEM failure
        pass
    return {"trail": CatalogTrailOut.from_model(trail), "linePoints": line_points(db, trail.id)}


@router.get("/trails/{external_id}/wildlife")
async def catalog_trail_wildlife(
    external_id: str,
    lookback_days: int = Query(14, ge=1, le=60),
    db: Session = Depends(get_db),
) -> dict:
    """Species recently reported to eBird near the trail; syncs eBird here on demand if sparse."""
    trail = _get_catalog_or_404(db, external_id)
    synced = 0
    if sightings_near_count(db, trail.lat, trail.lon, radius_km=15) < _MIN_SIGHTINGS and get_settings().ebird_api_key:
        synced = await sync_recent_observations(db, trail.lat, trail.lon, dist_km=15, back_days=lookback_days)
    # Catalog trails are point-based, so this is an area-level signal (eBird checklists cluster
    # at hotspots that are rarely right on an arbitrary trailhead), labelled honestly as such.
    species = recent_species_near_catalog(db, trail.id, buffer_m=_AREA_BUFFER_M, lookback_days=lookback_days)
    return {"trail": external_id, "syncedNow": synced, "areaRadiusKm": _AREA_BUFFER_M / 1000, "species": species}


@router.get("/trails/{external_id}/weather")
async def catalog_trail_weather(external_id: str, db: Session = Depends(get_db)) -> dict:
    """NWS forecast at the trail's location."""
    trail = _get_catalog_or_404(db, external_id)
    periods = await WeatherClient().forecast(trail.lat, trail.lon)
    trimmed = [
        {
            "name": p.get("name"),
            "startTime": p.get("startTime"),
            "isDaytime": p.get("isDaytime"),
            "temperature": p.get("temperature"),
            "temperatureUnit": p.get("temperatureUnit"),
            "shortForecast": p.get("shortForecast"),
            "windSpeed": p.get("windSpeed"),
        }
        for p in periods[:12]
    ]
    return {"trail": external_id, "periods": trimmed}


@router.post("/enrich-geometry")
async def enrich_geometry(
    south: float = Query(...),
    west: float = Query(...),
    north: float = Query(...),
    east: float = Query(...),
    max_calls: int = Query(40, ge=1, le=400),
    force: bool = Query(False),
    db: Session = Depends(get_db),
) -> dict:
    """Batch-match OSM lines for catalog trails in a bbox (one Overpass call per trail).
    `force` re-assembles existing lines too (to upgrade older single-way fragments)."""
    return await enrich_region(db, (south, north), (west, east), max_calls=max_calls, force=force)


@router.post("/compute-metrics")
async def compute_metrics(
    south: float = Query(...),
    west: float = Query(...),
    north: float = Query(...),
    east: float = Query(...),
    max_trails: int = Query(200, ge=1, le=500),
    force: bool = Query(False),
    db: Session = Depends(get_db),
) -> dict:
    """The fast initial elevation pass: compute terrain metrics for lined trails in a bbox
    using batched Open-Meteo lookups. USGS refinement happens per-trail on detail view."""
    return await bulk_compute_metrics(
        db, (south, north), (west, east), OpenMeteoElevation(), max_trails=max_trails, force=force
    )


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
