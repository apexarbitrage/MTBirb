"""Pre-seed whole regions so testers there get instant, fully-scored trail loads.

Browsing fills the catalog on demand, but the first visit to a fresh area pays a TrailAPI +
eBird round-trip (the "cold load"). This sweeps a grid over a region and primes both caches up
front: TrailAPI trails and eBird sightings (recent + notable) per cell, then a per-region
seasonality backfill. Cells that are already populated are skipped, so a run is resumable and
re-running is cheap (important because the TrailAPI free tier is rate-limited).

After the caches are primed it discovers OSM trails region-wide (one paced, skip-gated Overpass
call per ~16 km cell - the rows arrive with their lines) and then precomputes each trail's
wildlife score onto the row, so browsing the region's trail list does no spatial work per request.

Per-trail OSM line *assembly* is still intentionally NOT seeded (that's one Overpass call per
trail - the bulk-sweep pattern that risks getting the server IP banned); bbox *discovery* is a
couple orders of magnitude fewer calls for the same coverage, and it makes assembly unnecessary
for the trails it finds. Elevation metrics still load lazily per trail detail.

Run in the container, e.g.:
    docker compose exec app python -m app.seed_region --all
    docker compose exec app python -m app.seed_region ny --no-trails      # wildlife only (save TrailAPI quota)

The FULL seed - everything the app needs so a deploy never depends on throttled request-time
calls (run from a machine with clean Overpass access, pointed at the production DB):
    docker compose exec -e DATABASE_URL=<prod-url> app python -m app.seed_region --all \
        --enrich-lines --metrics
That adds per-trail line assembly for whatever OSM discovery didn't cover (--enrich-lines) and
bulk Open-Meteo elevation metrics for every lined trail (--metrics), on top of the default
trails + wildlife + seasonality + osm discovery + scores passes. Deploys with
OVERPASS_ENABLED=false (e.g. Render, whose egress IPs Overpass tarpits) rely on these runs for
all their OSM data.

Needs RAPIDAPI_KEY (trails) and EBIRD_API_KEY (wildlife + seasonality); a missing key skips that pass.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.integrations.elevation import OpenMeteoElevation
from app.logging_config import configure_logging
from app.models import CatalogTrail
from app.services.catalog_geometry import enrich_region
from app.services.osm_discovery import discover_grid
from app.services.trail_catalog import cache_trails_near, count_nearby, sightings_near_count
from app.services.trail_metrics import bulk_compute_metrics
from app.services.wildlife_likelihood import refresh_catalog_scores
from app.services.wildlife_sync import (
    backfill_region_history,
    sync_notable_observations,
    sync_recent_observations,
)

# eBird geo endpoints cap the radius at 50 km; TrailAPI takes miles.
_EBIRD_DIST_KM = 50
_TRAIL_RADIUS_MI = 25
# A cell already at/above these is considered seeded and skipped (matches the endpoints' gates:
# trails _MIN_CACHED=8, sightings _MIN_SIGHTINGS=20).
_TRAIL_SKIP_AT = 8
_WILDLIFE_SKIP_AT = 20
# Trails per batch when precomputing scores, to bound each spatial join's IN-list.
_SCORE_BATCH = 200


def _refresh_region_scores(db, region: "Region") -> int:
    """Precompute + store each region trail's wildlife score so the list reads it as a column
    (no per-request spatial join). Runs after wildlife + seasonality are cached, so it scores
    against the full local history. Returns the number of trails scored."""
    (lat0, lat1), (lon0, lon1) = region.lat_range, region.lon_range
    trails = list(
        db.scalars(
            select(CatalogTrail).where(
                CatalogTrail.lat >= lat0,
                CatalogTrail.lat <= lat1,
                CatalogTrail.lon >= lon0,
                CatalogTrail.lon <= lon1,
            )
        )
    )
    for i in range(0, len(trails), _SCORE_BATCH):
        refresh_catalog_scores(db, trails[i : i + _SCORE_BATCH])
    return len(trails)


@dataclass(frozen=True)
class Region:
    key: str
    label: str
    lat_range: tuple[float, float]
    lon_range: tuple[float, float]
    step: float  # grid spacing in degrees (~0.6deg ≈ 40 mi)
    ebird_regions: tuple[str, ...]  # for the seasonality backfill


REGIONS: dict[str, Region] = {
    "norcal": Region("norcal", "Northern California", (37.5, 42.0), (-124.2, -119.8), 0.6, ("US-CA",)),
    "ct": Region("ct", "Connecticut", (40.98, 42.06), (-73.73, -71.78), 0.35, ("US-CT",)),
    "ny": Region("ny", "New York", (40.48, 45.02), (-79.77, -71.85), 0.6, ("US-NY",)),
}


def grid(region: Region, step: float | None = None) -> list[tuple[float, float]]:
    """The (lat, lon) sweep points covering a region's bounding box."""
    s = step or region.step
    points: list[tuple[float, float]] = []
    lat = region.lat_range[0]
    while lat <= region.lat_range[1] + 1e-9:
        lon = region.lon_range[0]
        while lon <= region.lon_range[1] + 1e-9:
            points.append((round(lat, 4), round(lon, 4)))
            lon += s
        lat += s
    return points


