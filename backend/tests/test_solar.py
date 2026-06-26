"""Hermetic tests for the NOAA sunrise/sunset math (no network, no database)."""

from datetime import date, datetime, timezone

from app.services.solar import sun_times

# San Francisco.
SF = (37.7749, -122.4194)


def test_sunrise_before_sunset() -> None:
    rise, set_ = sun_times(*SF, date(2026, 6, 21))
    assert rise is not None and set_ is not None
    assert rise < set_


def test_summer_solstice_sf_within_tolerance() -> None:
    rise, set_ = sun_times(*SF, date(2026, 6, 21))
    # Almanac for San Francisco, 2026-06-21: sunrise ~05:47 PDT (12:47 UTC),
    # sunset ~20:34 PDT (03:34 UTC the next day).
    expected_rise = datetime(2026, 6, 21, 12, 47, tzinfo=timezone.utc)
    expected_set = datetime(2026, 6, 22, 3, 34, tzinfo=timezone.utc)
    assert abs((rise - expected_rise).total_seconds()) < 15 * 60
    assert abs((set_ - expected_set).total_seconds()) < 15 * 60


def test_day_longer_in_summer_than_winter() -> None:
    sr_s, ss_s = sun_times(*SF, date(2026, 6, 21))
    sr_w, ss_w = sun_times(*SF, date(2026, 12, 21))
    summer = (ss_s - sr_s).total_seconds()
    winter = (ss_w - sr_w).total_seconds()
    assert summer > winter
    assert 14 * 3600 < summer < 15.5 * 3600  # SF solstice ~14h47m
    assert 9 * 3600 < winter < 10 * 3600  # SF solstice ~9h33m


def test_equator_equinox_about_twelve_hours() -> None:
    rise, set_ = sun_times(0.0, 0.0, date(2026, 3, 20))
    day_len = (set_ - rise).total_seconds()
    assert abs(day_len - 12 * 3600) < 30 * 60
