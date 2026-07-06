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
TOMTOM_TILE_BASE = "https://api.tomtom.com/map/1/tile"
# Selectable raster layers -> (TomTom layer path, file extension, media type). `basic` is the full
# road map (nav screen); `sat` is satellite imagery + `hybrid` its transparent road/label overlay,
# stacked for the terrain map on Trail detail.
TILE_LAYERS: dict[str, tuple[str, str, str]] = {
    "basic": ("basic", "png", "image/png"),
    "sat": ("sat", "jpg", "image/jpeg"),
    "hybrid": ("hybrid", "png", "image/png"),
}


class TomTomNotConfigured(RuntimeError):
    """Raised when TOMTOM_API_KEY isn't set - callers turn this into a 503."""


# One process-wide pooled client so the two routing calls and the many tile fetches reuse
# keep-alive connections to TomTom instead of re-handshaking TLS on every request (the map alone
# pulls a screen's worth of tiles). Created lazily inside the event loop; closed on app shutdown
# via aclose_shared_client() (see app/main.py). httpx.AsyncClient is safe for concurrent use.
_shared_client: httpx.AsyncClient | None = None


def _client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=40),
        )
    return _shared_client


async def aclose_shared_client() -> None:
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        await _shared_client.aclose()
    _shared_client = None


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

        resp = await _client().get(f"{TOMTOM_ROUTING_URL}/{locations}/json", params=params)
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

    async def fetch_tile(self, z: int, x: int, y: int, layer: str = "basic") -> tuple[bytes, str]:
        """A single raster map tile from TomTom, fetched server-side so the key stays in `.env`
        and never reaches the browser (the frontend's Leaflet layer hits our proxy).

        `layer` picks the style (`basic`/`sat`/`hybrid`); returns (tile bytes, media type).
        """
        if not self._key:
            raise TomTomNotConfigured("TOMTOM_API_KEY not set")
        path, ext, media_type = TILE_LAYERS.get(layer, TILE_LAYERS["basic"])
        url = f"{TOMTOM_TILE_BASE}/{path}/main/{z}/{x}/{y}.{ext}"
        resp = await _client().get(url, params={"key": self._key})
        resp.raise_for_status()
        return resp.content, media_type
