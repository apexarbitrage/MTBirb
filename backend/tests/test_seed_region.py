"""The region registry + grid math for the pre-seeder (app/seed_region.py). Pure, no network/DB."""

from app.seed_region import REGIONS, grid


def test_regions_are_well_formed():
    assert set(REGIONS) == {"norcal", "ct", "ny"}
    for r in REGIONS.values():
        assert r.lat_range[0] < r.lat_range[1]
        assert r.lon_range[0] < r.lon_range[1]
        assert r.step > 0
        assert r.ebird_regions  # at least one eBird code for seasonality


def test_grid_covers_the_bbox():
    r = REGIONS["ct"]
    pts = grid(r)
    assert len(pts) > 1
    assert pts[0] == (round(r.lat_range[0], 4), round(r.lon_range[0], 4))  # SW corner first
    for lat, lon in pts:
        assert r.lat_range[0] <= lat <= r.lat_range[1] + r.step
        assert r.lon_range[0] <= lon <= r.lon_range[1] + r.step


def test_denser_step_yields_more_cells():
    r = REGIONS["ny"]
    assert len(grid(r, step=0.3)) > len(grid(r, step=0.8))
