"""Scores a trail's likelihood of a wildlife encounter from cached eBird sightings.

This is a first-pass proxy (raw nearby-observation counts), not a calibrated probability.
It does not yet account for search effort (checklists per area), seasonality, or time of
day, which is exactly the modeling work flagged as needing the most design time before this
becomes the "highest chance of seeing an owl" feature described in the product plan.
"""

from datetime import UTC, datetime, timedelta

from geoalchemy2.types import Geography
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Trail, WildlifeSighting


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
