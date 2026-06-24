"""Request/response schemas for logged trips (camelCase to match the frontend)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models import Trip


class TripBird(BaseModel):
    speciesCode: str | None = None
    commonName: str


class TripCreate(BaseModel):
    trailExternalId: str | None = None
    trailName: str
    difficulty: str | None = None
    miles: float | None = None
    riddenOn: date | None = None  # defaults to today on the server
    birds: list[TripBird] = Field(default_factory=list)


class TripOut(BaseModel):
    id: int
    trailExternalId: str | None
    trailName: str
    difficulty: str | None
    miles: float | None
    riddenOn: date
    birds: list[TripBird]
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
            lifers=lifers,
            createdAt=t.created_at,
        )
