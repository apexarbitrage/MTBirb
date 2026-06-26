"""Slope aspect (which way the trail's hillsides face) and a sun-exposure score, from the DEM.

Aspect is the missing per-trail differentiator under shared regional weather: a north-facing
(in the N hemisphere) trail stays shaded, cooler, and wetter/muddier longer than a south-facing one
nearby. We estimate it by sampling the DEM at four neighbours (N/S/E/W) around points along the
line, taking the local gradient, and reducing to a slope-weighted dominant downhill bearing
(8-point compass) plus a 0..1 `sun_exposure` (1 = fully equator-facing/sunny, 0.5 = flat/neutral).
The aspect math is pure and unit-tested; `compute_aspect` does the DEM sampling via an elevation
client (see integrations/elevation.py) and the optimal-now sort will later fold these in.
"""

from __future__ import annotations

import math

_COMPASS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
# Neighbour offset by DEM tier: USGS (~1-10m) resolves a tighter sample than Open-Meteo (~90m).
_OFFSET_M = {"usgs": 60.0, "open-meteo": 150.0}
# Slope (rise/run) at which aspect is fully trusted; gentler ground is weighted down toward neutral.
_SLOPE_FULL = 0.15
# Below this summed slope across the sampled points the line is ~flat - aspect is meaningless.
_MIN_TOTAL_SLOPE = 0.25
_EARTH_M_PER_DEG = 111_320.0


def _compass(bearing: float) -> str:
    return _COMPASS[int((bearing + 22.5) % 360 // 45)]


def aspect_from_neighbors(
    north: float, south: float, east: float, west: float, offset_m: float, lat: float
) -> dict:
    """Local downhill aspect + sun exposure from a point's four DEM neighbours (metres)."""
    dzdx = (east - west) / (2 * offset_m)  # +x east
    dzdy = (north - south) / (2 * offset_m)  # +y north
    slope = math.hypot(dzdx, dzdy)
    # The hillside faces downhill = the negative of the (uphill) gradient. Bearing is measured
    # clockwise from north, so its east component is sin and north component is cos.
    bearing = math.degrees(math.atan2(-dzdx, -dzdy)) % 360.0
    # Equator-facing is sunny: aim at due-south (180) in the N hemisphere, due-north (0) in the S.
    target = 180.0 if lat >= 0 else 0.0
    facing = (1 + math.cos(math.radians(bearing - target))) / 2  # 1 = fully equator-facing
    weight = min(slope / _SLOPE_FULL, 1.0)  # flat ground -> neutral
    sun_exposure = 0.5 + (facing - 0.5) * weight
    return {"aspect": _compass(bearing), "bearing": bearing, "slope": slope, "sun_exposure": sun_exposure}


async def compute_aspect(client, samples: list[tuple[float, float]], source: str) -> dict:
    """Dominant aspect + mean sun-exposure for a trail, sampling the DEM around points on its line.

    `samples` are the (lat, lon) resample points; `client` is an elevation client whose
    `lookup(points)` returns metres. Returns {"aspect": str|None, "sun_exposure": float|None};
    None when the line is too flat for aspect to mean anything.
    """
    offset_m = _OFFSET_M.get(source, 100.0)
    points = samples[::2][:12] or samples[:1]
    neighbors: list[tuple[float, float]] = []
    for lat, lon in points:
        dlat = offset_m / _EARTH_M_PER_DEG
        dlon = offset_m / (_EARTH_M_PER_DEG * max(math.cos(math.radians(lat)), 0.01))
        neighbors += [(lat + dlat, lon), (lat - dlat, lon), (lat, lon + dlon), (lat, lon - dlon)]

    elevs = await client.lookup(neighbors)
    sum_e = sum_n = sum_sun = sum_w = 0.0
    for i, (lat, _lon) in enumerate(points):
        n, s, e, w = elevs[4 * i : 4 * i + 4]
        a = aspect_from_neighbors(n, s, e, w, offset_m, lat)
        slope, br = a["slope"], math.radians(a["bearing"])
        sum_e += slope * math.sin(br)
        sum_n += slope * math.cos(br)
        sum_sun += a["sun_exposure"] * slope
        sum_w += slope

    if sum_w < _MIN_TOTAL_SLOPE:
        return {"aspect": None, "sun_exposure": None}
    bearing = math.degrees(math.atan2(sum_e, sum_n)) % 360.0
    return {"aspect": _compass(bearing), "sun_exposure": round(sum_sun / sum_w, 3)}
