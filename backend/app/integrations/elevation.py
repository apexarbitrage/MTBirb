"""Elevation (DEM) clients for deriving terrain metrics along a trail line.

Two tiers, per the product decision:
  - Open-Meteo (api.open-meteo.com): free, keyless, batches up to 100 points/call, ~90m global
    DEM. Used for the fast initial pass over many trails.
  - USGS EPQS (epqs.nationalmap.gov): free, keyless, ~1-10m US 3DEP, one point per call. Used
    to refine a trail's metrics when its detail is opened.

Both expose `lookup(points)` taking (lat, lon) pairs and returning elevations in meters.
"""

from __future__ import annotations

import asyncio

import httpx

OPEN_METEO_URL = "https://api.open-meteo.com/v1/elevation"
USGS_EPQS_URL = "https://epqs.nationalmap.gov/v1/json"


def _chunks(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


class OpenMeteoElevation:
    source = "open-meteo"

    async def lookup(self, points: list[tuple[float, float]]) -> list[float]:
        out: list[float] = []
        async with httpx.AsyncClient(timeout=30) as client:
            for chunk in _chunks(points, 100):
                lats = ",".join(f"{lat:.6f}" for lat, _ in chunk)
                lons = ",".join(f"{lon:.6f}" for _, lon in chunk)
                resp = await client.get(OPEN_METEO_URL, params={"latitude": lats, "longitude": lons})
                resp.raise_for_status()
                out.extend(float(e) for e in resp.json()["elevation"])
        return out


class UsgsElevation:
    source = "usgs"

    def __init__(self, concurrency: int = 6) -> None:
        self._sem = asyncio.Semaphore(concurrency)

    async def lookup(self, points: list[tuple[float, float]]) -> list[float]:
        async with httpx.AsyncClient(timeout=30) as client:

            async def one(lat: float, lon: float) -> float:
                async with self._sem:
                    resp = await client.get(
                        USGS_EPQS_URL,
                        params={"x": lon, "y": lat, "units": "Meters", "wkid": 4326},
                    )
                    resp.raise_for_status()
                    value = float(resp.json()["value"])
                    # EPQS returns a large negative sentinel for points outside its coverage.
                    return value if value > -1e5 else 0.0

            return list(await asyncio.gather(*(one(lat, lon) for lat, lon in points)))
