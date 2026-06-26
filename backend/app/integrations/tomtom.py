"""Client for the TomTom Routing API (https://developer.tomtom.com/routing-api).

Powers the "fun drive" to the trailhead. TomTom's `routeType=thrilling` (with `windingness` and
`hilliness`) returns a deliberately twisty, hilly route - exactly the curvature-maximising drive the
product pitches - on a free tier, so we don't have to build a curvature scorer over OSM. Called
**server-side only**: the key stays in `backend/.env` (read via settings) and never reaches the
browser. The endpoint returns 503 when the key is unset (see routers/catalog.py), like BirdNET.
"""

from __future__ import annotations

import httpx

from app.config import get_settings

TOMTOM_ROUTING_URL = "https://api.tomtom.com/routing/1/calculateRoute"
TOMTOM_TILE_URL = "https://api.tomtom.com/map/1/tile/basic/main"


class TomTomNotConfigured(RuntimeError):
    """Raised when TOMTOM_API_KEY isn't set - callers turn this into a 503."""


class TomTomClient:
    def __init__(self, api_key: str | None = None) -> None:
        self._key = api_key if api_key is not None else get_settings().tomtom_api_key

    async def calculate_route(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        route_type: str = "thrilling",
        windingness: str = "high",
        hilliness: str = "high",
    ) -> dict:
        """Driving route from start to end (each a (lat, lon) pair).

        Returns {distance_m, travel_time_s, points: [[lon, lat], ...]}. `windingness`/`hilliness`
        only apply to the thrilling route type.
        """
        if not self._key:
            raise TomTomNotConfigured("TOMTOM_API_KEY not set")
        (slat, slon), (dlat, dlon) = start, end
        locations = f"{slat:.6f},{slon:.6f}:{dlat:.6f},{dlon:.6f}"
        params = {
            "key": self._key,
            "routeType": route_type,
            "travelMode": "car",
            "traffic": "true",
        }
        if route_type == "thrilling":
            params.update(windingness=windingness, hilliness=hilliness)

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(f"{TOMTOM_ROUTING_URL}/{locations}/json", params=params)
            resp.raise_for_status()
            data = resp.json()

        route = data["routes"][0]
        summary = route["summary"]
        points = [
            [p["longitude"], p["latitude"]] for leg in route["legs"] for p in leg["points"]
        ]
        return {
            "distance_m": summary["lengthInMeters"],
            "travel_time_s": summary["travelTimeInSeconds"],
            "points": points,
        }

    async def fetch_tile(self, z: int, x: int, y: int) -> bytes:
        """A single raster map tile (PNG) from TomTom, fetched server-side so the key stays in
        `.env` and never reaches the browser (the frontend's Leaflet layer hits our proxy)."""
        if not self._key:
            raise TomTomNotConfigured("TOMTOM_API_KEY not set")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{TOMTOM_TILE_URL}/{z}/{x}/{y}.png", params={"key": self._key})
            resp.raise_for_status()
            return resp.content
