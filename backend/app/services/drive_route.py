"""Pure geometry over a driving route's points (no network, no DB).

Two helpers for the "fun drive": a **curviness** read derived from how much the route turns per
kilometre (TomTom doesn't return a curve count, so we compute it), and **waypoint sampling** for the
Google/Apple Maps handoff - a handful of evenly-spaced interior points that make the maps app follow
the same scenic route we show in-app. Points are [lon, lat] pairs, as the TomTom client returns.
"""

from __future__ import annotations

import math

# Degrees of cumulative heading change per km at which the 0..100 score saturates. Using *total*
# turning (not a per-segment threshold) keeps the read stable regardless of how densely TomTom
# samples the polyline. A tight mountain road turns several hundred degrees per km.
_TURN_SATURATION_DEG_PER_KM = 400.0
# Rough cumulative turning that adds up to one "curve", for a human-readable count.
_DEG_PER_CURVE = 45.0


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _bearing(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def _curviness_label(score: int) -> str:
    if score >= 75:
        return "Very twisty"
    if score >= 50:
        return "Twisty"
    if score >= 25:
        return "Moderate"
    return "Mellow"


def curviness(points: list[list[float]]) -> dict:
    """How twisty a route is: {score 0..100, label, curve_count} from heading changes per km."""
    if len(points) < 3:
        return {"score": 0, "label": "Mellow", "curve_count": 0}

    total_m = 0.0
    bearings: list[float] = []
    for i in range(1, len(points)):
        lon1, lat1 = points[i - 1]
        lon2, lat2 = points[i]
        total_m += _haversine_m(lon1, lat1, lon2, lat2)
        bearings.append(_bearing(lon1, lat1, lon2, lat2))

    total_turn = 0.0
    for i in range(1, len(bearings)):
        diff = abs(bearings[i] - bearings[i - 1])
        if diff > 180:
            diff = 360 - diff
        total_turn += diff

    km = max(total_m / 1000.0, 0.1)
    score = round(100 * (1 - math.exp(-(total_turn / km) / _TURN_SATURATION_DEG_PER_KM)))
    curve_count = round(total_turn / _DEG_PER_CURVE)
    return {"score": score, "label": _curviness_label(score), "curve_count": curve_count}


def sample_waypoints(points: list[list[float]], n: int = 8) -> list[list[float]]:
    """`n` evenly-distance-spaced interior [lon, lat] points (excludes start/end) for the maps
    handoff, so the maps app is constrained to follow the route. Capped small by the URL scheme."""
    if len(points) <= 2 or n <= 0:
        return []
    cum = [0.0]
    for i in range(1, len(points)):
        lon1, lat1 = points[i - 1]
        lon2, lat2 = points[i]
        cum.append(cum[-1] + _haversine_m(lon1, lat1, lon2, lat2))
    total = cum[-1]
    if total == 0:
        return []

    waypoints: list[list[float]] = []
    seg = 0
    for k in range(1, n + 1):
        target = total * k / (n + 1)  # interior fractions 1/(n+1) .. n/(n+1)
        while seg < len(cum) - 2 and cum[seg + 1] < target:
            seg += 1
        span = cum[seg + 1] - cum[seg]
        frac = 0.0 if span == 0 else (target - cum[seg]) / span
        lon1, lat1 = points[seg]
        lon2, lat2 = points[seg + 1]
        waypoints.append([lon1 + (lon2 - lon1) * frac, lat1 + (lat2 - lat1) * frac])
    return waypoints
