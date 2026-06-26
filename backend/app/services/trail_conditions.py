"""Estimates trail-surface ("tacky"/mud) state from recent precipitation.

Dirt riding has a sweet spot: bone-dry is loose and dusty, soaked is mud, and the prime state is
*tacky* - moist but drained and firm, a day or two after rain. So this rating is deliberately
**non-monotonic** in rainfall. We take Open-Meteo's hourly precipitation over the last couple of
days, sum it with an exponential time decay (this morning's rain weighs far more than two days ago,
which models the dirt drying out), and check whether it's raining now. That decayed load plus the
raining-now flag map to a label (Dry/Firm/Tacky/Wet/Muddy), a 0..100 score, and a 0..1 `factor`
that the optimal-ride-time model folds into its riding-conditions axis. Pure and unit-tested; the
router fetches the precip series (see integrations/precipitation.py) and passes it in.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

# Recent-rain contribution decays as exp(-hours_ago / tau): ~18h half-life-ish, so rain a day ago
# counts for little and a fresh soaking dominates - a stand-in for the dirt drying out.
_DECAY_TAU_H = 18.0
# Precip (mm) summed across the now window that counts as "actively raining" (surface getting wet).
_RAIN_NOW_MM = 0.4

# Decayed-load (mm) band edges, and the (label, score) each maps to. Tacky is the prime state.
_DRY_MAX = 0.15
_FIRM_MAX = 0.8
_TACKY_MAX = 4.0
_WET_MAX = 12.0


def _decayed_load(times: list[datetime], precip_mm: list[float], now: datetime) -> float:
    """Time-decayed sum (mm) of rain that has already fallen, by how long ago it fell."""
    total = 0.0
    for t, mm in zip(times, precip_mm, strict=False):
        hours_ago = (now - t).total_seconds() / 3600.0
        if hours_ago < 0:  # a forecast hour - not yet on the ground
            continue
        total += mm * math.exp(-hours_ago / _DECAY_TAU_H)
    return total


def _raining_now(times: list[datetime], precip_mm: list[float], now: datetime) -> float:
    """Precip (mm) in the window around now (this hour + the next couple of forecast hours)."""
    total = 0.0
    for t, mm in zip(times, precip_mm, strict=False):
        dh = (t - now).total_seconds() / 3600.0
        if -1.0 <= dh <= 2.0:
            total += mm
    return total


def _classify(load_mm: float, raining: bool) -> tuple[str, int]:
    if raining:
        return ("Muddy", 25) if load_mm > _WET_MAX else ("Wet", 45)
    if load_mm <= _DRY_MAX:
        return ("Dry", 82)
    if load_mm <= _FIRM_MAX:
        return ("Firm", 95)
    if load_mm <= _TACKY_MAX:
        return ("Tacky", 100)
    if load_mm <= _WET_MAX:
        return ("Wet", 60)
    return ("Muddy", 35)


def assess_surface(
    times: list[datetime], precip_mm: list[float], now: datetime | None = None
) -> dict:
    """Full surface assessment: label, 0..100 score, 0..1 factor, decayed load, raining-now flag."""
    now = now or datetime.now(UTC)
    load = _decayed_load(times, precip_mm, now)
    raining = _raining_now(times, precip_mm, now) >= _RAIN_NOW_MM
    label, score = _classify(load, raining)
    return {
        "label": label,
        "score": score,
        "factor": score / 100.0,
        "loadMm": round(load, 1),
        "rainingNow": raining,
    }


# --- per-trail differentiation -----------------------------------------------------------------
# The assessment above is regional (recent rain over an area). Nearby trails diverge by how fast
# each *sheds* that water: a sun-baked, steep, rocky trail dries far quicker than a shaded, flat,
# dirt one. We turn the trail's aspect/grade/surface into a 0..1 "drainage" (0.5 = neutral) and use
# it to recover (or worsen) the regional wetness deficit per trail. The effect vanishes when the
# area is dry (no deficit), and grows the wetter it is - exactly where trails actually differ.

# Additive drainage contribution by OSM surface (title-cased as `summarize_surface` returns them).
_SURFACE_DRAINAGE = {
    "Rock": 0.30, "Paved": 0.30, "Asphalt": 0.30, "Concrete": 0.30,
    "Gravel": 0.25, "Fine Gravel": 0.25, "Pebblestone": 0.25,
    "Compacted": 0.15, "Sand": 0.10, "Unpaved": 0.05,
    "Dirt": 0.0, "Ground": 0.0, "Earth": 0.0,
    "Soil": -0.05, "Grass": -0.10, "Clay": -0.20, "Mud": -0.25,
}
# How much of the wetness deficit a fully-draining trail recovers (and a non-draining one loses).
_TERRAIN_RECOVERY = 1.0


def grade_pct(grade: str | None) -> float | None:
    """Parse a stored grade string like "10.0%" into a number, or None."""
    if not grade:
        return None
    try:
        return float(grade.rstrip("%"))
    except ValueError:
        return None


def trail_drainage(
    sun_exposure: float | None, grade: float | None, surface: str | None
) -> float:
    """How fast a trail sheds water, 0..1 (0.5 = neutral). Sunnier, steeper, rockier -> higher."""
    d = 0.5
    if sun_exposure is not None:
        d += (sun_exposure - 0.5) * 0.5  # ±0.25 from aspect
    if grade is not None:
        d += min(max(grade, 0.0) / 40.0, 1.0) * 0.25  # steeper drains
    d += _SURFACE_DRAINAGE.get(surface or "", 0.0)
    return max(0.0, min(1.0, d))


def per_trail_surface_factor(
    base_factor: float,
    sun_exposure: float | None,
    grade: float | None,
    surface: str | None,
) -> float:
    """Adjust the regional surface factor for one trail's drainage. Identity when the area is dry
    (base_factor ~1.0); spreads trails apart as it gets wetter."""
    drainage = trail_drainage(sun_exposure, grade, surface)
    deficit = 1.0 - base_factor
    factor = base_factor + deficit * (drainage - 0.5) * _TERRAIN_RECOVERY
    return max(0.05, min(1.0, factor))
