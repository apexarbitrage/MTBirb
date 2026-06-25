"""Hermetic tests for the DEM-derived terrain metrics math (no network, no database)."""

import math

from app.services.trail_metrics import compute, resample


def test_resample_even_spacing_and_length() -> None:
    # A straight ~1km east-west line at the equator: 0.009deg lon ~= 1001m.
    line = [[0.0, 0.0], [0.009, 0.0]]
    samples, total_m = resample(line, 5)
    assert len(samples) == 5
    assert math.isclose(total_m, 1001.0, rel_tol=0.02)
    # Samples are (lat, lon), evenly spaced from start to end.
    lons = [lon for _, lon in samples]
    assert lons[0] == 0.0
    assert math.isclose(lons[-1], 0.009, rel_tol=1e-9)
    gaps = [lons[i + 1] - lons[i] for i in range(len(lons) - 1)]
    assert all(math.isclose(g, gaps[0], rel_tol=1e-6) for g in gaps)


def test_resample_handles_degenerate_line() -> None:
    samples, total_m = resample([[1.0, 2.0], [1.0, 2.0]], 4)
    assert total_m == 0.0
    assert samples == [(2.0, 1.0)] * 4  # (lat, lon)


def test_compute_climb_and_descent() -> None:
    # Up 100m then back down 100m over a 2000m line.
    elevations = [0.0, 50.0, 100.0, 50.0, 0.0]
    m = compute(elevations, 2000.0)
    # ~328 ft each way (100m), within rounding.
    assert abs(m["ascent_ft"] - 328) <= 1
    assert abs(m["descent_ft"] - 328) <= 1
    assert math.isclose(m["metric_length_mi"], 2000 / 1609.344, abs_tol=0.01)


def test_compute_noise_floor_ignores_jitter() -> None:
    # Sub-metre wiggles must not accumulate into phantom climb.
    elevations = [10.0, 10.4, 10.1, 10.5, 10.2]
    m = compute(elevations, 1000.0)
    assert m["ascent_ft"] == 0
    assert m["descent_ft"] == 0
    assert m["avg_up_grade"] == "0.0%"


def test_compute_grade_and_profile() -> None:
    # Pure 10% climb: rises 100m over 1000m horizontal.
    elevations = [0.0, 25.0, 50.0, 75.0, 100.0]
    m = compute(elevations, 1000.0)
    assert m["avg_up_grade"] == "10.0%"
    assert m["avg_down_grade"] == "0.0%"
    # Profile is normalized 0..1 across the samples.
    assert m["elevation_profile"][0] == 0.0
    assert m["elevation_profile"][-1] == 1.0
    assert m["ride_time_min"] > 0
    assert 1.0 <= m["effort"] <= 10.0
