"""Request/response schemas for logged trips (camelCase to match the frontend)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models import Trip


class TripBird(BaseModel):
    speciesCode: str | None = None
    commonName: str


class TripPhoto(BaseModel):
    lat: float | None = None
    lon: float | None = None
    takenAt: str | None = None
    thumb: str  # downscaled data-URL (the full image isn't stored)


class TripCreate(BaseModel):
    trailExternalId: str | None = None
    trailName: str
    difficulty: str | None = None
    miles: float | None = None
    riddenOn: date | None = None  # defaults to today on the server
    birds: list[TripBird] = Field(default_factory=list)
    photos: list[TripPhoto] = Field(default_factory=list)


class TripOut(BaseModel):
    id: int
    trailExternalId: str | None
    trailName: str
    difficulty: str | None
    miles: float | None
    riddenOn: date
    birds: list[TripBird]
    photos: list[TripPhoto]
    lifers: int
    createdAt: datetime

    @classmethod
    def from_model(cls, t: Trip, lifers: int) -> "TripOut":
        return cls(
            id=t.id,
            trailExternalId=t.trail_external_id,
            trailName=t.trail_name,
            difficulty=t.difficulty,
            miles=t.miles,
            riddenOn=t.ridden_on,
            birds=[TripBird(speciesCode=b.get("species_code"), commonName=b.get("common_name", "")) for b in (t.birds or [])],
            photos=[
                TripPhoto(lat=p.get("lat"), lon=p.get("lon"), takenAt=p.get("taken_at"), thumb=p.get("thumb", ""))
                for p in (t.photos or [])
            ],
            lifers=lifers,
            createdAt=t.created_at,
        )
