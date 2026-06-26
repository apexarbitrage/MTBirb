"""Hermetic tests for the trail-surface (tacky/mud) model (no network, no database)."""

from datetime import UTC, datetime, timedelta

from app.services.trail_conditions import (
    _decayed_load,
    assess_surface,
    grade_pct,
    per_trail_surface_factor,
    trail_drainage,
)

NOW = datetime(2026, 6, 26, 18, 0, tzinfo=UTC)


def _series(hours_to_mm: dict[int, float]) -> tuple[list[datetime], list[float]]:
    """Build (times, precip_mm) over a window; keys are hours relative to NOW (negative = past)."""
    times, precip = [], []
    for h in range(-48, 25):
        times.append(NOW + timedelta(hours=h))
        precip.append(hours_to_mm.get(h, 0.0))
    return times, precip


def test_no_rain_is_dry() -> None:
    a = assess_surface(*_series({}), now=NOW)
    assert a["label"] == "Dry"
    assert a["factor"] == a["score"] / 100.0
    assert not a["rainingNow"]


def test_raining_now_is_wet_or_muddy_and_low() -> None:
    a = assess_surface(*_series({0: 1.5, -1: 1.0}), now=NOW)
    assert a["rainingNow"]
    assert a["label"] in {"Wet", "Muddy"}
    assert a["score"] <= 45


def test_light_rain_yesterday_is_tacky() -> None:
    # A modest shower ~18-24h ago, dry since: the prime tacky window.
    a = assess_surface(*_series({-20: 4.0, -22: 3.0}), now=NOW)
    assert a["label"] == "Tacky"
    assert a["score"] == 100
    assert not a["rainingNow"]


def test_big_storm_hours_ago_is_wet_or_muddy() -> None:
    a = assess_surface(*_series({-3: 12.0, -4: 10.0, -5: 8.0}), now=NOW)
    assert a["label"] in {"Wet", "Muddy"}
    assert a["score"] <= 60


def test_dry_scores_higher_than_muddy() -> None:
    dry = assess_surface(*_series({}), now=NOW)
    muddy = assess_surface(*_series({-2: 15.0, -3: 14.0, -4: 12.0}), now=NOW)
    assert dry["score"] > muddy["score"]


def test_grade_pct_parses() -> None:
    assert grade_pct("10.0%") == 10.0
    assert grade_pct("0%") == 0.0
    assert grade_pct(None) is None
    assert grade_pct("steep") is None


def test_trail_drainage_ordering() -> None:
    # Sunnier, steeper, rockier all drain faster.
    assert trail_drainage(0.9, 12.0, "Rock") > trail_drainage(0.1, 12.0, "Rock")
    assert trail_drainage(0.5, 20.0, "Dirt") > trail_drainage(0.5, 2.0, "Dirt")
    assert trail_drainage(0.5, 8.0, "Rock") > trail_drainage(0.5, 8.0, "Grass")
    assert 0.0 <= trail_drainage(0.0, 0.0, "Mud") <= 1.0


def test_per_trail_factor_identity_when_dry() -> None:
    # A dry area (base 1.0) has no deficit, so terrain can't change anything.
    assert per_trail_surface_factor(1.0, 0.1, 2.0, "Mud") == 1.0
    assert per_trail_surface_factor(1.0, 0.9, 30.0, "Rock") == 1.0


def test_per_trail_factor_spreads_when_wet() -> None:
    # In a wet area, a sun-baked steep rocky trail beats a shaded flat dirt one nearby.
    dry_trail = per_trail_surface_factor(0.45, sun_exposure=0.9, grade=14.0, surface="Rock")
    wet_trail = per_trail_surface_factor(0.45, sun_exposure=0.1, grade=2.0, surface="Grass")
    assert dry_trail > 0.45 > wet_trail
    assert dry_trail > wet_trail
    assert 0.05 <= wet_trail and dry_trail <= 1.0


def test_recent_rain_weighs_more_than_old() -> None:
    recent = _decayed_load(*_series({-3: 5.0}), now=NOW)
    old = _decayed_load(*_series({-40: 5.0}), now=NOW)
    assert recent > old
    # Future precip is excluded from what's already on the ground.
    future = _decayed_load(*_series({6: 5.0}), now=NOW)
    assert future == 0.0
