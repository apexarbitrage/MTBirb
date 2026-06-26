"""Hermetic tests for the optimal-ride-time model (no network, no database)."""

from datetime import UTC, date, datetime, timedelta, timezone

from app.services.optimal_ride_time import (
    _comfort_factor,
    _daylight_factor,
    _precip_factor,
    _select_best_run,
    _wildlife_activity_factor,
    _wind_factor,
    combined_score,
    conditions_score,
    score_now,
    score_optimal_window,
    wildlife_score_hour,
)

PDT = timezone(timedelta(hours=-7))
SF_LAT, SF_LON = 37.7749, -122.4194
SUNRISE = datetime(2026, 6, 21, 6, 0, tzinfo=PDT)
SUNSET = datetime(2026, 6, 21, 20, 0, tzinfo=PDT)


def _at(hour: int) -> datetime:
    return datetime(2026, 6, 21, hour, 0, tzinfo=PDT)


def _hourly(temp: int = 60, wind: int = 5, pop: int = 0) -> list[dict]:
    """A full synthetic NWS hourly day for 2026-06-21 in SF's zone."""
    return [
        {
            "startTime": _at(h).isoformat(),
            "isDaytime": 6 <= h < 20,
            "temperature": temp,
            "temperatureUnit": "F",
            "windSpeed": f"{wind} mph",
            "probabilityOfPrecipitation": {"value": pop},
            "shortForecast": "Sunny",
        }
        for h in range(24)
    ]


# --- factor helpers ----------------------------------------------------------------------------


def test_comfort_factor_band_and_decay() -> None:
    assert _comfort_factor(62) == 1.0
    assert _comfort_factor(30) < _comfort_factor(45) < 1.0
    assert _comfort_factor(95) < _comfort_factor(80) < 1.0
    assert all(0.0 <= _comfort_factor(t) <= 1.0 for t in range(-20, 121, 5))
    assert _comfort_factor(None) == 0.6


def test_wind_and_precip_monotonic() -> None:
    assert _wind_factor(0) == 1.0
    assert _wind_factor(30) < _wind_factor(10) < _wind_factor(0)
    assert _precip_factor(0) == 1.0
    assert _precip_factor(100) < _precip_factor(50) < _precip_factor(0)
    assert _precip_factor(100) >= 0.1


def test_daylight_factor() -> None:
    assert _daylight_factor(_at(13), SUNRISE, SUNSET, True) == 1.0
    assert _daylight_factor(_at(2), SUNRISE, SUNSET, False) == 0.0
    assert _daylight_factor(SUNRISE, SUNRISE, SUNSET, True) == 0.5  # twilight edge
    # No sun data -> fall back to NWS isDaytime.
    assert _daylight_factor(_at(13), None, None, True) == 1.0
    assert _daylight_factor(_at(2), None, None, False) == 0.0


def test_wildlife_activity_is_crepuscular() -> None:
    dawn = _wildlife_activity_factor(_at(6), SUNRISE, SUNSET)
    midday = _wildlife_activity_factor(_at(13), SUNRISE, SUNSET)
    dusk = _wildlife_activity_factor(_at(20), SUNRISE, SUNSET)
    night = _wildlife_activity_factor(_at(2), SUNRISE, SUNSET)
    assert dawn > 0.9 and dusk > 0.9
    assert dawn > midday and dusk > midday
    assert midday > night


# --- score composers ---------------------------------------------------------------------------


def test_conditions_score_rewards_clear_calm() -> None:
    clear = conditions_score(62, 3, 0, 1.0)
    rainy = conditions_score(62, 25, 90, 1.0)
    assert clear > rainy
    assert 0 <= rainy <= clear <= 100
    assert clear >= 90


def test_conditions_score_surface_multiplier() -> None:
    # A muddy surface (low factor) drags conditions down from an otherwise perfect hour.
    assert conditions_score(62, 5, 0, 1.0, surface=0.3) < conditions_score(62, 5, 0, 1.0, surface=1.0)


def test_score_now_ranks_birdier_trail_higher() -> None:
    now = datetime(2026, 6, 21, 13, 30, tzinfo=UTC)  # ~6:30 AM PDT, near SF sunrise
    birdy = score_now(now, SF_LAT, SF_LON, 85, conditions_now=80)
    quiet = score_now(now, SF_LAT, SF_LON, 30, conditions_now=80)
    assert birdy > quiet


