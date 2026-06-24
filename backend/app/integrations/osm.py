"""Client for the OpenStreetMap Overpass API (https://overpass-api.de/).

Open trail geometry is the project's first-choice trail source (over Trailforks/Strava/
AllTrails - see CLAUDE.md). This fetches ridable ways (paths/tracks/cycleways) with their
full line geometry so trails get real coordinates instead of placeholders.
"""

import httpx

from app.config import get_settings

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Ridable ways; exclude explicit bicycle=no. mtb:scale* tags, when present, give difficulty.
_QUERY_TEMPLATE = """[out:json][timeout:{timeout}];
(
  way["highway"~"^(path|cycleway|track|bridleway)$"]["bicycle"!="no"]({south},{west},{north},{east});
);
out geom;"""


class OverpassClient:
    def __init__(self, url: str = OVERPASS_URL) -> None:
        self._url = url

    async def fetch_ways(
        self, south: float, west: float, north: float, east: float, timeout: int = 25
    ) -> list[dict]:
        """Ridable OSM ways in a bbox, each with name, tags, and (lon, lat) geometry points."""
        query = _QUERY_TEMPLATE.format(
            timeout=timeout, south=south, west=west, north=north, east=east
        )
        # Overpass rejects the default python-httpx User-Agent (406); send a real one.
        headers = {"User-Agent": get_settings().weather_user_agent}
        async with httpx.AsyncClient(timeout=timeout + 10, headers=headers) as client:
            response = await client.post(self._url, data={"data": query})
            response.raise_for_status()
            return parse_ways(response.json().get("elements", []))


def parse_ways(elements: list[dict]) -> list[dict]:
    """Keep way elements that carry usable line geometry; flatten to name/tags/points."""
    ways = []
    for el in elements:
        geometry = el.get("geometry")
        if el.get("type") != "way" or not geometry or len(geometry) < 2:
            continue
        tags = el.get("tags", {})
        ways.append(
            {
                "osm_id": el["id"],
                "name": tags.get("name"),
                "tags": tags,
                "points": [(p["lon"], p["lat"]) for p in geometry],
            }
        )
    return ways
