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

# Species-richness saturation constant for the first-pass score: score = 100*(1-e^(-n/K)).
# Tuned so the realistic 8 km richness range (~15-65 species) spreads across ~40-90.
_SCORE_SATURATION = 28.0
_MAX_SCORE = 98


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


def _score_from_richness(species_count: int) -> int:
    """A saturating 0..MAX score from the number of distinct species reported nearby."""
    if species_count <= 0:
        return 0
    return min(_MAX_SCORE, round(100 * (1 - math.exp(-species_count / _SCORE_SATURATION))))


def score_catalog_trails(
    db: Session,
    trail_ids: list[int],
    buffer_m: float = 8000,
    lookback_days: int = 30,
) -> dict[int, dict]:
    """First-pass wildlife-activity score for many catalog trails, from cached sightings.

    For each trail, counts the distinct species reported to eBird within `buffer_m` of its
    geometry (line if matched, else trailhead point) in the lookback window, and turns that
    richness into a saturating 0..98 score. This is a relative, area-level proxy - the same
    raw-signal caveat as the rest of this module - not a calibrated probability. One spatial
    join feeds all the trails; aggregation/ranking happens in Python. Returns, per trail id:
    `score`, `species_count`, and `top_species` (most-recent first).
    """
    if not trail_ids:
        return {}
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    trail_geog = func.cast(func.coalesce(CatalogTrail.line_geom, CatalogTrail.geom), Geography)
    sight_geog = func.cast(WildlifeSighting.geom, Geography)
    rows = db.execute(
        select(
            CatalogTrail.id,
            WildlifeSighting.species_code,
            WildlifeSighting.common_name,
            WildlifeSighting.observed_at,
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

    # Per trail, keep the most recent observation of each species.
    _floor = datetime.min.replace(tzinfo=UTC)
    per: dict[int, dict[str, tuple[str, datetime | None]]] = {tid: {} for tid in trail_ids}
    for tid, code, name, observed_at in rows:
        if code is None:  # outer-join row for a trail with no nearby sightings
            continue
        existing = per[tid].get(code)
        if existing is None or (observed_at or _floor) > (existing[1] or _floor):
            per[tid][code] = (name, observed_at)

    result: dict[int, dict] = {}
    for tid in trail_ids:
        species = per[tid]
        top = sorted(species.items(), key=lambda kv: kv[1][1] or _floor, reverse=True)
        result[tid] = {
            "score": _score_from_richness(len(species)),
            "species_count": len(species),
            "top_species": [
                {"species_code": code, "common_name": name, "last_observed": observed_at}
                for code, (name, observed_at) in top
            ],
        }
    return result