def test_score_now_lower_conditions_lower_rank() -> None:
    now = datetime(2026, 6, 21, 13, 30, tzinfo=UTC)
    good = score_now(now, SF_LAT, SF_LON, 70, conditions_now=80)
    muddy = score_now(now, SF_LAT, SF_LON, 70, conditions_now=30)
    assert good > muddy


def test_score_now_without_forecast_uses_wildlife() -> None:
    now = datetime(2026, 6, 21, 13, 30, tzinfo=UTC)
    assert score_now(now, SF_LAT, SF_LON, 80, conditions_now=None) > 0


def test_wildlife_score_scales_with_trail_score() -> None:
    # Same peak activity, birdier trail reads higher; floor keeps the shape visible at score 0.
    assert wildlife_score_hour(1.0, 90) > wildlife_score_hour(1.0, 50)
    assert wildlife_score_hour(1.0, 0) >= 40


def test_combined_leans_on_conditions() -> None:
    assert combined_score(100, 0) > combined_score(0, 100)


def test_select_best_run() -> None:
    assert _select_best_run([]) == (0, 0)
    assert _select_best_run([50]) == (0, 1)
    # Peak 95, threshold 83 -> only the 90,95 pair qualifies.
    assert _select_best_run([10, 20, 90, 95, 40, 30]) == (2, 4)
    # Two qualifying runs -> the higher-summed one wins.
    assert _select_best_run([80, 82, 40, 90]) == (0, 2)


# --- end-to-end window scoring -----------------------------------------------------------------


def test_score_window_clear_day_picks_crepuscular() -> None:
    # All-day mild & calm: the wildlife overlap pulls the best window to a dawn/dusk period.
    now = _at(3).astimezone(UTC)
    res = score_optimal_window(_hourly(), SF_LAT, SF_LON, trail_score=80, now=now)
    assert res["available"] is True
    assert res["date"] == "2026-06-21"
    assert res["hours"] and res["bestWindow"]
    best_hours = [h for h in res["hours"] if h["isBest"]]
    assert best_hours
    # Night hours are excluded from the curve.
    assert "2 AM" not in [h["time"] for h in res["hours"]]
    # Every best hour is within tolerance of the day's peak combined score.
    peak = max(h["combined"] for h in res["hours"])
    assert all(h["combined"] >= peak - 12 for h in best_hours)
    # The wildlife overlap pulls the window to a crepuscular (dawn or dusk) period.
    why = res["bestWindowWhy"].lower()
    assert "dawn" in why or "dusk" in why


def test_score_window_rained_out_morning_moves_later() -> None:
    # Rain & wind 6-11a, clear after: conditions push the best window past the morning washout.
    hours = _hourly()
    for h in hours:
        local_hour = datetime.fromisoformat(h["startTime"]).hour
        if 6 <= local_hour < 11:
            h["probabilityOfPrecipitation"]["value"] = 90
            h["windSpeed"] = "26 mph"
    now = _at(3).astimezone(UTC)
    res = score_optimal_window(hours, SF_LAT, SF_LON, trail_score=80, now=now)
    best_hours = [h for h in res["hours"] if h["isBest"]]
    assert best_hours
    # No washed-out morning hour should be marked best.
    washed = {"6 AM", "7 AM", "8 AM", "9 AM", "10 AM"}
    assert not (washed & {h["time"] for h in best_hours})


def test_score_window_empty_forecast_unavailable() -> None:
    res = score_optimal_window([], SF_LAT, SF_LON, trail_score=50)
    assert res["available"] is False
    assert res["hours"] == [] and res["bestWindow"] is None


def test_score_window_rolls_to_tomorrow_after_dark() -> None:
    # Asked at 11pm local: today's daylight is gone, so target tomorrow.
    today = _hourly()
    tomorrow = [
        {**h, "startTime": (datetime.fromisoformat(h["startTime"]) + timedelta(days=1)).isoformat()}
        for h in _hourly()
    ]
    now = datetime(2026, 6, 21, 23, 0, tzinfo=PDT).astimezone(UTC)
    res = score_optimal_window(today + tomorrow, SF_LAT, SF_LON, trail_score=70, now=now)
    assert res["available"] is True
    assert res["date"] == date(2026, 6, 22).isoformat()
