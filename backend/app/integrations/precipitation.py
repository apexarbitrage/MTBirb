"""Recent + near-term precipitation for a point, from Open-Meteo.

Free, keyless, and global - unlike NWS (US-only), so the trail-surface ("tacky"/mud) rating works
worldwide even where the hourly ride-time forecast can't. Uses the forecast endpoint's `past_days`
window so we get the rain that has already fallen (what actually sets the dirt) plus a little
forecast ahead. Returns tz-aware UTC hourly times paired with precipitation in mm.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoPrecip:
    source = "open-meteo"

    async def recent(
        self, lat: float, lon: float, past_days: int = 2, forecast_days: int = 1
    ) -> dict:
        """Hourly precipitation (mm) spanning the last `past_days` and next `forecast_days`.

        Returns {"times": [aware UTC datetime, ...], "precip_mm": [float, ...]}."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                OPEN_METEO_FORECAST_URL,
                params={
                    "latitude": f"{lat:.4f}",
                    "longitude": f"{lon:.4f}",
                    "hourly": "precipitation",
                    "past_days": past_days,
                    "forecast_days": forecast_days,
                    "timezone": "GMT",
                },
            )
            resp.raise_for_status()
            hourly = resp.json()["hourly"]
        times = [
            datetime.fromisoformat(t).replace(tzinfo=timezone.utc) for t in hourly["time"]
        ]
        precip = [float(p) if p is not None else 0.0 for p in hourly["precipitation"]]
        return {"times": times, "precip_mm": precip}
