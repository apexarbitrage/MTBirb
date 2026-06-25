"""Seed the catalog with Northern California trails via a one-time TrailAPI grid sweep.

TrailAPI returns only the nearest 50 trails per call, so coverage comes from sweeping a grid
of points and deduping. Northern California is the first seeded region; everywhere else fills
in on demand as it's browsed (see app/services/trail_catalog.py).

Run with:  python -m app.seed_catalog
"""

from __future__ import annotations

import asyncio

from app.db import SessionLocal
from app.services.trail_catalog import cache_trails_near

# Northern California bounding box and grid step (degrees). ~0.6deg ~= 40 miles.
_LAT_RANGE = (37.5, 42.0)
_LON_RANGE = (-124.2, -119.8)
_STEP = 0.6
_RADIUS_MI = 25


def _grid() -> list[tuple[float, float]]:
    points = []
    lat = _LAT_RANGE[0]
    while lat <= _LAT_RANGE[1] + 1e-9:
        lon = _LON_RANGE[0]
        while lon <= _LON_RANGE[1] + 1e-9:
            points.append((round(lat, 4), round(lon, 4)))
            lon += _STEP
        lat += _STEP
    return points


async def seed_norcal(max_calls: int = 90) -> int:
    """Sweep the NorCal grid, caching trails. Returns total trails added."""
    db = SessionLocal()
    calls = 0
    total = 0
    try:
        for lat, lon in _grid():
            if calls >= max_calls:
                break
            try:
                added = await cache_trails_near(db, lat, lon, _RADIUS_MI)
            except Exception as exc:  # noqa: BLE001 - keep sweeping if one point fails
                print(f"  ({lat}, {lon}) error: {exc}")
                continue
            calls += 1
            total += added
            print(f"  ({lat}, {lon}) +{added}  [{calls} calls, {total} new total]")
            await asyncio.sleep(0.2)
    finally:
        db.close()
    print(f"done: {calls} calls, {total} trails added")
    return total


if __name__ == "__main__":
    asyncio.run(seed_norcal())
