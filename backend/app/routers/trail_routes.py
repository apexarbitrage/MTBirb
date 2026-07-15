"""Saved multi-trail routes: build, save, browse, and export chains of adjacent trails.

The builder's one data source is GET /trail-routes/candidates: given the chain so far it returns
the members (with lines), every lined trail within the chain tolerance (the tappable candidates),
and kicks *bounded* background line-enrichment for the nearest un-lined trails (the same
fire-and-forget Overpass/USGS pattern as the catalog detail) - the client polls while
`enrichingCount` drains, so candidates pop in as their lines land.

Everything else recomputes a saved route from its member rows at read time (combined line, summed
stats, union species, wildlife score), so routes improve as members' metrics refine. Endpoints are
open (genuine user actions, same policy as trips - see app/security.py); like trips there are no
accounts yet, so routes are one global set.
"""

import asyncio
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.db import get_db
from app.integrations.weather import WeatherClient
from app.models import CatalogTrail, TrailRoute
from app.routers.catalog import (
    _AREA_BUFFER_M,
    _DISPLAY_LINE_POINTS,
    _enrich_trail_background,
    _enriching_trails,
    _surface_assessment,
)
from app.schemas.trail_route import (
    RouteTrailLite,
    TrailRouteCreate,
    TrailRouteDetailOut,
    TrailRouteSummaryOut,
)
from app.services.gpx import build_gpx, slugify
from app.services.optimal_ride_time import score_optimal_window
from app.services.trail_conditions import grade_pct, per_trail_surface_factor
from app.services.trail_routes import (
    _MAX_MEMBERS,
    concat_member_lines,
    connects_to,
    lined_candidates,
    lines_for,
    pick_enrich_targets,
    recent_species_near_route,
    route_stats,
    unlined_nearby,
)
from app.services.wildlife_likelihood import score_catalog_trails

router = APIRouter(prefix="/trail-routes", tags=["trail-routes"])
logger = logging.getLogger(__name__)

# external_ids we've already kicked a line-enrichment for this process. A failed assembly leaves
# line_geom null with no persisted marker, so without this the builder's poll loop would re-hit
# Overpass for the same un-lineable trail on every poll.
_line_attempted: set[str] = set()


def _route_or_404(db: Session, route_id: int) -> TrailRoute:
    route = db.get(TrailRoute, route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="route not found")
    return route


def _member_rows(db: Session, external_ids: list[str]) -> tuple[list[CatalogTrail], list[str]]:
    """The catalog rows for a route's members, in chain order, plus any ids no longer cataloged
    (a route must keep rendering from its survivors)."""
    rows = db.scalars(select(CatalogTrail).where(CatalogTrail.external_id.in_(external_ids)))
    by_ext = {t.external_id: t for t in rows}
    members = [by_ext[i] for i in external_ids if i in by_ext]
    missing = [i for i in external_ids if i not in by_ext]
    return members, missing


def _max_stored_score(members: list[CatalogTrail]) -> int | None:
    """The route's wildlife score as the max over members' precomputed scores - honest because a
    connected chain's members share nearly the same 8 km sighting buffer. None until any member
    has been scored."""
    scores = [m.wildlife_score.get("score") for m in members if m.wildlife_score]
    scores = [s for s in scores if s is not None]
    return max(scores) if scores else None


def _combined_line(db: Session, members: list[CatalogTrail]) -> list[list[float]]:
    lines = lines_for(db, [m.external_id for m in members])
    ordered = [lines[m.external_id] for m in members if m.external_id in lines]
    return concat_member_lines(ordered)


def _candidates_data(db: Session, ids: list[str]) -> tuple[list, list[str], list, dict]:
    """The candidates endpoint's synchronous DB work, bundled so the async handler can push it
    to the threadpool in one hop: member rows, the chain-tolerance spatial query, and the
    display-thinned lines (full OSM density is for GPX/geometry math, not builder payloads)."""
    members, missing = _member_rows(db, ids)
    if missing:
        return members, missing, [], {}
    candidates = lined_candidates(db, ids)
    lines = lines_for(db, ids + [c.external_id for c in candidates], max_points=_DISPLAY_LINE_POINTS)
    return members, missing, candidates, lines


