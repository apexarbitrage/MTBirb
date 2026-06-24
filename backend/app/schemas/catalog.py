"""Response schema for the TrailAPI catalog (camelCase to match the frontend)."""

from __future__ import annotations

from pydantic import BaseModel

from app.models import CatalogTrail


class CatalogTrailOut(BaseModel):
    id: str  # TrailAPI external id
    name: str
    difficulty: str | None
    lengthMi: float | None
    city: str | None
    region: str | None
    lat: float
    lon: float
    url: str | None
    # DEM-derived terrain metrics (null until computed); see services/trail_metrics.py.
    metricLengthMi: float | None
    ascentFt: int | None
    descentFt: int | None
    avgUpGrade: str | None
    avgDownGrade: str | None
    elevationProfile: list[float] | None
    rideTimeMin: int | None
    effort: float | None
    elevSource: str | None

    @classmethod
    def from_model(cls, t: CatalogTrail) -> "CatalogTrailOut":
        return cls(
            id=t.external_id,
            name=t.name,
            difficulty=t.difficulty,
            lengthMi=t.length_mi,
            city=t.city,
            region=t.region,
            lat=t.lat,
            lon=t.lon,
            url=t.url,
            metricLengthMi=t.metric_length_mi,
            ascentFt=t.ascent_ft,
            descentFt=t.descent_ft,
            avgUpGrade=t.avg_up_grade,
            avgDownGrade=t.avg_down_grade,
            elevationProfile=t.elevation_profile,
            rideTimeMin=t.ride_time_min,
            effort=t.effort,
            elevSource=t.elev_source,
        )
