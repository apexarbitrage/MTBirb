"""Client for the eBird API 2.0 (https://documenter.getpostman.com/view/664302/S1ENwy59).

eBird itself withholds precise coordinates for sensitive species (owls, rare raptors, etc.)
and returns a coarse location instead. We pass that through as-is via `is_obscured` rather
than trying to recover a more precise point - see app/models/sighting.py.
"""

import httpx

from app.config import get_settings

EBIRD_BASE_URL = "https://api.ebird.org/v2"


class EBirdClient:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or get_settings().ebird_api_key

    def _headers(self) -> dict[str, str]:
        return {"X-eBirdApiToken": self._api_key}

    async def recent_observations(
        self, lat: float, lng: float, dist_km: int = 25, back_days: int = 14
    ) -> list[dict]:
        """Recent species observations within `dist_km` of a point."""
        async with httpx.AsyncClient(base_url=EBIRD_BASE_URL, headers=self._headers()) as client:
            response = await client.get(
                "/data/obs/geo/recent",
                params={"lat": lat, "lng": lng, "dist": dist_km, "back": back_days},
            )
            response.raise_for_status()
            return response.json()

    async def notable_observations(
        self, lat: float, lng: float, dist_km: int = 25, back_days: int = 14
    ) -> list[dict]:
        """Recent *notable* (locally rare/unusual) observations within `dist_km` of a point.

        This is the feed behind the product's real hook - "something unusual" - as opposed to
        the common species the plain recent feed is dominated by. `detail=full` so each record
        carries its review status (`obsValid`/`obsReviewed`) and location.
        """
        async with httpx.AsyncClient(base_url=EBIRD_BASE_URL, headers=self._headers()) as client:
            response = await client.get(
                "/data/obs/geo/recent/notable",
                params={"lat": lat, "lng": lng, "dist": dist_km, "back": back_days, "detail": "full"},
            )
            response.raise_for_status()
            return response.json()

    async def historic_observations(
        self, region_code: str, year: int, month: int, day: int, cat: str = "species"
    ) -> list[dict]:
        """Species observed in a region on a specific past date (one row per species).

        The recent feeds only reach `back`=30 days, so this per-day historic endpoint is the
        only way to sample observations across the year - the basis for the seasonality signal.
        """
        async with httpx.AsyncClient(base_url=EBIRD_BASE_URL, headers=self._headers()) as client:
            response = await client.get(
                f"/data/obs/{region_code}/historic/{year}/{month}/{day}", params={"cat": cat}
            )
            response.raise_for_status()
            return response.json()

    async def nearby_hotspots(self, lat: float, lng: float, dist_km: int = 25) -> list[dict]:
        """eBird hotspots within `dist_km` of a point."""
        async with httpx.AsyncClient(base_url=EBIRD_BASE_URL, headers=self._headers()) as client:
            response = await client.get(
                "/ref/hotspot/geo", params={"lat": lat, "lng": lng, "dist": dist_km, "fmt": "json"}
            )
            response.raise_for_status()
            return response.json()
