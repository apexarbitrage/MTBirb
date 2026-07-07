"""Request/response schemas for saved multi-trail routes (camelCase to match the frontend).

A route's line/stats/species are recomputed from its member trails at read time (see
services/trail_routes.py), so these schemas carry derived values, not stored ones. `mappedCount`
vs `trailCount` keeps the stats honest when some members were never terrain-mapped.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models import CatalogTrail, TrailRoute
from app.services.trail_routes import _MAX_MEMBERS


class TrailRouteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    # Ordered chain of catalog external_ids; the server re-validates connectivity on create.
    trailIds: list[str] = Field(min_length=2, max_length=_MAX_MEMBERS)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        return v


class RouteTrailLite(BaseModel):
    """A member/candidate trail, trimmed to what the builder map and member list need."""

    id: str  # catalog external_id
    name: str
    difficulty: str | None
    lengthMi: float | None
    metricLengthMi: float | None
    ascentFt: int | None
    rideTimeMin: int | None
    lat: float
    lon: float
    linePoints: list[list[float]] | None = None  # [[lon, lat], ...]

    @classmethod
    def from_model(cls, t: CatalogTrail, line: list[list[float]] | None = None) -> "RouteTrailLite":
        return cls(
            id=t.external_id,
            name=t.name,
            difficulty=t.difficulty,
            lengthMi=t.length_mi,
            metricLengthMi=t.metric_length_mi,
            ascentFt=t.ascent_ft,
            rideTimeMin=t.ride_time_min,
            lat=t.lat,
            lon=t.lon,
            linePoints=line,
        )


class TrailRouteSummaryOut(BaseModel):
    """A route as the Routes list shows it: name + combined headline stats."""

    id: int
    name: str
    trailCount: int
    mappedCount: int
    miles: float | None
    ascentFt: int | None
    wildlifeScore: int | None
    createdAt: datetime

    @classmethod
    def from_model(
        cls, r: TrailRoute, stats: dict, wildlife_score: int | None
    ) -> "TrailRouteSummaryOut":
        return cls(
            id=r.id,
            name=r.name,
            trailCount=stats["trail_count"],
            mappedCount=stats["mapped_count"],
            miles=stats["miles"],
            ascentFt=stats["ascent_ft"],
            wildlifeScore=wildlife_score,
            createdAt=r.created_at,
        )


class TrailRouteDetailOut(TrailRouteSummaryOut):
    """The full route detail: summary + the rest of the combined stats, the ordered members,
    and the concatenated line. `missingTrailIds` lists members no longer in the catalog (the
    survivors still render)."""

    descentFt: int | None
    rideTimeMin: int | None
    highPointFt: int | None
    lowPointFt: int | None
    members: list[RouteTrailLite]
    missingTrailIds: list[str]
    linePoints: list[list[float]]  # [] when no member has a line yet
    startLat: float | None
    startLon: float | None

    @classmethod
    def from_detail(
        cls,
        r: TrailRoute,
        stats: dict,
        wildlife_score: int | None,
        members: list[RouteTrailLite],
        missing: list[str],
        line_points: list[list[float]],
    ) -> "TrailRouteDetailOut":
        return cls(
            id=r.id,
            name=r.name,
            trailCount=stats["trail_count"],
            mappedCount=stats["mapped_count"],
            miles=stats["miles"],
            ascentFt=stats["ascent_ft"],
            wildlifeScore=wildlife_score,
            createdAt=r.created_at,
            descentFt=stats["descent_ft"],
            rideTimeMin=stats["ride_time_min"],
            highPointFt=stats["high_point_ft"],
            lowPointFt=stats["low_point_ft"],
            members=members,
            missingTrailIds=missing,
            linePoints=line_points,
            startLat=members[0].lat if members else None,
            startLon=members[0].lon if members else None,
        )
