"""Multi-trail routes: chaining adjacent catalog trails into one saved, ridable route.

A TrailRoute stores only the ordered member external_ids (models/trail_route.py); everything else
- the combined line, summed stats, species - is recomputed from the member rows at read time. This
module holds both halves of that:

- The **spatial queries** behind the route builder: which trails' OSM lines come within
  `_CHAIN_TOLERANCE_M` of the chain built so far (the candidates a rider can tap to add), which
  nearby un-lined trails are worth background-enriching so they can become candidates, and the
  create-time validation that a submitted chain really connects. All geometry references are built
  as SQL subqueries (never ORM geometry values round-tripped through Python - see CLAUDE.md), and
  the candidate filter targets `line_geom::geography` directly so migration 0012's functional GiST
  index applies.
- The **pure helpers** for presenting a route: orienting + concatenating member lines into one
  polyline, summing member metrics honestly (some members may never have been mapped), and gating
  which un-lined trails to enrich (so the builder's poll loop can't re-hammer Overpass for a trail
  whose line assembly already failed).
"""

import json
from datetime import UTC, datetime, timedelta

from geoalchemy2.types import Geography
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CatalogTrail, WildlifeSighting
from app.services.catalog_geometry import _haversine_m

# A trail "connects" to the chain if its line comes within this many meters. Wider than
# stitch_ways' 70 m gap tolerance on purpose: distinct named trails often meet across a junction,
# parking lot, or fire-road crossing rather than sharing a node.
_CHAIN_TOLERANCE_M = 100.0
# Un-lined trails only have a trailhead point, which can sit well away from where the trail itself
# approaches the chain - so the enrichment search radius is much wider than the chain tolerance.
_UNLINED_SEARCH_M = 1500.0
# Bounded Overpass work per candidates request (politeness; same concern as enrich_region).
_MAX_ENRICH = 8
_MAX_MEMBERS = 20
# Candidate lists stay small: everything within 100 m of the chain, capped for response size.
_MAX_CANDIDATES = 30
# When two member lines meet at (nearly) the same point, drop the duplicated joint vertex.
_JOINT_DEDUPE_M = 5.0


def _chain_geog(member_ids: list[str]):
    """The whole chain (members' lines, or trailhead points while un-lined) as one geography,
    built as a scalar subquery so the geometry never round-trips through Python."""
    geom = func.coalesce(CatalogTrail.line_geom, CatalogTrail.geom)
    return (
        select(func.cast(func.ST_Collect(geom), Geography))
        .where(CatalogTrail.external_id.in_(member_ids))
        .scalar_subquery()
    )


def lined_candidates(
    db: Session, member_ids: list[str], limit: int = _MAX_CANDIDATES
) -> list[CatalogTrail]:
    """Trails whose OSM line comes within the chain tolerance of the current route - the trails
    the builder offers next. Filters on `line_geom::geography` (not the coalesce) so the functional
    geography index from migration 0012 applies."""
    chain = _chain_geog(member_ids)
    line_geog = func.cast(CatalogTrail.line_geom, Geography)
    return list(
        db.scalars(
            select(CatalogTrail)
            .where(
                CatalogTrail.line_geom.is_not(None),
                CatalogTrail.external_id.not_in(member_ids),
                func.ST_DWithin(line_geog, chain, _CHAIN_TOLERANCE_M),
            )
            .order_by(CatalogTrail.name)
            .limit(limit)
        )
    )


def unlined_nearby(
    db: Session, member_ids: list[str], limit: int = _MAX_ENRICH
) -> list[CatalogTrail]:
    """Un-lined trails whose trailhead point sits near the chain - the ones worth background-
    enriching so they can become candidates once their line lands."""
    chain = _chain_geog(member_ids)
    point_geog = func.cast(CatalogTrail.geom, Geography)
    return list(
        db.scalars(
            select(CatalogTrail)
            .where(
                CatalogTrail.line_geom.is_(None),
                CatalogTrail.external_id.not_in(member_ids),
                func.ST_DWithin(point_geog, chain, _UNLINED_SEARCH_M),
            )
            .order_by(func.ST_Distance(point_geog, chain))
            .limit(limit)
        )
    )


def connects_to(db: Session, ids_so_far: list[str], candidate_external_id: str) -> bool:
    """Whether a trail's line comes within the chain tolerance of the route built so far. The
    same ST_DWithin predicate as `lined_candidates`, so create-time validation can never reject
    a candidate the builder offered."""
    candidate_geog = (
        select(func.cast(CatalogTrail.line_geom, Geography))
        .where(CatalogTrail.external_id == candidate_external_id)
        .scalar_subquery()
    )
    return bool(
        db.scalar(select(func.ST_DWithin(_chain_geog(ids_so_far), candidate_geog, _CHAIN_TOLERANCE_M)))
    )


