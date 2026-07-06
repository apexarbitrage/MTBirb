"""Request/response schemas for logged trips (camelCase to match the frontend)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models import Trip


class TripBird(BaseModel):
    speciesCode: str | None = None
    commonName: str


# A downscaled thumbnail data-URL is a few tens of KB; cap it well above that but low enough that
# a caller can't stuff a full-res image (or arbitrary payload) into the trip's JSON row.
_MAX_THUMB_CHARS = 400_000  # ~300 KB of base64
_MAX_PHOTOS_PER_TRIP = 12


class TripPhoto(BaseModel):
    lat: float | None = None
    lon: float | None = None
    takenAt: str | None = None
    thumb: str = Field(max_length=_MAX_THUMB_CHARS)  # downscaled data-URL (full image isn't stored)


class TripCreate(BaseModel):
    trailExternalId: str | None = None
    trailName: str
    difficulty: str | None = None
    miles: float | None = None
    riddenOn: date | None = None  # defaults to today on the server
    birds: list[TripBird] = Field(default_factory=list, max_length=200)
    photos: list[TripPhoto] = Field(default_factory=list, max_length=_MAX_PHOTOS_PER_TRIP)


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
