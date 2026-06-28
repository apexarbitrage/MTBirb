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
    # Expanded terrain + surface stats (null until computed/enriched).
    maxGrade: str | None = None
    highPointFt: int | None = None
    lowPointFt: int | None = None
    longestClimbMi: float | None = None
    aspect: str | None = None
    sunExposure: float | None = None
    surface: str | None = None
    mtbScale: str | None = None
    # Wildlife overlay from cached eBird (preview proxy; null/empty when not scored). `score` is
    # overall recency-weighted activity; `notableScore` is the odds of something locally unusual.
    score: int | None = None
    notableScore: int | None = None
    likelyBirds: list[str] = Field(default_factory=list)
    notableBirds: list[str] = Field(default_factory=list)
    metaBird: str | None = None
    peak: str | None = None
    sightingHeadline: str | None = None
    factors: list[SightingFactor] = Field(default_factory=list)
    # Set only when the list is filtered to one species: that species' odds near this trail.
    speciesLikelihood: int | None = None
    # A rider's custom hero photo, as a cache-busting version token (null = use the stock hero).
    # The image itself streams from GET /catalog/trails/{id}/photo?v={photoVersion}.
    photoVersion: str | None = None

    @classmethod
    def from_model(
        cls,
        t: CatalogTrail,
        score_info: dict | None = None,
        with_factors: bool = False,
        species_likelihood: int | None = None,
        photo_version: str | None = None,
    ) -> "CatalogTrailOut":
        wildlife = _wildlife_fields(score_info, with_factors)
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
            maxGrade=t.max_grade,
            highPointFt=t.high_point_ft,
            lowPointFt=t.low_point_ft,
            longestClimbMi=t.longest_climb_mi,
            aspect=t.aspect,
            sunExposure=t.sun_exposure,
            surface=t.surface,
            mtbScale=t.mtb_scale,
            speciesLikelihood=species_likelihood,
            photoVersion=photo_version,
            **wildlife,
        )


def _plural(n: int, word: str) -> str:
    # "species" (and other -s words) are invariant; don't tack on another "s".
    if n == 1 or word.endswith("s"):
        return f"{n} {word}"
    return f"{n} {word}s"


def _wildlife_fields(score_info: dict | None, with_factors: bool) -> dict:
    """Turn a per-trail score dict (from score_catalog_trails) into the camelCase overlay.

    `likelyBirds` are the most-likely (recency-weighted) species - common ones included, which
    is correct for "what you'll probably see". `notableBirds`/`peak` come from eBird's notable
    feed - the rarer, more exciting sightings the product is really pitching.
    """
    if not score_info:
        return {}
    likely = [s["common_name"] for s in score_info.get("top_species", [])]
    notable = [s["common_name"] for s in score_info.get("top_notable", [])]
    count = score_info.get("species_count", 0)
    notable_count = score_info.get("notable_count", 0)
    score = score_info.get("score", 0)
    notable_score = score_info.get("notable_score", 0)
    last = score_info.get("top_species", [{}])[0].get("last_observed") if count else None
    # Headline a notable name when there is one (the hook), else the activity summary.
    headline = (
        f"{notable[0]} and {_plural(notable_count - 1, 'other notable species')} reported nearby"
        if notable_count > 1
        else f"{notable[0]} reported nearby - a notable sighting"
        if notable_count == 1
        else f"{_plural(count, 'species')} reported nearby recently"
        if count
        else "No recent eBird reports nearby"
    )

    fields: dict = {
        "score": score,
        "notableScore": notable_score,
        "likelyBirds": likely[:3],
        "notableBirds": notable[:3],
        "metaBird": (notable or likely or [None])[0],
        "peak": ", ".join((notable or likely)[:2]) or None,
        "sightingHeadline": headline,
    }
    if with_factors:
        fields["factors"] = [
            SightingFactor(
                label="Notable nearby",
                value=_plural(notable_count, "species"),
                pct=notable_score,
                tone=_tone(notable_score),
            ),
            SightingFactor(
                label="Species activity",
                value=_plural(count, "species"),
                pct=score,
                tone=_tone(score),
            ),
            SightingFactor(
                label="Most recent report",
                value=_humanize_since(last),
                pct=_recency_pct(last),
                tone=_tone(_recency_pct(last)),
            ),
        ]
    return fields