def lines_for(db: Session, external_ids: list[str]) -> dict[str, list[list[float]]]:
    """The OSM lines for many trails in one query: {external_id: [[lon, lat], ...]}. Trails
    without a line are simply absent."""
    if not external_ids:
        return {}
    rows = db.execute(
        select(CatalogTrail.external_id, func.ST_AsGeoJSON(CatalogTrail.line_geom)).where(
            CatalogTrail.external_id.in_(external_ids),
            CatalogTrail.line_geom.is_not(None),
        )
    ).all()
    return {ext_id: json.loads(geojson)["coordinates"] for ext_id, geojson in rows}


def recent_species_near_route(
    db: Session,
    member_ids: list[str],
    buffer_m: float = 8000,
    lookback_days: int = 14,
    limit: int = 8,
) -> list[dict]:
    """Species recently reported near any part of the route - one union-buffer query over the
    members' geometries (no per-member merging, so nothing is double-counted). The line-or-point
    coalesce + ST_Buffer/ST_Intersects pattern mirrors `recent_species_near_catalog`."""
    buffered = func.ST_Buffer(_chain_geog(member_ids), buffer_m)
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
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


def concat_member_lines(lines: list[list[list[float]]]) -> list[list[float]]:
    """Orient and concatenate member lines (each [[lon, lat], ...], in chain order) into one
    polyline. Each segment is flipped if that brings its start nearer the chain's tail, and a
    joint vertex duplicated across the seam is dropped. Members meet within the chain tolerance
    but not necessarily exactly, so a small gap simply becomes a straight connector (consecutive
    points render/export as a straight line - fine at <=100 m)."""
    segments = [seg for seg in lines if seg and len(seg) >= 2]
    if not segments:
        return []
    first = segments[0]
    if len(segments) > 1:
        # Point the first segment's tail at the next member: flip it if its *start* is the end
        # nearer segment 2 (nearest of that segment's two endpoints).
        nxt = segments[1]
        d_from_end = min(_haversine_m(first[-1], nxt[0]), _haversine_m(first[-1], nxt[-1]))
        d_from_start = min(_haversine_m(first[0], nxt[0]), _haversine_m(first[0], nxt[-1]))
        if d_from_start < d_from_end:
            first = first[::-1]
    chain = list(first)
    for seg in segments[1:]:
        tail = chain[-1]
        if _haversine_m(tail, seg[-1]) < _haversine_m(tail, seg[0]):
            seg = seg[::-1]
        joint = 1 if _haversine_m(tail, seg[0]) <= _JOINT_DEDUPE_M else 0
        chain.extend(seg[joint:])
    return chain


def route_stats(members: list) -> dict:
    """Summed terrain stats over a route's member trails, honest about coverage: only members
    with computed metrics contribute, and `mapped_count` lets the UI say "N of M trails mapped"
    instead of presenting a partial sum as the whole route. Length falls back to the catalog's
    nominal `length_mi` for unmapped members so the total is still useful."""

    def _sum(values: list) -> float | int | None:
        present = [v for v in values if v is not None]
        return sum(present) if present else None

    miles = _sum([m.metric_length_mi if m.metric_length_mi is not None else m.length_mi for m in members])
    highs = [m.high_point_ft for m in members if m.high_point_ft is not None]
    lows = [m.low_point_ft for m in members if m.low_point_ft is not None]
    return {
        "trail_count": len(members),
        "mapped_count": sum(1 for m in members if m.metric_length_mi is not None),
        "miles": round(miles, 1) if miles is not None else None,
        "ascent_ft": _sum([m.ascent_ft for m in members]),
        "descent_ft": _sum([m.descent_ft for m in members]),
        "ride_time_min": _sum([m.ride_time_min for m in members]),
        "high_point_ft": max(highs) if highs else None,
        "low_point_ft": min(lows) if lows else None,
    }


def pick_enrich_targets(
    unlined_ids: list[str],
    attempted: set[str],
    in_flight: set[str],
    limit: int = _MAX_ENRICH,
) -> list[str]:
    """Which un-lined trails to kick a background line-enrichment for. Skips ids already attempted
    this process (a failed assembly leaves line_geom null with no persisted marker - without this
    gate the builder's poll loop would re-hit Overpass for the same un-lineable trail every 2.5 s)
    and ids currently in flight. Order (nearest first) is preserved."""
    picks = [i for i in unlined_ids if i not in attempted and i not in in_flight]
    return picks[:limit]
