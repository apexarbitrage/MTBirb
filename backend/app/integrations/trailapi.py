"""Client for TrailAPI via RapidAPI (https://rapidapi.com/trailapi/api/trailapi).

Returns a curated catalog of nearby trails (name, trailhead point, difficulty, length,
description) - point metadata, not line geometry. Used alongside OSM, which supplies the
geometry. Requires a RapidAPI key (RAPIDAPI_KEY).
"""

import httpx

from app.config import get_settings

TRAILAPI_HOST = "trailapi-trailapi.p.rapidapi.com"
TRAILAPI_BASE_URL = f"https://{TRAILAPI_HOST}"


class TrailApiClient:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or get_settings().rapidapi_key

    def _headers(self) -> dict[str, str]:
        return {"X-RapidAPI-Key": self._api_key, "X-RapidAPI-Host": TRAILAPI_HOST}

    async def explore(self, lat: float, lon: float, radius: int = 25) -> list[dict]:
        """Trails near a point. Each record has lat/lon plus name/difficulty/length metadata."""
        async with httpx.AsyncClient(base_url=TRAILAPI_BASE_URL, headers=self._headers()) as client:
            response = await client.get(
                "/trails/explore/", params={"lat": lat, "lon": lon, "radius": radius}
            )
            response.raise_for_status()
            return response.json().get("data", [])