async def seed_region(
    region: Region,
    *,
    year: int,
    do_trails: bool = True,
    do_wildlife: bool = True,
    do_seasonality: bool = True,
    do_osm: bool = True,
    do_lines: bool = False,
    do_metrics: bool = False,
    do_scores: bool = True,
    step: float | None = None,
    max_trail_calls: int | None = None,
    max_osm_calls: int = 400,
    max_line_calls: int = 400,
    max_metric_trails: int = 2000,
) -> None:
    settings = get_settings()
    have_trailapi = bool(settings.rapidapi_key)
    have_ebird = bool(settings.ebird_api_key)
    if do_trails and not have_trailapi:
        print("  ! RAPIDAPI_KEY not set - skipping trail seeding")
    if (do_wildlife or do_seasonality) and not have_ebird:
        print("  ! EBIRD_API_KEY not set - skipping wildlife + seasonality seeding")

    cells = grid(region, step)
    print(f"== {region.label}: {len(cells)} grid cells (step {step or region.step}°) ==")

    db = SessionLocal()
    trails_added = sightings_added = trail_calls = 0
    try:
        for i, (lat, lon) in enumerate(cells, start=1):
            tag = f"[{i}/{len(cells)}] ({lat}, {lon})"

            if do_trails and have_trailapi and (max_trail_calls is None or trail_calls < max_trail_calls):
                if count_nearby(db, lat, lon, radius_km=40) >= _TRAIL_SKIP_AT:
                    print(f"{tag} trails: already cached, skip")
                else:
                    try:
                        added = await cache_trails_near(db, lat, lon, radius=_TRAIL_RADIUS_MI)
                        trails_added += added
                        trail_calls += 1
                        print(f"{tag} trails: +{added}")
                    except Exception as exc:  # noqa: BLE001 - keep sweeping past one bad cell
                        print(f"{tag} trails: error {exc}")
                    await asyncio.sleep(0.2)

            if do_wildlife and have_ebird:
                if sightings_near_count(db, lat, lon, radius_km=15) >= _WILDLIFE_SKIP_AT:
                    print(f"{tag} wildlife: already cached, skip")
                else:
                    try:
                        recent, notable = await asyncio.gather(
                            sync_recent_observations(db, lat, lon, dist_km=_EBIRD_DIST_KM, back_days=30),
                            sync_notable_observations(db, lat, lon, dist_km=_EBIRD_DIST_KM, back_days=30),
                        )
                        sightings_added += recent + notable
                        print(f"{tag} wildlife: +{recent + notable}")
                    except Exception as exc:  # noqa: BLE001
                        print(f"{tag} wildlife: error {exc}")
                    await asyncio.sleep(0.2)

        if do_seasonality and have_ebird:
            for code in region.ebird_regions:
                try:
                    summary = await backfill_region_history(db, code, year)
                    print(f"  seasonality {code} ({year}): {summary}")
                except Exception as exc:  # noqa: BLE001
                    print(f"  seasonality {code}: error {exc}")

        # Discover OSM trails region-wide (Overpass is keyless): one paced call per ~16 km cell,
        # cells with OSM coverage skipped - so a capped run is resumable, like the trail pass.
        # Runs before the score pass so the new rows get their wildlife score in the same run.
        if do_osm:
            try:
                summary = await discover_grid(
                    db, region.lat_range, region.lon_range, max_calls=max_osm_calls
                )
                print(f"  osm discovery: {summary}")
                if summary.get("rateLimited") or summary.get("aborted"):
                    print("  ! Overpass is busy (rate-limiting/overloaded) - stopped early."
                          " Re-run later (or set OVERPASS_URL to a mirror);"
                          " the sweep resumes where it left off.")
            except Exception as exc:  # noqa: BLE001
                print(f"  osm discovery: error {exc}")

        # Per-trail OSM line assembly for whatever discovery couldn't cover (TrailAPI rows whose
        # names matched nothing - typos, unbounded trails). One Overpass call per trail, so this
        # is opt-in (--enrich-lines) and meant for machines with clean Overpass access; deploys
        # with OVERPASS_ENABLED=false rely entirely on runs like this for their lines.
        if do_lines:
            try:
                summary = await enrich_region(
                    db, region.lat_range, region.lon_range, max_calls=max_line_calls
                )
                print(f"  line assembly: {summary}")
            except Exception as exc:  # noqa: BLE001
                print(f"  line assembly: error {exc}")

        # Bulk Open-Meteo elevation metrics for every lined trail (keyless, works from anywhere),
        # so no trail detail ever needs the coarse pass at request time - the per-detail USGS
        # refinement still upgrades trails on first open.
        if do_metrics:
            try:
                summary = await bulk_compute_metrics(
                    db, region.lat_range, region.lon_range, OpenMeteoElevation(),
                    max_trails=max_metric_trails,
                )
                print(f"  metrics: {summary}")
            except Exception as exc:  # noqa: BLE001
                print(f"  metrics: error {exc}")

        # Precompute the wildlife score onto each row last, once the full local cache is in place,
        # so browsing the region's trail list does zero spatial work per request.
        if do_scores:
            try:
                scored = _refresh_region_scores(db, region)
                print(f"  scores: refreshed {scored} trails")
            except Exception as exc:  # noqa: BLE001
                print(f"  scores: error {exc}")
    finally:
        db.close()
    print(f"== {region.label} done: +{trails_added} trails, +{sightings_added} sightings "
          f"({trail_calls} TrailAPI calls) ==\n")


