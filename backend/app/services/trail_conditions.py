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
