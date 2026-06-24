"""Scores a trail's likelihood of a wildlife encounter from cached eBird sightings.

This is a first-pass proxy (raw nearby-observation counts), not a calibrated probability.
It does not yet account for search effort (checklists per area), seasonality, or time of
day, which is exactly the modeling work flagged as needing the most design time before this
becomes the "highest chance of seeing an owl" feature described in the product plan.
"""

import math
from datetime import UTC, datetime, timedelta

from geoalchemy2.types import Geography
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import CatalogTrail, Trail, WildlifeSighting

# Saturation constants for scores of the form 100*(1-e^(-x/K)).
# - richness (plain species count) tuned to the 8 km range (~15-65 species) -> ~40-90.
# - activity sums recency-decayed weights (an "effective recent species count").
# - notable is far sparser, so it saturates quickly (a handful of rare species reads as high).
_SCORE_SATURATION = 28.0
_ACTIVITY_SATURATION = 22.0
_NOTABLE_SATURATION = 6.0
_MAX_SCORE = 98
# A sighting's contribution decays as exp(-days_since / tau): ~3 weeks halves it roughly twice
# a month, so a bird not reported lately stops propping up a trail's score.
_RECENCY_TAU_DAYS = 21.0
# Weight for a record with no usable date (rare); small but non-zero.
_UNKNOWN_DATE_WEIGHT = 0.3
# Scoring looks back up to a year so accumulated/backfilled history counts; recency decay (not a
# hard cutoff) is what down-weights older records. Seasonality further modulates this.
_SCORE_WINDOW_DAYS = 365

# Seasonality: in which months a species is *typically* present, learned from cached history.
# We deliberately exclude the recent window so the dense current-month feed doesn't make every
# species look in-season (a single recent stray shouldn't mark a month typical). Phenology is
# the set of months a species appears in across the older/backfilled record; today's month
# (with neighbours) either lands in that set or it doesn't. An out-of-season species is damped
# to the floor; an in-season specialist gets a modest lift over a year-round resident.
_SEASON_RECENT_EXCLUDE_DAYS = 35
_SEASON_FLOOR = 0.3
_SEASON_BOOST = 0.4  # max extra weight for a tightly-seasonal species in its window
_SEASON_RESIDENT_MONTHS = 11  # present ~year-round -> treat as neutral


def score_trail_for_species(
    db: Session,
    trail_id: int,
    species_code: str,
    buffer_m: float = 500,
    lookback_days: int = 365,
) -> dict:
    if db.scalar(select(Trail.id).where(Trail.id == trail_id)) is None:
        raise ValueError(f"no trail with id {trail_id}")

    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    # Built as a subquery (rather than loading Trail.geom into Python and rebinding it)
    # so the geometry never round-trips through a WKB/WKT conversion mismatch.
    trail_geog = (
        select(func.cast(Trail.geom, Geography)).where(Trail.id == trail_id).scalar_subquery()
    )
    buffered = func.ST_Buffer(trail_geog, buffer_m)

    nearby_observations = db.scalar(
        select(func.count())
        .select_from(WildlifeSighting)
        .where(WildlifeSighting.species_code == species_code)
        .where(WildlifeSighting.observed_at >= cutoff)
        .where(func.ST_Intersects(func.cast(WildlifeSighting.geom, Geography), buffered))
    )

    return {
        "trail_id": trail_id,
        "species_code": species_code,
        "nearby_observations": nearby_observations or 0,
        "buffer_m": buffer_m,
        "lookback_days": lookback_days,
    }


def recent_species_near_trail(
    db: Session,
    trail_id: int,
    buffer_m: float = 750,
    lookback_days: int = 14,
    limit: int = 8,
) -> list[dict]:
    """Species recently reported to eBird near a trail, ranked by observation count.

    Honest raw signal (counts of cached sightings within a buffer), not a calibrated
    probability - the same caveat as score_trail_for_species applies.
    """
    if db.scalar(select(Trail.id).where(Trail.id == trail_id)) is None:
        raise ValueError(f"no trail with id {trail_id}")

    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    trail_geog = (
        select(func.cast(Trail.geom, Geography)).where(Trail.id == trail_id).scalar_subquery()
    )
    buffered = func.ST_Buffer(trail_geog, buffer_m)

    rows = db.execute(
        select(
            WildlifeSighting.species_code,
            WildlifeSighting.common_name,
            func.count().label("observations"),
            func.max(WildlifeSighting.observed_at).label("last_observed"),
        )
        .where(WildlifeSighting.observed_at >= cutoff)
        .where(func.ST_Intersects(func.cast(WildlifeSighting.geom, Geography), buffered))
        .group_by(WildlifeSighting.species_code, WildlifeSighting.common_name)
        .order_by(func.count().desc(), func.max(WildlifeSighting.observed_at).desc())
        .limit(limit)
    ).all()

    return [
        {
            "species_code": r.species_code,
            "common_name": r.common_name,
            "observations": r.observations,
            "last_observed": r.last_observed,
        }
        for r in rows
    ]


def _saturating_score(x: float, k: float) -> int:
    """A saturating 0..MAX score: 100*(1 - e^(-x/k)), clamped."""
    if x <= 0:
        return 0
    return min(_MAX_SCORE, round(100 * (1 - math.exp(-x / k))))


def _score_from_richness(species_count: int) -> int:
    """A saturating 0..MAX score from the number of distinct species reported nearby."""
    return _saturating_score(species_count, _SCORE_SATURATION)


def _recency_weight(observed_at: datetime | None, now: datetime) -> float:
    """How much a species' most-recent sighting still counts: exp(-days_since / tau)."""
    if observed_at is None:
        return _UNKNOWN_DATE_WEIGHT
    days = max((now - observed_at).total_seconds() / 86400.0, 0.0)
    return math.exp(-days / _RECENCY_TAU_DAYS)


