"""Client for the OpenStreetMap Overpass API (https://overpass-api.de/).

Open trail geometry is the project's first-choice trail source (over Trailforks/Strava/
AllTrails - see CLAUDE.md). This fetches ridable ways (paths/tracks/cycleways) with their
full line geometry so trails get real coordinates instead of placeholders.
"""

import re
from collections import Counter

import httpx

from app.config import get_settings

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Ridable ways; exclude explicit bicycle=no. mtb:scale* tags, when present, give difficulty.
_QUERY_TEMPLATE = """[out:json][timeout:{timeout}];
(
  way["highway"~"^(path|cycleway|track|bridleway)$"]["bicycle"!="no"]({south},{west},{north},{east});
);
out geom;"""

# Name-filtered variant: pulls every way carrying a given name (case-insensitive regex) across a
# wide bbox, so a trail split into many OSM ways can be reassembled. footway is included here
# (named trails are sometimes tagged footway) but still excludes bicycle=no.
_NAMED_QUERY_TEMPLATE = """[out:json][timeout:{timeout}];
(
  way["highway"~"^(path|cycleway|track|bridleway|footway)$"]["bicycle"!="no"]["name"~"{name_re}",i]({south},{west},{north},{east});
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
        return await self._run(query, timeout)

    async def fetch_named_ways(
        self,
        name_re: str,
        south: float,
        west: float,
        north: float,
        east: float,
        timeout: int = 35,
    ) -> list[dict]:
        """Ridable OSM ways whose name matches `name_re` (case-insensitive) within a bbox.

        Used to reassemble a trail that OSM has split into many same-named ways across a wide
        area - the name filter keeps the response small even over a large bbox.
        """
        query = _NAMED_QUERY_TEMPLATE.format(
            timeout=timeout, name_re=name_re, south=south, west=west, north=north, east=east
        )
        return await self._run(query, timeout)

    async def _run(self, query: str, timeout: int) -> list[dict]:
        # Overpass rejects the default python-httpx User-Agent (406); send a real one.
        headers = {"User-Agent": get_settings().weather_user_agent}
        async with httpx.AsyncClient(timeout=timeout + 10, headers=headers) as client:
            response = await client.post(self._url, data={"data": query})
            response.raise_for_status()
            return parse_ways(response.json().get("elements", []))


def _scale_rank(scale: str) -> int:
    """Order `mtb:scale` values (0..6, sometimes "1+") by their leading digit."""
    match = re.match(r"(\d)", scale)
    return int(match.group(1)) if match else -1


def summarize_surface(ways: list[dict]) -> dict:
    """Aggregate a trail's OSM ways into a surface descriptor.

    Returns the most-common `surface` tag (title-cased, e.g. "Fine Gravel") and the hardest
    `mtb:scale` (technical difficulty 0..6) across the ways - both None when untagged.
    """
    surfaces: Counter[str] = Counter()
    scales: list[str] = []
    for way in ways:
        tags = way.get("tags", {})
        if tags.get("surface"):
            surfaces[tags["surface"]] += 1
        if tags.get("mtb:scale") is not None:
            scales.append(str(tags["mtb:scale"]))
    surface = surfaces.most_common(1)[0][0].replace("_", " ").title() if surfaces else None
    mtb_scale = max(scales, key=_scale_rank) if scales else None
    return {"surface": surface, "mtb_scale": mtb_scale}


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
