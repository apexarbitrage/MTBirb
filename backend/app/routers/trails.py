from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.integrations.weather import WeatherClient
from app.models import Trail
from app.schemas.trail import TrailOut
from app.services.wildlife_likelihood import recent_species_near_trail

router = APIRouter(prefix="/trails", tags=["trails"])


def _get_trail_or_404(db: Session, slug: str) -> Trail:
    trail = db.scalar(select(Trail).where(Trail.slug == slug))
    if trail is None:
        raise HTTPException(status_code=404, detail="trail not found")
    return trail


@router.get("")
def list_trails(db: Session = Depends(get_db)) -> list[TrailOut]:
    trails = db.scalars(select(Trail).order_by(Trail.id)).all()
    return [TrailOut.from_model(t) for t in trails]


@router.get("/{slug}")
def get_trail(slug: str, db: Session = Depends(get_db)) -> TrailOut:
    return TrailOut.from_model(_get_trail_or_404(db, slug))


@router.get("/{slug}/wildlife")
def trail_wildlife(
    slug: str,
    lookback_days: int = Query(14, ge=1, le=60),
    db: Session = Depends(get_db),
) -> dict:
    """Species recently reported to eBird near this trail (from the cached sightings)."""
    trail = _get_trail_or_404(db, slug)
    species = recent_species_near_trail(db, trail.id, lookback_days=lookback_days)
    return {"trail": slug, "lookbackDays": lookback_days, "species": species}


@router.get("/{slug}/weather")
async def trail_weather(slug: str, db: Session = Depends(get_db)) -> dict:
    """NWS forecast periods for the trail's location."""
    trail = _get_trail_or_404(db, slug)
    lat, lon = db.execute(
        select(
            func.ST_Y(func.ST_Centroid(Trail.geom)),
            func.ST_X(func.ST_Centroid(Trail.geom)),
        ).where(Trail.id == trail.id)
    ).one()

    periods = await WeatherClient().forecast(lat, lon)
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
    return {"trail": slug, "point": {"lat": lat, "lon": lon}, "periods": trimmed}
