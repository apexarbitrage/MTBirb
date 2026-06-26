"""Derive terrain metrics for a trail line from a DEM elevation profile.

Given a trail's OSM line, we resample it to a fixed number of evenly-spaced points, look up
each point's ground elevation (via an elevation client), and reduce that into the metrics the
design shows: total climb/descent, average up/down grade, a normalized elevation profile, plus
heuristic ride-time and effort estimates. The pure math here is independent of which DEM tier
(Open-Meteo or USGS) supplied the elevations - `ensure_metrics` ties a client to a trail.
"""

from __future__ import annotations

import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CatalogTrail
from app.services.trail_catalog import line_points
from app.services.trail_surface import compute_aspect

_M_PER_FT = 0.3048
_M_PER_MI = 1609.344
# Sample count along the line. Enough for a readable profile and a stable grade without making
# the USGS pass (one HTTP call per point) slow.
SAMPLE_POINTS = 24
# DEM elevations are noisy; ignore sub-metre wiggles so total climb isn't inflated by jitter.
_NOISE_FLOOR_M = 1.0
# Below this mapped length the line is a fragment (often an OSM name mismatch), and DEM noise
# dominates the profile - producing nonsense grades. We skip metrics rather than fabricate them.
_MIN_METRIC_LENGTH_M = 500.0
# Sentinel `elev_source` for a line too short to derive trustworthy metrics from.
_TOO_SHORT = "too-short"
_METRIC_FIELDS = (
    "metric_length_mi", "ascent_ft", "descent_ft", "avg_up_grade",
    "avg_down_grade", "elevation_profile", "ride_time_min", "effort",
    "max_grade", "high_point_ft", "low_point_ft", "longest_climb_mi",
    "aspect", "sun_exposure",
)


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def resample(points: list[list[float]], n: int) -> tuple[list[tuple[float, float]], float]:
    """Resample a [[lon, lat], ...] polyline to n points evenly spaced by distance.

    Returns the sample points as (lat, lon) pairs (the order elevation clients expect) and the
    polyline's total length in metres.
    """
    if n < 2 or len(points) < 2:
        lon, lat = points[0]
        return [(lat, lon)] * max(n, 1), 0.0

    cum = [0.0]
    for i in range(1, len(points)):
        seg = _haversine_m(points[i - 1][0], points[i - 1][1], points[i][0], points[i][1])
        cum.append(cum[-1] + seg)
    total = cum[-1]
    if total == 0:
        lon, lat = points[0]
        return [(lat, lon)] * n, 0.0

    samples: list[tuple[float, float]] = []
    seg_idx = 0
    for k in range(n):
        target = total * k / (n - 1)
        while seg_idx < len(cum) - 2 and cum[seg_idx + 1] < target:
            seg_idx += 1
        span = cum[seg_idx + 1] - cum[seg_idx]
        frac = 0.0 if span == 0 else (target - cum[seg_idx]) / span
        lon0, lat0 = points[seg_idx]
        lon1, lat1 = points[seg_idx + 1]
        samples.append((lat0 + (lat1 - lat0) * frac, lon0 + (lon1 - lon0) * frac))
    return samples, total


def compute(elevations_m: list[float], total_m: float) -> dict:
    """Reduce evenly-spaced elevations + total length into the trail's terrain metrics."""
    n = len(elevations_m)
    seg_m = total_m / (n - 1) if n > 1 else 0.0

    ascent_m = descent_m = 0.0
    up_run_m = down_run_m = 0.0
    max_up_grade = 0.0
    longest_climb_m = cur_climb_m = 0.0
    for i in range(1, n):
        delta = elevations_m[i] - elevations_m[i - 1]
        if delta > _NOISE_FLOOR_M:
            ascent_m += delta
            up_run_m += seg_m
            cur_climb_m += seg_m
            longest_climb_m = max(longest_climb_m, cur_climb_m)
            if seg_m:
                max_up_grade = max(max_up_grade, delta / seg_m * 100)
        else:
            # A descent or a near-flat bench both end the current sustained climb.
            if delta < -_NOISE_FLOOR_M:
                descent_m += -delta
                down_run_m += seg_m
            cur_climb_m = 0.0

    lo, hi = min(elevations_m), max(elevations_m)
    span = hi - lo or 1.0
    profile = [round((e - lo) / span, 3) for e in elevations_m]

    miles = total_m / _M_PER_MI
    ascent_ft = ascent_m / _M_PER_FT
    descent_ft = descent_m / _M_PER_FT
    avg_up = (ascent_m / up_run_m * 100) if up_run_m else 0.0
    avg_down = (descent_m / down_run_m * 100) if down_run_m else 0.0

    # Heuristic estimates (not from the DEM): a flat-ground pace of ~10 mph plus a climbing
    # penalty, and an effort index that grows with distance and total climb. Labelled as
    # estimates in the UI - they stand in until a calibrated effort model lands.
    ride_min = round(miles * 6.0 + ascent_ft * 0.012)
    effort = round(min(10.0, max(1.0, miles * 0.5 + ascent_ft / 500.0)), 1)

    return {
        "metric_length_mi": round(miles, 2),
        "ascent_ft": round(ascent_ft),
        "descent_ft": round(descent_ft),
        "avg_up_grade": f"{avg_up:.1f}%",
        "avg_down_grade": f"{avg_down:.1f}%",
        "elevation_profile": profile,
        "ride_time_min": int(ride_min),
        "effort": effort,
        "max_grade": f"{max_up_grade:.0f}%",
        "high_point_ft": round(hi / _M_PER_FT),
        "low_point_ft": round(lo / _M_PER_FT),
        "longest_climb_mi": round(longest_climb_m / _M_PER_MI, 2),
    }


