"""Hermetic tests for the trail-surface (tacky/mud) model (no network, no database)."""

from datetime import UTC, datetime, timedelta

from app.services.trail_conditions import _decayed_load, assess_surface

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


def test_recent_rain_weighs_more_than_old() -> None:
    recent = _decayed_load(*_series({-3: 5.0}), now=NOW)
    old = _decayed_load(*_series({-40: 5.0}), now=NOW)
    assert recent > old
    # Future precip is excluded from what's already on the ground.
    future = _decayed_load(*_series({6: 5.0}), now=NOW)
    assert future == 0.0
