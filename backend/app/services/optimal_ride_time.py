"""Scores the best time-of-day to ride a trail by blending live weather with wildlife activity.

For each upcoming daylight hour we compute two 0..100 axes and a combined score:
  - riding conditions: comfort (temperature), wind, precip chance, and daylight, from the NWS
    hourly forecast;
  - wildlife activity: a crepuscular (dawn/dusk-peaking) prior scaled by the trail's overall eBird
    score, so a birdier trail's curve sits higher.
The best window is the contiguous run of hours whose combined score is near the day's peak. This is
a first-pass model, not a calibrated probability: it doesn't yet account for past-rain mud, trail
exposure/aspect, or time-stamped eBird effort. NWS is US-only, so callers fail soft outside the US.

Pure and dependency-free (no DB, no network) so it's unit-testable; the router feeds it the hourly
forecast and the trail's wildlife score.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from app.services.solar import sun_times

# Riding-comfort temperature band (°F) and how far past it comfort decays to ~0.
_COMFORT_LO, _COMFORT_HI = 52.0, 72.0
_COMFORT_COLD_SPAN, _COMFORT_HOT_SPAN = 30.0, 33.0
# Wind (mph) at which conditions roughly halve, and the comfort floor for any factor.
_WIND_HALF = 17.0
_FACTOR_FLOOR = 0.1
# Combined score leans on conditions (you can't ride in bad weather) but rewards wildlife overlap.
_CONDITIONS_WEIGHT = 0.6
# Wildlife curve is scaled by the trail's eBird score, floored so the dawn/dusk shape stays visible
# even on a trail with little cached data.
_WILDLIFE_SCALE_FLOOR = 45
# Crepuscular peak width (hours) around sunrise/sunset, and the daytime/night activity baselines.
_CREPUSCULAR_SIGMA_H = 1.5
_DAY_ACTIVITY_BASE, _NIGHT_ACTIVITY_BASE = 0.35, 0.15
# Twilight shoulder on each side of sunrise/sunset that still counts as (dim) ridable daylight.
_TWILIGHT_SHOULDER = timedelta(minutes=60)
# An hour is "best" if its combined score is within this many points of the day's peak.
_BEST_BAND_TOLERANCE = 12
# Roll to tomorrow when fewer than this many daylight hours remain today.
_MIN_DAYLIGHT_HOURS = 3.0


@dataclass(frozen=True)
class _Hour:
    dt: datetime
    temp_f: float | None
    wind_mph: float | None
    pop_pct: float
    is_daytime: bool


# --- pure factor helpers (each returns 0..1) ---------------------------------------------------


def _comfort_factor(temp_f: float | None) -> float:
    """Riding comfort by temperature: 1.0 in the mild band, decaying in cold/heat."""
    if temp_f is None:
        return 0.6
    if _COMFORT_LO <= temp_f <= _COMFORT_HI:
        return 1.0
    if temp_f < _COMFORT_LO:
        return max(_FACTOR_FLOOR, 1.0 - (_COMFORT_LO - temp_f) / _COMFORT_COLD_SPAN)
    return max(_FACTOR_FLOOR, 1.0 - (temp_f - _COMFORT_HI) / _COMFORT_HOT_SPAN)


def _wind_factor(wind_mph: float | None) -> float:
    """1.0 in calm air, falling toward the floor as wind rises (~0.5 near _WIND_HALF)."""
    if wind_mph is None:
        return 0.8
    return max(_FACTOR_FLOOR, 1.0 - 0.5 * wind_mph / _WIND_HALF)


def _precip_factor(pop_pct: float) -> float:
    """1.0 with no rain in the forecast, down to the floor at a certain soaking."""
    return max(_FACTOR_FLOOR, 1.0 - 0.9 * max(pop_pct, 0.0) / 100.0)


def _daylight_factor(
    dt: datetime, sunrise: datetime | None, sunset: datetime | None, is_daytime: bool
) -> float:
    """1.0 in full daylight, ramping through a twilight shoulder to 0 at night."""
    if sunrise is None or sunset is None:
        return 1.0 if is_daytime else 0.0
    s = _TWILIGHT_SHOULDER
    if sunrise <= dt <= sunset:
        if dt < sunrise + s:
            return 0.5 + 0.5 * (dt - sunrise) / s
        if dt > sunset - s:
            return 0.5 + 0.5 * (sunset - dt) / s
        return 1.0
    if sunrise - s <= dt < sunrise:
        return 0.5 * (dt - (sunrise - s)) / s
    if sunset < dt <= sunset + s:
        return 0.5 * ((sunset + s) - dt) / s
    return 0.0


def _wildlife_activity_factor(
    dt: datetime, sunrise: datetime | None, sunset: datetime | None
) -> float:
    """Crepuscular activity: peaks near sunrise & sunset, with a daytime/night baseline."""
    if sunrise is None or sunset is None:
        return 0.5
    hours_from_edge = min(
        abs((dt - sunrise).total_seconds()), abs((dt - sunset).total_seconds())
    ) / 3600.0
    peak = math.exp(-(hours_from_edge**2) / (2 * _CREPUSCULAR_SIGMA_H**2))
    base = _DAY_ACTIVITY_BASE if sunrise <= dt <= sunset else _NIGHT_ACTIVITY_BASE
    return min(1.0, base + (1.0 - base) * peak)


# --- score composers ---------------------------------------------------------------------------


def conditions_score(
    temp_f: float | None,
    wind_mph: float | None,
    pop_pct: float,
    daylight: float,
    surface: float = 1.0,
) -> int:
    """Riding conditions 0..100. `surface` is the trail-surface (tacky/mud) multiplier from
    recent precipitation (see services/trail_conditions.py); 1.0 = no penalty / unknown."""
    raw = (
        _comfort_factor(temp_f)
        * _wind_factor(wind_mph)
        * _precip_factor(pop_pct)
        * daylight
        * surface
    )
    return max(0, min(100, round(100 * raw)))


def wildlife_score_hour(activity: float, trail_score: int) -> int:
    """Crepuscular shape scaled by trail birdiness (floored so the shape stays visible)."""
    ceil = max(trail_score, _WILDLIFE_SCALE_FLOOR)
    return max(0, min(100, round(activity * ceil)))


def combined_score(conditions: int, wildlife: int) -> int:
    return round(_CONDITIONS_WEIGHT * conditions + (1 - _CONDITIONS_WEIGHT) * wildlife)


def _select_best_run(scores: list[int]) -> tuple[int, int]:
    """The highest-summed contiguous run of hours within _BEST_BAND_TOLERANCE of the day's peak.

    Returns a [start, end) index range; (0, 0) when there are no scores."""
    if not scores:
        return (0, 0)
    threshold = max(scores) - _BEST_BAND_TOLERANCE
    best_start, best_end, best_sum = 0, 0, -1
    i, n = 0, len(scores)
    while i < n:
        if scores[i] >= threshold:
            j, run_sum = i, 0
            while j < n and scores[j] >= threshold:
                run_sum += scores[j]
                j += 1
            if run_sum > best_sum:
                best_start, best_end, best_sum = i, j, run_sum
            i = j
        else:
            i += 1
    return (best_start, best_end)


# --- parsing & formatting ----------------------------------------------------------------------


def _parse_wind(text: str | None) -> float | None:
    if not text:
        return None
    nums = [int(x) for x in re.findall(r"\d+", text)]
    return float(max(nums)) if nums else None


def _parse_hour(period: dict) -> _Hour | None:
    try:
        dt = datetime.fromisoformat(period["startTime"])
    except (KeyError, ValueError, TypeError):
        return None
    temp = period.get("temperature")
    temp_f = float(temp) if isinstance(temp, (int, float)) else None
    if temp_f is not None and period.get("temperatureUnit") == "C":
        temp_f = temp_f * 9 / 5 + 32
    pop = (period.get("probabilityOfPrecipitation") or {}).get("value")
    pop_pct = float(pop) if isinstance(pop, (int, float)) else 0.0
    return _Hour(
        dt=dt,
        temp_f=temp_f,
        wind_mph=_parse_wind(period.get("windSpeed")),
        pop_pct=pop_pct,
        is_daytime=bool(period.get("isDaytime")),
    )


def _fmt_hour(dt: datetime) -> str:
    return f"{dt.hour % 12 or 12} {'AM' if dt.hour < 12 else 'PM'}"


def _fmt_range(start: datetime, end: datetime) -> str:
    s_ampm, e_ampm = "AM" if start.hour < 12 else "PM", "AM" if end.hour < 12 else "PM"
    s12, e12 = start.hour % 12 or 12, end.hour % 12 or 12
    return f"{s12}–{e12} {e_ampm}" if s_ampm == e_ampm else f"{s12} {s_ampm}–{e12} {e_ampm}"


def _avg(values: list[float]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def _conjoin(parts: list[str]) -> str:
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return ", ".join(parts[:-1]) + f", and {parts[-1]}"


def _best_why(
    best: list[tuple[_Hour, int, int, int]], sunrise: datetime | None, sunset: datetime | None
) -> tuple[str, bool]:
    """A human 'why' sentence for the best window and whether dawn/dusk activity drove it."""
    avg_wind = _avg([h.wind_mph for h, *_ in best])
    avg_pop = _avg([h.pop_pct for h, *_ in best])
    avg_temp = _avg([h.temp_f for h, *_ in best])
    mid = best[len(best) // 2][0].dt

    crepuscular = False
    parts: list[str] = []
    if avg_wind is not None and avg_wind < 8:
        parts.append("calm wind")
    elif avg_wind is not None and avg_wind < 14:
        parts.append("light wind")
    if avg_pop is not None and avg_pop < 20:
        parts.append("dry trail")
    if avg_temp is not None and 50 <= avg_temp <= 74:
        parts.append("mild temps")
    if sunrise is not None and abs((mid - sunrise).total_seconds()) < 2.5 * 3600:
        parts.append("dawn wildlife activity")
        crepuscular = True
    elif sunset is not None and abs((mid - sunset).total_seconds()) < 2.5 * 3600:
        parts.append("dusk wildlife activity")
        crepuscular = True

    if len(parts) >= 2:
        why = _conjoin(parts)
        why = why[0].upper() + why[1:] + " all line up."
    elif parts:
        why = parts[0][0].upper() + parts[0][1:] + "."
    else:
        why = "The best balance of light and conditions today."
    return why, crepuscular


def _pick_target_date(now_local: datetime, lat: float, lon: float) -> date:
    """Today if enough daylight remains, else tomorrow."""
    today = now_local.date()
    _, sunset = sun_times(lat, lon, today)
    if sunset is not None and (sunset - now_local).total_seconds() >= _MIN_DAYLIGHT_HOURS * 3600:
        return today
    return (now_local + timedelta(days=1)).date()


def _empty(available: bool) -> dict:
    return {
        "available": available,
        "date": None,
        "hours": [],
        "bestWindow": None,
        "bestWindowWhy": None,
        "window": None,
    }


def _local_date(now: datetime, lon: float):
    """The trail's local calendar date, approximated from solar time (lon/15h offset). Used where
    we have no real timezone (the per-trail sort, which works globally)."""
    return (now + timedelta(hours=lon / 15.0)).date()


def current_conditions_score(
    hourly: list[dict],
    lat: float,
    lon: float,
    now: datetime | None = None,
    surface_factor: float = 1.0,
) -> int | None:
    """Regional riding-conditions score for the hour covering `now`, or None if no forecast.

    Computed once for a point (weather is regional) and reused across nearby trails by the sort."""
    now = now or datetime.now(UTC)
    parsed = [h for h in (_parse_hour(p) for p in hourly) if h is not None]
    if not parsed:
        return None
    now_local = now.astimezone(parsed[0].dt.tzinfo)
    sunrise, sunset = sun_times(lat, lon, now_local.date())
    current = next((h for h in parsed if h.dt <= now < h.dt + timedelta(hours=1)), None)
    if current is None:
        future = [h for h in parsed if h.dt >= now]
        current = future[0] if future else parsed[-1]
    daylight = _daylight_factor(current.dt, sunrise, sunset, current.is_daytime)
    return conditions_score(current.temp_f, current.wind_mph, current.pop_pct, daylight, surface_factor)


def score_now(
    now: datetime,
    lat: float,
    lon: float,
    trail_score: int,
    conditions_now: int | None,
) -> int:
    """How good *now* is for this trail: blends the regional conditions-now (already surface-scaled)
    with the trail's own crepuscular wildlife activity. Falls back to wildlife alone with no
    forecast. This is the rank used by the optimal-now sort."""
    sunrise, sunset = sun_times(lat, lon, _local_date(now, lon))
    wild = wildlife_score_hour(_wildlife_activity_factor(now, sunrise, sunset), trail_score)
    return wild if conditions_now is None else combined_score(conditions_now, wild)


def score_optimal_window(
    hourly: list[dict],
    lat: float,
    lon: float,
    trail_score: int,
    now: datetime | None = None,
    surface_factor: float = 1.0,
) -> dict:
    """Score the target day's daylight hours and pick the best window. See module docstring."""
    now = now or datetime.now(UTC)
    parsed = [h for h in (_parse_hour(p) for p in hourly) if h is not None]
    if not parsed:
        return _empty(available=False)

    now_local = now.astimezone(parsed[0].dt.tzinfo)
    target = _pick_target_date(now_local, lat, lon)
    sunrise, sunset = sun_times(lat, lon, target)
    grace = now_local - timedelta(minutes=30)

    rows: list[tuple[_Hour, int, int, int]] = []
    for h in parsed:
        if h.dt.date() != target or h.dt < grace:
            continue
        daylight = _daylight_factor(h.dt, sunrise, sunset, h.is_daytime)
        if daylight <= 0:
            continue
        cond = conditions_score(h.temp_f, h.wind_mph, h.pop_pct, daylight, surface_factor)
        wild = wildlife_score_hour(_wildlife_activity_factor(h.dt, sunrise, sunset), trail_score)
        rows.append((h, cond, wild, combined_score(cond, wild)))

    if not rows:
        return {**_empty(available=True), "date": target.isoformat()}

    b_start, b_end = _select_best_run([r[3] for r in rows])
    hours_out = [
        {
            "time": _fmt_hour(h.dt),
            "iso": h.dt.isoformat(),
            "conditions": cond,
            "wildlife": wild,
            "combined": comb,
            "tempF": round(h.temp_f) if h.temp_f is not None else None,
            "windMph": round(h.wind_mph) if h.wind_mph is not None else None,
            "popPct": round(h.pop_pct),
            "isBest": b_start <= i < b_end,
        }
        for i, (h, cond, wild, comb) in enumerate(rows)
    ]

    best = rows[b_start:b_end]
    window_start = best[0][0].dt
    window_end = best[-1][0].dt + timedelta(hours=1)
    best_window = _fmt_range(window_start, window_end)
    why, crepuscular = _best_why(best, sunrise, sunset)
    summary = "best light & activity" if crepuscular else "best riding conditions"

    return {
        "available": True,
        "date": target.isoformat(),
        "hours": hours_out,
        "bestWindow": best_window,
        "bestWindowWhy": why,
        "window": f"{best_window} · {summary}",
    }
