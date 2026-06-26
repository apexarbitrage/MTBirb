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
        """Coarse day/night forecast periods for a point, as returned by NWS."""
        return await self._periods(lat, lon, "forecast")

    async def forecast_hourly(self, lat: float, lon: float) -> list[dict]:
        """True per-hour forecast periods for a point. Each carries startTime, isDaytime,
        temperature/temperatureUnit, windSpeed ("8 mph"), probabilityOfPrecipitation.value, and
        shortForecast - the inputs the optimal-ride-time model scores hour by hour."""
        return await self._periods(lat, lon, "forecastHourly")

    async def _periods(self, lat: float, lon: float, kind: str) -> list[dict]:
        """Resolve the point's grid metadata, then return the `kind` forecast's periods.

        `kind` is the properties key on the /points response: "forecast" (day/night) or
        "forecastHourly" (per-hour)."""
        async with httpx.AsyncClient(base_url=NWS_BASE_URL, headers=self._headers()) as client:
            point = await client.get(f"/points/{lat:.4f},{lon:.4f}")
            point.raise_for_status()
            forecast_url = point.json()["properties"][kind]

            forecast = await client.get(forecast_url)
            forecast.raise_for_status()
            return forecast.json()["properties"]["periods"]