async def ensure_metrics(db: Session, trail: CatalogTrail, client, *, force: bool = False) -> bool:
    """Compute + store terrain metrics for a catalog trail using the given elevation client.

    No-op (returns False) if the trail has no line yet, or if it already carries metrics from
    this client's tier and `force` is False. Records which tier produced them in `elev_source`.
    """
    if trail.line_geom is None:
        return False
    if not force and trail.elev_source == _TOO_SHORT:
        return False
    # Re-run if this tier already produced the metrics, unless a newer field (aspect) is missing -
    # that lets trails computed before aspect existed backfill it on the next detail open.
    if not force and trail.elev_source == client.source and trail.aspect is not None:
        return False
    points = line_points(db, trail.id)
    if not points or len(points) < 2:
        return False

    samples, total_m = resample(points, SAMPLE_POINTS)
    if total_m < _MIN_METRIC_LENGTH_M:
        # Too fragmentary to trust: drop any stale metrics and mark it so we don't keep retrying.
        for field in _METRIC_FIELDS:
            setattr(trail, field, None)
        trail.elev_source = _TOO_SHORT
        db.commit()
        return False
    elevations = await client.lookup(samples)
    metrics = compute(elevations, total_m)

    trail.metric_length_mi = metrics["metric_length_mi"]
    trail.ascent_ft = metrics["ascent_ft"]
    trail.descent_ft = metrics["descent_ft"]
    trail.avg_up_grade = metrics["avg_up_grade"]
    trail.avg_down_grade = metrics["avg_down_grade"]
    trail.elevation_profile = metrics["elevation_profile"]
    trail.ride_time_min = metrics["ride_time_min"]
    trail.effort = metrics["effort"]
    trail.max_grade = metrics["max_grade"]
    trail.high_point_ft = metrics["high_point_ft"]
    trail.low_point_ft = metrics["low_point_ft"]
    trail.longest_climb_mi = metrics["longest_climb_mi"]
    try:
        aspect = await compute_aspect(client, samples, client.source)
        trail.aspect = aspect["aspect"]
        trail.sun_exposure = aspect["sun_exposure"]
    except Exception:  # noqa: BLE001 - aspect is a bonus; keep the elevation metrics on failure
        pass
    trail.elev_source = client.source
    db.commit()
    return True


async def bulk_compute_metrics(
    db: Session,
    lat_range: tuple[float, float],
    lon_range: tuple[float, float],
    client,
    *,
    max_trails: int = 200,
    force: bool = False,
) -> dict:
    """The fast initial pass: compute metrics for lined catalog trails in a bbox.

    Skips trails already carrying metrics from this client's tier (unless `force`). Intended for
    the Open-Meteo tier; the USGS refinement happens per-trail when a detail is opened.
    """
    query = select(CatalogTrail).where(
        CatalogTrail.lat.between(*lat_range),
        CatalogTrail.lon.between(*lon_range),
        CatalogTrail.line_geom.is_not(None),
    )
    if not force:
        query = query.where(CatalogTrail.elev_source.is_distinct_from(client.source))
    trails = list(db.scalars(query.limit(max_trails)))

    computed = 0
    for trail in trails:
        try:
            computed += int(await ensure_metrics(db, trail, client, force=force))
        except Exception:  # noqa: BLE001 - one DEM failure shouldn't abort the batch
            continue
    return {"source": client.source, "candidates": len(trails), "computed": computed}
