"""Browse the TrailAPI catalog with on-demand caching.

GET /catalog/trails returns the cached trails nearest a point; if that area is sparsely
cached it first fetches the nearest 50 from TrailAPI and caches them, so the catalog fills in
as areas are browsed (within the request quota).
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.integrations.elevation import OpenMeteoElevation, UsgsElevation
from app.integrations.precipitation import OpenMeteoPrecip
from app.integrations.weather import WeatherClient
from app.models import CatalogTrail
from app.schemas.catalog import CatalogTrailOut
from app.services.catalog_geometry import ensure_line, enrich_region
from app.services.optimal_ride_time import (
    current_conditions_score,
    score_now,
    score_optimal_window,
)
from app.services.trail_conditions import assess_surface
from app.services.trail_catalog import (
    cache_trails_near,
    count_nearby,
    line_points,
    nearby_trails,
    recent_species_near_catalog,
    sightings_near_count,
)
from app.services.trail_metrics import bulk_compute_metrics, ensure_metrics
from app.services.wildlife_likelihood import (
    score_catalog_trails,
    score_species_for_trails,
    species_near,
)
from app.services.wildlife_sync import (
    backfill_region_history,
    sync_notable_observations,
    sync_recent_observations,
)

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
    lookback_days: int = Query(30, ge=1, le=60),
    species: str | None = Query(None, description="rank by this eBird species code's odds"),
    db: Session = Depends(get_db),
) -> dict:
    fetched_now = 0
    if count_nearby(db, lat, lon, radius_km) < _MIN_CACHED and get_settings().rapidapi_key:
        # TrailAPI radius is in miles; cap at its useful range.
        fetched_now = await cache_trails_near(db, lat, lon, radius=min(int(radius_km * 0.62) + 1, 100))

    # The wildlife score reads cached sightings; sync the area once if it's sparse so a
    # newly-browsed region isn't scored against an empty cache. Both feeds: the common-species
    # recent feed (activity) and the notable feed (rare sightings).
    synced_now = 0
    back = min(lookback_days, 30)  # eBird's recent feeds cap at back=30
    if sightings_near_count(db, lat, lon, radius_km=15) < _MIN_SIGHTINGS and get_settings().ebird_api_key:
        synced_now += await sync_recent_observations(db, lat, lon, dist_km=15, back_days=back)
        synced_now += await sync_notable_observations(db, lat, lon, dist_km=25, back_days=back)

    trails = nearby_trails(db, lat, lon, radius_km, limit)
    ids = [t.id for t in trails]
    scores = score_catalog_trails(db, ids, buffer_m=_AREA_BUFFER_M)
    # When targeting one species, also score each trail by that species' odds and rank by it.
    sp = score_species_for_trails(db, ids, species) if species else {}
    out = [
        CatalogTrailOut.from_model(
            t, scores.get(t.id), species_likelihood=sp.get(t.id, {}).get("likelihood") if species else None
        )
        for t in trails
    ]
    if species:
        out.sort(key=lambda c: c.speciesLikelihood or 0, reverse=True)
    return {
        "count": len(out),
        "fetchedNow": fetched_now,
        "syncedNow": synced_now,
        "species": species,
        "trails": out,
    }


@router.get("/species")
async def list_species_near(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(15, ge=1, le=80),
    limit: int = Query(16, ge=1, le=60),
    notable_only: bool = Query(False),
    db: Session = Depends(get_db),
) -> dict:
    """Species reported near a point, ranked by recency+seasonality odds (the targeting picker).

    Syncs the area's eBird feeds once if the cache is sparse, like the trail list does."""
    synced_now = 0
    if sightings_near_count(db, lat, lon, radius_km=15) < _MIN_SIGHTINGS and get_settings().ebird_api_key:
        synced_now += await sync_recent_observations(db, lat, lon, dist_km=15, back_days=30)
        synced_now += await sync_notable_observations(db, lat, lon, dist_km=25, back_days=30)

    species = species_near(db, lat, lon, radius_m=radius_km * 1000, limit=limit if not notable_only else 60)
    if notable_only:
        species = [s for s in species if s["notable"]][:limit]
    return {"count": len(species), "syncedNow": synced_now, "species": species}


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
    score = score_catalog_trails(db, [trail.id], buffer_m=_AREA_BUFFER_M).get(trail.id)
    return {
        "trail": CatalogTrailOut.from_model(trail, score, with_factors=True),
        "linePoints": line_points(db, trail.id),
    }


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


