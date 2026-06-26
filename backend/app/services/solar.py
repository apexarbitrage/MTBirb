"""Sunrise/sunset for a point and date, used by the optimal-ride-time model.

A small, dependency-free implementation of the NOAA "Almanac for Computers" sunrise equation -
accurate to a minute or two, which is plenty for a dawn/dusk activity curve and a daylight mask.
Returns timezone-aware UTC datetimes; the caller compares them against tz-aware forecast hours, so
the absolute instants line up regardless of the trail's local zone. Returns None for the rare
polar day/night case (sun never crosses the horizon), where the caller falls back to NWS isDaytime.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

# Official sunrise/sunset zenith (90°50'): geometric horizon plus refraction + the sun's radius.
_ZENITH = 90.833


def _solar_event_utc_hours(lat: float, lon: float, on_date: date, rising: bool) -> float | None:
    """Hours (UTC) of sunrise (rising=True) or sunset on `on_date`, or None if it doesn't occur."""
    day_of_year = on_date.toordinal() - date(on_date.year, 1, 1).toordinal() + 1
    lng_hour = lon / 15.0

    # Approximate time of the event, then the sun's mean anomaly at that time.
    t = day_of_year + ((6 if rising else 18) - lng_hour) / 24.0
    mean_anomaly = 0.9856 * t - 3.289

    # Sun's true longitude.
    true_long = (
        mean_anomaly
        + 1.916 * math.sin(math.radians(mean_anomaly))
        + 0.020 * math.sin(math.radians(2 * mean_anomaly))
        + 282.634
    ) % 360.0

    # Right ascension, put in the same quadrant as the true longitude.
    right_asc = math.degrees(math.atan(0.91764 * math.tan(math.radians(true_long)))) % 360.0
    long_quadrant = (true_long // 90) * 90
    ra_quadrant = (right_asc // 90) * 90
    right_asc = (right_asc + (long_quadrant - ra_quadrant)) / 15.0  # degrees -> hours

    # Sun's declination, then the local hour angle.
    sin_dec = 0.39782 * math.sin(math.radians(true_long))
    cos_dec = math.cos(math.asin(sin_dec))
    cos_h = (math.cos(math.radians(_ZENITH)) - sin_dec * math.sin(math.radians(lat))) / (
        cos_dec * math.cos(math.radians(lat))
    )
    if cos_h > 1 or cos_h < -1:
        return None  # sun never rises / never sets at this lat on this date

    h = (360 - math.degrees(math.acos(cos_h))) if rising else math.degrees(math.acos(cos_h))
    h /= 15.0  # degrees -> hours

    local_mean_time = h + right_asc - 0.06571 * t - 6.622
    return (local_mean_time - lng_hour) % 24.0


def sun_times(lat: float, lon: float, on_date: date) -> tuple[datetime | None, datetime | None]:
    """(sunrise, sunset) as tz-aware UTC datetimes for the point on `on_date`; None when absent."""
    midnight = datetime(on_date.year, on_date.month, on_date.day, tzinfo=timezone.utc)
    # The events occur near local solar noon; for western longitudes a UTC hour-of-day can wrap
    # onto the next UTC day, so anchor each event to the day offset nearest local noon (else sunset
    # would land before sunrise in UTC).
    local_noon_utc = midnight + timedelta(hours=12.0 - lon / 15.0)

    def _anchor(event_hours: float | None) -> datetime | None:
        if event_hours is None:
            return None
        base = midnight + timedelta(hours=event_hours)
        return min(
            (base + timedelta(days=off) for off in (-1, 0, 1)),
            key=lambda dt: abs((dt - local_noon_utc).total_seconds()),
        )

    return (
        _anchor(_solar_event_utc_hours(lat, lon, on_date, rising=True)),
        _anchor(_solar_event_utc_hours(lat, lon, on_date, rising=False)),
    )
