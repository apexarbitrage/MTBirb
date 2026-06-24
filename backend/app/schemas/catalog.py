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
        )