def _month_neighbours(month: int) -> set[int]:
    """The month and its two calendar neighbours (wrapping Dec<->Jan), 1-based."""
    return {(month - 2) % 12 + 1, month, month % 12 + 1}


def _seasonal_factor(months_present: set[int], today_month: int) -> float:
    """How in-season a species is this month, from the set of months it's historically present.

    Neutral (1.0) when we have no phenology or the species is essentially year-round. Otherwise
    it's either in season (this month or a neighbour is in the set) - lifted a little, more so
    the more tightly seasonal it is - or out of season, damped to the floor.
    """
    n = len(months_present)
    if n == 0 or n >= _SEASON_RESIDENT_MONTHS:
        return 1.0
    if months_present & _month_neighbours(today_month):
        return round(1.0 + (1 - n / 12) * _SEASON_BOOST, 3)
    return _SEASON_FLOOR


def species_seasonality(
    db: Session, species_codes: list[str], ref_date: datetime | None = None
) -> dict[str, float]:
    """Per-species seasonal factor for `ref_date` (default now), from historic phenology.

    Uses each species' set of months present in the cache *outside* the recent window, so the
    dense current-month feed doesn't flatten the signal. Phenology is treated as a species-level
    property across the (regional) cache, so it's unfiltered by trail. Species with no historic
    record simply don't appear here and default to neutral at the call site.
    """
    if not species_codes:
        return {}
    now = ref_date or datetime.now(UTC)
    cutoff = now - timedelta(days=_SEASON_RECENT_EXCLUDE_DAYS)
    rows = db.execute(
        select(WildlifeSighting.species_code, WildlifeSighting.observed_at).where(
            WildlifeSighting.species_code.in_(species_codes),
            WildlifeSighting.observed_at < cutoff,
        )
    ).all()
    months: dict[str, set[int]] = {}
    for code, observed_at in rows:
        if observed_at is not None:
            months.setdefault(code, set()).add(observed_at.month)
    return {code: _seasonal_factor(m, now.month) for code, m in months.items()}


def score_catalog_trails(
    db: Session,
    trail_ids: list[int],
    buffer_m: float = 8000,
    window_days: int = _SCORE_WINDOW_DAYS,
) -> dict[int, dict]:
    """Recency-weighted wildlife scores for many catalog trails, from cached eBird sightings.

    For each trail we gather the species reported within `buffer_m` of its geometry (line if
    matched, else trailhead point), weight each by how recently it was last seen (so stale
    reports fade rather than counting forever), and saturate the sum into two 0..98 scores:
    an overall `score` (all species - "how alive is this place") and a `notable_score` (only
    species from eBird's notable feed - "odds of something unusual"). Each species' weight is
    also scaled by a seasonal factor (`species_seasonality`), so an out-of-season vagrant counts
    for less than an in-season regular. Still an area-level proxy, not a calibrated probability.
    One spatial join feeds every trail; ranking happens in Python. Returns per trail id: `score`,
    `notable_score`, `species_count`, `notable_count`, `top_species`, and `top_notable`.
    """
    if not trail_ids:
        return {}
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=window_days)
    trail_geog = func.cast(func.coalesce(CatalogTrail.line_geom, CatalogTrail.geom), Geography)
    sight_geog = func.cast(WildlifeSighting.geom, Geography)
    rows = db.execute(
        select(
            CatalogTrail.id,
            WildlifeSighting.species_code,
            WildlifeSighting.common_name,
            WildlifeSighting.observed_at,
            WildlifeSighting.is_notable,
        )
        .join(
            WildlifeSighting,
            and_(
                func.ST_DWithin(trail_geog, sight_geog, buffer_m),
                WildlifeSighting.observed_at >= cutoff,
            ),
            isouter=True,
        )
        .where(CatalogTrail.id.in_(trail_ids))
    ).all()

    # Per trail, collapse to one entry per species: its most recent date and whether it's ever
    # arrived via the notable feed nearby.
    _floor = datetime.min.replace(tzinfo=UTC)
    per: dict[int, dict[str, dict]] = {tid: {} for tid in trail_ids}
    for tid, code, name, observed_at, notable in rows:
        if code is None:  # outer-join row for a trail with no nearby sightings
            continue
        entry = per[tid].get(code)
        if entry is None:
            per[tid][code] = {"name": name, "observed_at": observed_at, "notable": bool(notable)}
        else:
            if (observed_at or _floor) > (entry["observed_at"] or _floor):
                entry["observed_at"] = observed_at
            entry["notable"] = entry["notable"] or bool(notable)

    # Seasonal factor per species (one pass over all species present near these trails).
    all_codes = {code for tid in trail_ids for code in per[tid]}
    season = species_seasonality(db, list(all_codes), ref_date=now)

    result: dict[int, dict] = {}
    for tid in trail_ids:
        species = [
            {
                "species_code": code,
                "common_name": e["name"],
                "last_observed": e["observed_at"],
                "notable": e["notable"],
                "season": season.get(code, 1.0),
                "weight": _recency_weight(e["observed_at"], now) * season.get(code, 1.0),
            }
            for code, e in per[tid].items()
        ]
        species.sort(key=lambda s: s["weight"], reverse=True)
        notable = [s for s in species if s["notable"]]
        result[tid] = {
            "score": _saturating_score(sum(s["weight"] for s in species), _ACTIVITY_SATURATION),
            "notable_score": _saturating_score(
                sum(s["weight"] for s in notable), _NOTABLE_SATURATION
            ),
            "species_count": len(species),
            "notable_count": len(notable),
            "top_species": species,
            "top_notable": notable,
        }
    return result
