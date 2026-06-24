"""Response schema for the TrailAPI catalog (camelCase to match the frontend).

Beyond the trail's own fields and DEM-derived terrain metrics, this carries the first-pass
wildlife overlay (score, likely birds, sighting factors) built from cached eBird sightings by
`services/wildlife_likelihood.score_catalog_trails`. Those are a relative, area-level proxy
labelled "preview" in the UI - not the calibrated likelihood model (see CLAUDE.md).
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.models import CatalogTrail


class SightingFactor(BaseModel):
    label: str
    value: str
    pct: int
    tone: str  # "terracotta" | "sage"


def _tone(pct: int) -> str:
    return "terracotta" if pct >= 70 else "sage"


def _humanize_since(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    days = (datetime.now(UTC) - dt).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    return f"{days} days ago"


def _recency_pct(dt: datetime | None) -> int:
    if dt is None:
        return 0
    days = max((datetime.now(UTC) - dt).days, 0)
    return max(20, 100 - days * 2)


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
    # First-pass wildlife overlay from cached eBird (preview; null when not scored).
    score: int | None = None
    likelyBirds: list[str] = Field(default_factory=list)
    metaBird: str | None = None
    peak: str | None = None
    sightingHeadline: str | None = None
    factors: list[SightingFactor] = Field(default_factory=list)

    @classmethod
    def from_model(
        cls,
        t: CatalogTrail,
        score_info: dict | None = None,
        lookback_days: int = 30,
        with_factors: bool = False,
    ) -> "CatalogTrailOut":
        wildlife = _wildlife_fields(score_info, lookback_days, with_factors)
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
            **wildlife,
        )


def _wildlife_fields(score_info: dict | None, lookback_days: int, with_factors: bool) -> dict:
    """Turn a per-trail score dict (from score_catalog_trails) into the camelCase overlay."""
    if not score_info:
        return {}
    top = score_info.get("top_species", [])
    names = [s["common_name"] for s in top]
    count = score_info.get("species_count", 0)
    score = score_info.get("score", 0)
    last = top[0]["last_observed"] if top else None

    fields: dict = {
        "score": score,
        "likelyBirds": names[:3],
        "metaBird": names[0] if names else None,
        "peak": ", ".join(names[:2]) if names else None,
        "sightingHeadline": (
            f"{count} species reported nearby in the last {lookback_days} days"
            if count
            else "No recent eBird reports nearby"
        ),
    }
    if with_factors:
        fields["factors"] = [
            SightingFactor(
                label="Species nearby", value=f"{count} in {lookback_days}d", pct=score, tone=_tone(score)
            ),
            SightingFactor(
                label="Most recent report",
                value=_humanize_since(last),
                pct=_recency_pct(last),
                tone=_tone(_recency_pct(last)),
            ),
            SightingFactor(
                label="Top species", value=names[0] if names else "—", pct=score, tone=_tone(score)
            ),
        ]
    return fields