async def _surface_assessment(lat: float, lon: float, now: datetime) -> dict | None:
    """Recent-precip trail-surface (tacky/mud) assessment, or None if precip is unavailable."""
    try:
        precip = await OpenMeteoPrecip().recent(lat, lon)
        return assess_surface(precip["times"], precip["precip_mm"], now=now)
    except Exception:  # noqa: BLE001 - surface is a bonus; never fail the caller on it
        return None


@router.get("/trails/{external_id}/optimal-time")
async def catalog_trail_optimal_time(external_id: str, db: Session = Depends(get_db)) -> dict:
    """Best time-of-day to ride: blends the NWS hourly forecast (riding conditions, with a recent-
    precip surface penalty) and a dawn/dusk wildlife-activity prior scaled by the trail's eBird
    score. Fails soft outside the US (NWS-only): returns available=false with no curve, but still
    reports trailConditions (Open-Meteo precip is global) so the screen's conditions read stays live.
    """
    trail = _get_catalog_or_404(db, external_id)
    now = datetime.now(UTC)
    score = score_catalog_trails(db, [trail.id], buffer_m=_AREA_BUFFER_M).get(trail.id)
    trail_score = (score or {}).get("score", 0)

    surface = await _surface_assessment(trail.lat, trail.lon, now)
    surface_factor = surface["factor"] if surface else 1.0
    trail_conditions = {"score": surface["score"], "label": surface["label"]} if surface else None

    try:
        hourly = await WeatherClient().forecast_hourly(trail.lat, trail.lon)
    except Exception:  # noqa: BLE001 - no US forecast (or NWS hiccup): degrade, don't error
        return {"trail": external_id, "available": False, "date": None, "hours": [],
                "bestWindow": None, "bestWindowWhy": None, "window": None,
                "trailConditions": trail_conditions}
    payload = score_optimal_window(
        hourly, trail.lat, trail.lon, trail_score, now=now, surface_factor=surface_factor
    )
    return {"trail": external_id, **payload, "trailConditions": trail_conditions}


@router.get("/optimal-now")
async def catalog_optimal_now(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(40, ge=1, le=160),
    limit: int = Query(60, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    """Rank nearby trails by how well *now* overlaps their optimal window (the optimal-now sort).

    Weather and recent rain are regional, so the current conditions + surface are computed once for
    the query point and reused across trails; the per-trail differentiator is each trail's wildlife
    score and crepuscular timing. Fails soft: no NWS forecast -> rank on the wildlife/daylight term.
    """
    now = datetime.now(UTC)
    surface = await _surface_assessment(lat, lon, now)
    surface_factor = surface["factor"] if surface else 1.0
    conditions_now = None
    try:
        hourly = await WeatherClient().forecast_hourly(lat, lon)
        conditions_now = current_conditions_score(hourly, lat, lon, now=now, surface_factor=surface_factor)
    except Exception:  # noqa: BLE001 - no US forecast: rank on wildlife/daylight alone
        conditions_now = None

    trails = nearby_trails(db, lat, lon, radius_km, limit)
    scores = score_catalog_trails(db, [t.id for t in trails], buffer_m=_AREA_BUFFER_M)
    ranked = [
        {
            "id": t.external_id,
            "optimalNow": score_now(now, t.lat, t.lon, (scores.get(t.id) or {}).get("score", 0), conditions_now),
        }
        for t in trails
    ]
    ranked.sort(key=lambda r: r["optimalNow"], reverse=True)
    return {
        "trails": ranked,
        "conditionsNow": conditions_now,
        "trailConditions": {"score": surface["score"], "label": surface["label"]} if surface else None,
    }


@router.post("/backfill-history")
async def backfill_history(
    region_code: str = Query(..., description="eBird region, e.g. a county like US-CA-081"),
    year: int = Query(..., ge=2000, le=2100),
    day: int = Query(15, ge=1, le=28),
    db: Session = Depends(get_db),
) -> dict:
    """Sample one historic day per month for an eBird region to seed the seasonality signal."""
    if not get_settings().ebird_api_key:
        raise HTTPException(status_code=503, detail="eBird API key not configured")
    return await backfill_region_history(db, region_code, year, day=day)


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
