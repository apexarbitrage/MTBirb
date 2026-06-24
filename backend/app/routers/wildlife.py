from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.services.wildlife_sync import sync_recent_observations

router = APIRouter(prefix="/wildlife", tags=["wildlife"])


@router.post("/sync")
async def sync_observations(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    dist_km: int = Query(25, ge=1, le=50),
    back_days: int = Query(14, ge=1, le=30),
    db: Session = Depends(get_db),
) -> dict:
    """Cache recent eBird observations around a point into wildlife_sightings."""
    if not get_settings().ebird_api_key:
        raise HTTPException(status_code=503, detail="EBIRD_API_KEY is not configured")
    added = await sync_recent_observations(db, lat, lng, dist_km, back_days)
    return {"synced": added, "lat": lat, "lng": lng, "dist_km": dist_km, "back_days": back_days}