@router.get("/candidates")
async def route_candidates(
    ids: list[str] = Query(..., min_length=1, max_length=_MAX_MEMBERS),
    db: Session = Depends(get_db),
) -> dict:
    """The builder's data source: the chain's members, the lined trails within the chain tolerance
    (tappable candidates), and a bounded background enrichment kick for nearby un-lined trails.
    `enrichingCount` > 0 means lines are still landing - the client polls until it drains."""
    # Threadpooled: these are the heaviest spatial queries on any hot path, and this endpoint
    # fires on every tap in the builder - run inline they'd freeze the event loop (see CLAUDE.md).
    members, missing, candidates, lines = await run_in_threadpool(_candidates_data, db, ids)
    if missing:
        raise HTTPException(status_code=404, detail=f"unknown trail ids: {', '.join(missing)}")

    # Hybrid coverage: lined candidates return instantly; the nearest un-lined trails get a
    # bounded background line-assembly so they can join the candidate set on a later poll.
    # Skipped when this deploy can't reach Overpass (OVERPASS_ENABLED=false) - a hanging call
    # holds a DB connection, and 8 at once is the pool-exhaustion/502 recipe; on such deploys
    # candidates come from the seeded lines alone (enrichingCount 0 = client doesn't poll).
    enriching: set[str] = set()
    if get_settings().overpass_enabled:
        unlined = await run_in_threadpool(unlined_nearby, db, ids)
        targets = pick_enrich_targets(
            [t.external_id for t in unlined], _line_attempted, _enriching_trails
        )
        for ext_id in targets:
            _line_attempted.add(ext_id)
            asyncio.create_task(_enrich_trail_background(ext_id))
        # Just-kicked tasks haven't hit the in-flight set yet (they start on the next loop tick).
        enriching = {t.external_id for t in unlined} & _enriching_trails | set(targets)

    return {
        "members": [RouteTrailLite.from_model(m, lines.get(m.external_id)) for m in members],
        "candidates": [RouteTrailLite.from_model(c, lines.get(c.external_id)) for c in candidates],
        "enrichingCount": len(enriching),
    }


@router.post("")
def create_trail_route(body: TrailRouteCreate, db: Session = Depends(get_db)) -> TrailRouteSummaryOut:
    """Save a route. Connectivity is re-validated server-side with the same ST_DWithin predicate
    the candidates endpoint offers from, so a chain the builder produced can't be rejected here."""
    ids = body.trailIds
    if len(set(ids)) != len(ids):
        raise HTTPException(status_code=422, detail="a trail can only appear in a route once")
    members, missing = _member_rows(db, ids)
    if missing:
        raise HTTPException(status_code=422, detail=f"unknown trail ids: {', '.join(missing)}")
    by_ext = {m.external_id: m for m in members}
    unlined = [i for i in ids if by_ext[i].line_geom is None]
    if unlined:
        raise HTTPException(
            status_code=422, detail=f"trails without a mapped line can't be chained: {', '.join(unlined)}"
        )
    for i in range(1, len(ids)):
        if not connects_to(db, ids[:i], ids[i]):
            raise HTTPException(
                status_code=422,
                detail=f"trail {ids[i]} does not connect to the route (within 100 m)",
            )

    route = TrailRoute(name=body.name, trail_external_ids=ids)
    db.add(route)
    db.commit()
    db.refresh(route)
    return TrailRouteSummaryOut.from_model(route, route_stats(members), _max_stored_score(members))


@router.get("")
def list_trail_routes(db: Session = Depends(get_db)) -> dict:
    """All saved routes, newest first, with combined headline stats recomputed from members."""
    routes = list(
        db.scalars(select(TrailRoute).order_by(TrailRoute.created_at.desc(), TrailRoute.id.desc()))
    )
    all_ids = sorted({i for r in routes for i in r.trail_external_ids})
    rows = db.scalars(select(CatalogTrail).where(CatalogTrail.external_id.in_(all_ids))) if all_ids else []
    by_ext = {t.external_id: t for t in rows}
    out = []
    for r in routes:
        members = [by_ext[i] for i in r.trail_external_ids if i in by_ext]
        out.append(TrailRouteSummaryOut.from_model(r, route_stats(members), _max_stored_score(members)))
    return {"routes": out}


