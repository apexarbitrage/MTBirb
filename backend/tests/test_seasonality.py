"""Hermetic tests for the month-based seasonality factor (no DB, no network)."""

from app.services.wildlife_likelihood import (
    _month_neighbours,
    _seasonal_factor,
)


def test_month_neighbours_wrap() -> None:
    assert _month_neighbours(6) == {5, 6, 7}
    assert _month_neighbours(1) == {12, 1, 2}
    assert _month_neighbours(12) == {11, 12, 1}


def test_neutral_without_phenology_or_for_residents() -> None:
    assert _seasonal_factor(set(), today_month=6) == 1.0  # no history
    assert _seasonal_factor(set(range(1, 13)), today_month=6) == 1.0  # year-round
    assert _seasonal_factor({1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}, today_month=6) == 1.0  # ~resident


def test_out_of_season_is_damped() -> None:
    winter_duck = {11, 12, 1, 2}  # present Nov-Feb
    assert _seasonal_factor(winter_duck, today_month=6) == 0.3  # June -> out of season
    # A neighbouring month still counts as in season (Oct near Nov).
    assert _seasonal_factor(winter_duck, today_month=10) > 1.0


def test_in_season_specialist_lifts_more_than_generalist() -> None:
    summer_migrant = {5, 6, 7}  # tightly seasonal, present now
    broad = {3, 4, 5, 6, 7, 8, 9}  # present now but spread out
    f_specialist = _seasonal_factor(summer_migrant, today_month=6)
    f_broad = _seasonal_factor(broad, today_month=6)
    assert f_specialist > f_broad > 1.0
    assert f_specialist <= 1.0 + 0.4  # bounded by the boost ceiling
