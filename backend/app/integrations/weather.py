"""Client for the US National Weather Service API (https://www.weather.gov/documentation/services-web-api).

Free, keyless, US-only. A non-US weather source will be needed before this app can support
trails outside the US - tracked as a later-phase gap, not handled here.
"""

import httpx

from app.config import get_settings

NWS_BASE_URL = "https://api.weather.gov"


class WeatherClient:
    def __init__(self, user_agent: str | None = None) -> None:
        self._user_agent = user_agent or get_settings().weather_user_agent

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self._user_agent, "Accept": "application/geo+json"}

    async def forecast(self, lat: float, lon: float) -> list[dict]:
        """Hourly-ish forecast periods for a point, as returned by NWS."""
        async with httpx.AsyncClient(base_url=NWS_BASE_URL, headers=self._headers()) as client:
            point = await client.get(f"/points/{lat:.4f},{lon:.4f}")
            point.raise_for_status()
            forecast_url = point.json()["properties"]["forecast"]

            forecast = await client.get(forecast_url)
            forecast.raise_for_status()
            return forecast.json()["properties"]["periods"]