async def _run(args: argparse.Namespace) -> None:
    keys = list(REGIONS) if args.all else args.regions
    year = args.year or (datetime.now(UTC).year - 1)  # last complete year for full-season history
    for key in keys:
        region = REGIONS.get(key)
        if region is None:
            print(f"unknown region '{key}' (known: {', '.join(REGIONS)})")
            continue
        await seed_region(
            region,
            year=year,
            do_trails=not args.no_trails,
            do_wildlife=not args.no_wildlife,
            do_seasonality=not args.no_seasonality,
            do_osm=not args.no_osm,
            do_lines=args.enrich_lines,
            do_metrics=args.metrics,
            do_scores=not args.no_scores,
            step=args.step,
            max_trail_calls=args.max_trail_calls,
            max_osm_calls=args.max_osm_calls,
            max_line_calls=args.max_line_calls,
            max_metric_trails=args.max_metric_trails,
        )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Pre-seed regions (trails + wildlife + seasonality).")
    p.add_argument("regions", nargs="*", help=f"region keys: {', '.join(REGIONS)}")
    p.add_argument("--all", action="store_true", help="seed every known region")
    p.add_argument("--year", type=int, help="seasonality backfill year (default: last year)")
    p.add_argument("--step", type=float, help="override grid spacing in degrees")
    p.add_argument("--max-trail-calls", type=int, help="cap TrailAPI calls per region (quota guard)")
    p.add_argument("--no-trails", action="store_true", help="skip TrailAPI trail seeding")
    p.add_argument("--no-wildlife", action="store_true", help="skip eBird sighting seeding")
    p.add_argument("--no-seasonality", action="store_true", help="skip the seasonality backfill")
    p.add_argument("--no-osm", action="store_true", help="skip OSM trail discovery")
    p.add_argument("--max-osm-calls", type=int, default=400,
                   help="cap Overpass discovery calls per region (default 400; re-runs resume)")
    p.add_argument("--enrich-lines", action="store_true",
                   help="assemble OSM lines for still-line-less trails (1 Overpass call/trail)")
    p.add_argument("--max-line-calls", type=int, default=400,
                   help="cap per-trail line-assembly Overpass calls per region (default 400)")
    p.add_argument("--metrics", action="store_true",
                   help="bulk-compute Open-Meteo elevation metrics for lined trails")
    p.add_argument("--max-metric-trails", type=int, default=2000,
                   help="cap trails per region for the metrics pass (default 2000)")
    p.add_argument("--no-scores", action="store_true", help="skip precomputing the wildlife scores")
    return p


def main() -> None:
    # The services log through `logging` (endpoint in use, Overpass cooldowns, per-cell
    # failures); without this only WARNING+ reaches the console and runs are undiagnosable.
    configure_logging()
    p = build_parser()
    args = p.parse_args()
    if not args.regions and not args.all:
        p.error("name at least one region, or pass --all")
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
