"""API response schemas for trails.

Field names are camelCase on purpose: they mirror the frontend `Trail` interface
(`frontend/src/data/trails.ts`) one-to-one so the client consumes the response with no
remapping. Fields sourced from the `Trail.derived` overlay are integration-derived and
currently seeded placeholders - see app/models/trail.py.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.models import Trail


class SightingFactor(BaseModel):
    label: str
    value: str
    pct: int
    tone: str  # "terracotta" | "sage"


class TrailOut(BaseModel):
    id: str  # the trail slug
    name: str
    diff: str | None
    miles: float | None
    effort: float | None
    features: list[str]
    rideTime: int | None
    location: str | None
    gainFt: int | None
    climbFt: int | None
    descentFt: int | None
    avgUpGrade: str | None
    avgDownGrade: str | None
    elevation: list[float]

    # --- integration-derived overlay (seeded placeholders today) ---
    score: int | None
    window: str | None
    realfeel: str | None
    sky: str | None
    condition: str | None
    dirt: str | None
    peak: str | None
    metaTime: str | None
    metaBird: str | None
    likelyBirds: list[str]
    sightingHeadline: str | None
    factors: list[SightingFactor]
    bestWindow: str | None
    bestWindowWhy: str | None

    @classmethod
    def from_model(cls, trail: Trail) -> "TrailOut":
        d = trail.derived or {}
        return cls(
            id=trail.slug or str(trail.id),
            name=trail.name,
            diff=trail.difficulty,
            miles=trail.miles,
            effort=trail.effort,
            features=trail.features or [],
            rideTime=trail.ride_time_min,
            location=trail.location,
            gainFt=trail.gain_ft,
            climbFt=trail.climb_ft,
            descentFt=trail.descent_ft,
            avgUpGrade=trail.avg_up_grade,
            avgDownGrade=trail.avg_down_grade,
            elevation=trail.elevation or [],
            score=d.get("score"),
            window=d.get("window"),
            realfeel=d.get("realfeel"),
            sky=d.get("sky"),
            condition=d.get("condition"),
            dirt=d.get("dirt"),
            peak=d.get("peak"),
            metaTime=d.get("metaTime"),
            metaBird=d.get("metaBird"),
            likelyBirds=d.get("likelyBirds", []),
            sightingHeadline=d.get("sightingHeadline"),
            factors=[SightingFactor(**f) for f in d.get("factors", [])],
            bestWindow=d.get("bestWindow"),
            bestWindowWhy=d.get("bestWindowWhy"),
        )