@router.get("/{route_id}")
def get_trail_route(route_id: int, db: Session = Depends(get_db)) -> dict:
    """A route's detail: ordered members, the combined oriented line, summed stats, a live
    wildlife score, and the species reported near any part of the route."""
    route = _route_or_404(db, route_id)
    members, missing = _member_rows(db, route.trail_external_ids)
    # Display-thinned: the detail's map and member rows don't need full OSM density (GPX export
    # rebuilds the combined line from the full-fidelity geometry separately).
    lines = lines_for(db, [m.external_id for m in members], max_points=_DISPLAY_LINE_POINTS)
    combined = concat_member_lines(
        [lines[m.external_id] for m in members if m.external_id in lines]
    )

    # Live score (like the trail detail): max over members - a connected chain shares one area.
    scores = score_catalog_trails(db, [m.id for m in members], buffer_m=_AREA_BUFFER_M)
    live = [s.get("score") for s in scores.values() if s]
    wildlife_score = max(live) if live else None

    species = (
        recent_species_near_route(db, [m.external_id for m in members], buffer_m=_AREA_BUFFER_M)
        if members
        else []
    )
    detail = TrailRouteDetailOut.from_detail(
        route,
        route_stats(members),
        wildlife_score,
        [RouteTrailLite.from_model(m, lines.get(m.external_id)) for m in members],
        missing,
        combined,
    )
    return {"route": detail, "species": species, "areaRadiusKm": _AREA_BUFFER_M / 1000}


@router.delete("/{route_id}", status_code=204)
def delete_trail_route(route_id: int, db: Session = Depends(get_db)) -> Response:
    """Remove a saved route (idempotent). Ride history is untouched - trips keep the route's
    name in trail_name and their route_id simply goes stale."""
    route = db.get(TrailRoute, route_id)
    if route is not None:
        db.delete(route)
        db.commit()
    return Response(status_code=204)


@router.get("/{route_id}/export.gpx")
def export_trail_route_gpx(route_id: int, db: Session = Depends(get_db)) -> Response:
    """Download the whole route as one GPX course. One <trk>/<trkseg>: members meet within the
    chain tolerance, so a small gap becomes a straight connector (multi-trkseg courses import
    inconsistently in Garmin/Strava, and a <=100 m straight jump is below course-routing noise)."""
    route = _route_or_404(db, route_id)
    members, _missing = _member_rows(db, route.trail_external_ids)
    combined = _combined_line(db, members)
    if not combined:
        raise HTTPException(status_code=404, detail="no member trail has a mapped line to export")
    stats = route_stats(members)
    desc_parts = [f"{stats['trail_count']} trails"]
    if stats["miles"] is not None:
        desc_parts.append(f"{stats['miles']} mi")
    gpx = build_gpx(route.name, combined, desc=" · ".join(desc_parts))
    return Response(
        content=gpx,
        media_type="application/gpx+xml",
        headers={"Content-Disposition": f'attachment; filename="{slugify(route.name)}.gpx"'},
    )


@router.get("/{route_id}/optimal-time")
async def trail_route_optimal_time(route_id: int, db: Session = Depends(get_db)) -> dict:
    """Best time-of-day to ride the route - the same model as a trail's optimal-time, anchored at
    the route's starting trailhead (weather/sun barely vary across a chain a few miles long) with
    the wildlife term as the max member score. Response shape matches the trail endpoint so the
    frontend reuses its types and curve screen."""
    route = _route_or_404(db, route_id)
    members, _missing = _member_rows(db, route.trail_external_ids)
    if not members:
        raise HTTPException(status_code=404, detail="route has no member trails left")
    rep = members[0]
    now = datetime.now(UTC)

    scores = await run_in_threadpool(
        score_catalog_trails, db, [m.id for m in members], buffer_m=_AREA_BUFFER_M
    )
    live = [s.get("score", 0) for s in scores.values() if s]
    trail_score = max(live) if live else 0

    surface = await _surface_assessment(rep.lat, rep.lon, now)
    base_factor = surface["factor"] if surface else 1.0
    surface_factor = per_trail_surface_factor(
        base_factor, rep.sun_exposure, grade_pct(rep.avg_up_grade), rep.surface
    )
    trail_conditions = {"score": surface["score"], "label": surface["label"]} if surface else None

    try:
        hourly = await WeatherClient().forecast_hourly(rep.lat, rep.lon)
    except Exception:  # noqa: BLE001 - no US forecast (or NWS hiccup): degrade, don't error
        return {"route": route_id, "available": False, "date": None, "hours": [],
                "bestWindow": None, "bestWindowWhy": None, "window": None,
                "trailConditions": trail_conditions}
    payload = score_optimal_window(
        hourly, rep.lat, rep.lon, trail_score, now=now, surface_factor=surface_factor
    )
    return {"route": route_id, **payload, "trailConditions": trail_conditions}
