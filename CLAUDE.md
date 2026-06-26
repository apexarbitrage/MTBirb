# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

MTBirb is a web-based mobile app (installable PWA) that helps mountain bikers pick trails
based on both riding criteria (difficulty, features, condition, busyness) and wildlife/birding
potential (highest chance of a specific species, of any wildlife encounter, or of something
unusual). It also surfaces weather-based "best time to ride," and will eventually route
drivers to the trailhead with a "fun drive" (twisty-road-maximizing) option, export the chosen
route to a GPS device, and offer in-trail bird ID.

This is an early-stage scaffold, not a feature-complete app. Most third-party integrations are
intentionally stubbed or absent - see "Integration phasing" below before assuming a data source
is wired up.

## Commands

### Backend (`backend/`, Python 3.11+ / FastAPI)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

- Run the API: `uvicorn app.main:app --reload` (serves on :8000)
- Run all tests: `pytest`
- Run a single test: `pytest tests/test_health.py::test_health`
- Lint: `ruff check .`
- Apply migrations: `alembic upgrade head`
- Create a migration: `alembic revision -m "description"` (write the `upgrade`/`downgrade`
  bodies by hand - see the note on GeoAlchemy2 indexes below before adding one for a geometry
  column)

The backend needs a running Postgres+PostGIS (`docker compose up -d` from the repo root, or a
local install - see `README.md`). `DATABASE_URL` / `EBIRD_API_KEY` / `WEATHER_USER_AGENT` are
read from `backend/.env` (copy from `.env.example`).

### Frontend (`frontend/`, React + Vite PWA)

```bash
cd frontend
npm install
```

- Dev server: `npm run dev` (serves on :5173, proxies `/api/*` to the backend on :8000)
- Build: `npm run build` (runs `tsc -b` then `vite build`)
- Lint: `npm run lint`

## Architecture

Monorepo with two independently-run services: `backend/` (FastAPI + PostgreSQL/PostGIS) and
`frontend/` (React/Vite PWA). They're not deployed as one process - the frontend talks to the
backend over HTTP, proxied under `/api` in dev (see `frontend/vite.config.ts`).

### Backend structure

- `app/models/` - SQLAlchemy models. `Trail` (LineString geometry + difficulty/features/source
  metadata) and `WildlifeSighting` (a cached species observation, currently eBird-sourced, with
  Point geometry).
- `app/integrations/` - one client per third-party data source (`ebird.py`, `weather.py`,
  `birdnet.py`, `osm.py`, `trailapi.py`, `elevation.py`). Each wraps a single external API; this
  is where new data sources get added. `elevation.py` holds two interchangeable DEM clients
  (`OpenMeteoElevation`, `UsgsElevation`) behind a common `lookup(points)`.
- `app/services/` - cross-cutting logic that doesn't belong to one model or one integration
  (`wildlife_likelihood.py`, `catalog_geometry.py`, `trail_metrics.py`, ...).
- `app/routers/` - FastAPI route modules, included in `app/main.py`.

### Frontend structure

The PWA implements the hi-fi design (9 screens: 5 core tabs - Discover, Birbs/Targeting, Trails,
Trips, You - plus 4 flow screens - Trail detail, Optimal time, Fun-drive nav, Bird ID). Most of it
now runs on the **live backend**, not the design's static sample data:
- Discover / Trails / Trail detail read the real catalog near the user's location (`TrailsProvider`
  + `useGeolocation` → `GET /catalog/trails`), with the recency/season/notable wildlife score,
  OSM-derived elevation, eBird species, and NWS weather.
- Targeting (Birbs) ranks trails by a chosen species' live odds (`GET /catalog/species`,
  `?species=` on the trail list); its filter lives in `AppState.speciesFilter`.
- Trips is a real logged-ride store (`GET`/`POST /trips`): the log-ride sheet on the trail detail
  records species (checked off the trail's eBird birds or typed in) and geotagged photos
  (`exifr` reads EXIF GPS client-side; only a downscaled thumbnail + coords are kept), mapped onto
  the trail line.
Bird ID records a mic clip and runs it through BirdNET (`POST /birdnet/identify`). Optimal time
is live too: its dual curve, best window, and hourly strip come from the per-hour ride-time model
(`GET /catalog/trails/{id}/optimal-time` via `useOptimalTime`), which also feeds the Discover hero
window and a Trail-detail card; it falls back to an illustrative sample outside the US (no NWS
hourly forecast). Still static/illustrative: the You tab. `src/data/trails.ts` now holds just the
shared `Trail` type + helpers, not sample rows.

- `src/screens/` - one component + co-located CSS Module per screen, routed in `src/App.tsx`
  (React Router). Flow screens have no bottom nav and use `BackButton`.
- `src/components/` - shared UI: `BottomNav`, `DifficultyMarker`, `ScoreRing`, `Photo`
  (the design's `image-slot` → a real `<img>` with a palette fallback), `icons.tsx` (all custom
  inline-SVG icons), `BirdIdFab`, `BackButton`.
- `src/state/AppState.tsx` - React Context holding cross-screen state (Discover hero/sort, Trails
  sort/dir, the Targeting→Trails species filter, the Trail-detail subject). Screen-local UI state
  stays in the screens.
- `src/data/trails.ts` - the shared `Trail` type, the catalog→Trail adapter, and the ported
  sort/format/score helpers (the static sample rows are gone). `src/data/use*.ts` are the backend
  hooks (trails, catalog detail, nearby species, species-ranked trails, trips, geolocation).
- `src/styles/tokens.css` - all design tokens as CSS custom properties; use these, don't hard-code
  hex. `common.module.css` holds shared visual atoms (eyebrow, title, card, score chips).
- Photos go in `public/assets/` (see its README for the exact filenames); slots show a tasteful
  placeholder until real licensed photos are dropped in.
- Two in-app entry points aren't in the static design (which scrolled between frames): the Bird ID
  floating button (`BirdIdFab`, on Discover + Trail detail) and Optimal time (tap the Discover hero
  window, or a Trail-detail stat tile).

### The wildlife-likelihood model is the product's core differentiator, and is still maturing

`app/services/wildlife_likelihood.py` scores a trail from cached `WildlifeSighting` rows within
a buffer of its geometry. `score_catalog_trails` is the batched scorer the catalog uses: each
species is weighted by how recently it was last seen (`exp(-days/tau)`, so stale reports fade),
and the weights saturate into two 0..98 axes - an overall activity `score` (all species) and a
`notable_score` (only species from eBird's *notable* feed, flagged via `WildlifeSighting.is_notable`
and synced by `sync_notable_observations`). So "likely birds" are the common recent species and
"notable"/`peak` are the rare ones - the product's real hook. Each species' weight is also scaled
by **seasonality** (`species_seasonality`): the set of months it's historically present (learned
from records older than ~35 days so the dense current feed doesn't flatten it), so an out-of-season
vagrant is damped and an in-season specialist lifted. Because the recent/notable feeds cap at
`back=30` days, that cross-season history comes from sampling eBird's per-region `historic` endpoint
- `backfill_region_history` (one day/month) behind `POST /catalog/backfill-history`, which must be
run per region (like the catalog seed) for seasonality to have signal. Still an area-level proxy,
not a calibrated probability: it does not yet weight by eBird search effort (checklists per area) or
time of day, and the historic sampling is coarse (one day/month under-detects month presence).
Treat this model as the area still maturing - the highest-value place to keep deepening.

### The optimal-ride-time model blends live weather with a wildlife-activity prior

`app/services/optimal_ride_time.py` scores the best time-of-day to ride a trail. For each upcoming
daylight hour it computes two 0..98 axes - **riding conditions** (comfort temperature, wind, precip
chance, and daylight, from the NWS *hourly* forecast `forecast_hourly`) and **wildlife activity** (a
crepuscular dawn/dusk prior from `services/solar.py` sun times, scaled by the trail's overall eBird
`score` so a birdier trail's curve sits higher) - then a conditions-weighted `combined` score. The
best window is the highest-summed run of hours near the day's peak. `GET
/catalog/trails/{id}/optimal-time` serves the curve + window; it's the only place that fetches the
hourly forecast (the list/detail stay fast). The conditions axis also folds in a **trail-surface
("tacky"/mud) factor** from recent precipitation (`services/trail_conditions.py`, fed by Open-Meteo's
`past_days` precip via `integrations/precipitation.py` - keyless and *global*, so the surface read
works even outside NWS coverage). That surface model is deliberately non-monotonic in rainfall: dry is
loose/dusty, soaked is mud, and *tacky* (moist, drained) is the prime state; it yields a 0..100 score
+ label (Dry/Firm/Tacky/Wet/Muddy) shown as the Discover hero's "trail conditions" cell (replacing
wind) and a 0..1 factor multiplied into riding conditions. `GET /catalog/optimal-now` ranks nearby
trails by how well *now* overlaps each trail's window (the "Optimal now" sort on Discover + Trails):
weather is computed once for the region, but each trail's surface diverges by its own **drainage**
(`per_trail_surface_factor`: aspect/sun, grade, and OSM surface recover or worsen the regional
wetness deficit - a shaded dirt trail reads muddier than a sun-baked rocky one nearby), and
`score_now` blends that with the trail's crepuscular wildlife term. The same per-trail factor scales
each trail's own optimal-time curve. The model is pure/dependency-free and unit-tested
(`test_optimal_ride_time.py`, `test_trail_conditions.py`, `test_solar.py`); still a first pass, not
calibrated - aspect resolves best on USGS (US) trails, no time-stamped eBird effort yet. NWS is US-only, so the
time-of-day curve fails soft (`available:false`) outside the US, but the Open-Meteo surface rating and
the wildlife/daylight ranking still work there.

### Trail terrain metrics are two-tier (Open-Meteo, then USGS)

`app/services/trail_metrics.py` derives the design's elevation stats (total climb/descent,
avg up/down grade, normalized profile, plus heuristic ride-time/effort) for a catalog trail by
resampling its OSM line to a fixed number of points and looking up each point's DEM elevation.
Two tiers fill the same columns: a fast batched **Open-Meteo** pass over many trails
(`POST /catalog/compute-metrics`, ~90m DEM), then a higher-resolution **USGS 3DEP** refinement
(~1m) computed per-trail when its detail is opened. `CatalogTrail.elev_source` records which tier
produced the current values; the USGS pass is a no-op once a trail is already `usgs`. The coarse
tier visibly over-reads climb on flat trails (Open-Meteo said Sawyer Camp gains 646 ft; USGS, 301)
- that gap is the reason for the refinement.

Metrics are only meaningful over a line that actually represents the trail, so two guards apply:
a sub-metre **noise floor** when summing climb (DEM jitter otherwise inflates it), and a minimum
**mapped length** (`_MIN_METRIC_LENGTH_M`) below which the line is treated as a fragment and
metrics are skipped (`elev_source="too-short"`, columns nulled) rather than fabricated. The
displayed length is `metric_length_mi` (the mapped extent), which can be shorter than TrailAPI's
nominal `length_mi` - the UI labels the elevation card "N mi mapped" to be honest about this.

Beyond climb/descent/grade, `compute` also yields **max grade, high/low point, and longest
sustained climb** (pure math off the same samples), and `ensure_metrics` computes a slope
**aspect + sun-exposure** (`services/trail_surface.py`): it samples the DEM at four neighbours
around points on the line, reduces each to a downhill bearing, and slope-weight-averages them into
a dominant 8-point compass aspect + a 0..1 sun-exposure (1 = fully equator-facing). Aspect is the
per-trail differentiator the optimal-now sort will later use (north-facing trails stay
shaded/wetter). It recomputes when `aspect` is null even on an already-`usgs` trail, so older trails
backfill on detail open. Independently, `ensure_line` aggregates the matched OSM ways' tags
(`osm.summarize_surface`) into a **surface** type and **mtb:scale** technical rating, backfilling
them on detail open when null. All of these surface on the Trail-detail terrain card and feed the
optimal-now sort's per-trail drainage (see `per_trail_surface_factor` below).

### Reassembling full trails from OSM (catalog_geometry.py)

OSM splits a trail into many same-named ways. `assemble_line` pulls every way matching the trail's
name (a loose `_name_core` regex) across a length-sized bbox via `OverpassClient.fetch_named_ways`,
then `stitch_ways` chains them from the trailhead into one ordered line - turning what used to be a
single nearest-way fragment (e.g. 54 m of Sawyer Camp) into the real ~6 mi trail. It falls back to
the old nearest-way match in a small radius when the named assembly comes up short. `ensure_line`
/ `enrich_region` take `force=True` to re-assemble trails that already have an (older fragment)
line; that clears `elev_source` so metrics recompute. Name mismatches (TrailAPI typos like
"Purisma" vs OSM "Purisima") defeat the name filter and fall back to a fragment - those get caught
by the mapped-length guard above, not silently shown.

### Geospatial query gotcha

When querying against a `Trail.geom` or `WildlifeSighting.geom` from another row (e.g.
buffering one trail and intersecting against sightings), build the geometry reference as a SQL
subquery (`select(func.cast(Trail.geom, Geography)).where(...).scalar_subquery()`), not by
loading the ORM object and reusing `trail.geom` as a Python value in a new query. The latter
round-trips through GeoAlchemy2's WKB/WKT bind handling and produces a "parse error - invalid
geometry" from PostGIS. `score_trail_for_species` in `wildlife_likelihood.py` is the reference
pattern.

### Don't add explicit indexes on geometry columns

GeoAlchemy2's `Geometry` type creates a GIST index automatically via a DDL hook whenever its
table is created (`spatial_index=True` is the default), including through Alembic's
`op.create_table`. An explicit `op.create_index(..., postgresql_using="gist")` on a geometry
column will create a redundant duplicate index, not a missing one.

### Integration phasing - what's real vs. stubbed

- **eBird** (`app/integrations/ebird.py`) and **weather/NWS** (`app/integrations/weather.py`)
  are real, working clients against free public APIs.
- **BirdNET** (`app/integrations/birdnet.py`) runs Cornell's open sound-ID model locally via
  `birdnetlib` (a bundled tflite model) - the substitute for the closed Merlin app, which has no
  integration path. Inference is real (`POST /birdnet/identify`, Bird ID screen records a WAV
  client-side and sends it). The heavy deps are an **optional `birdnet` extra** (imported lazily,
  so the API runs without them and the endpoint returns 503); installing it pins `numpy<2` because
  `tflite-runtime` is built against the numpy 1.x ABI. The client records 48 kHz mono WAV so the
  server needs no ffmpeg.
- **Trailforks**: an API request is pending (free/non-profit tier). Not yet integrated.
- **Strava / AllTrails**: not integrated, and not just because they're unbuilt - both carry real
  ToS constraints (Strava's API agreement restricts aggregate/heatmap use of other users' data;
  AllTrails has no public self-serve API). The project's data-source strategy is open data
  (OSM trail geometry, user-uploaded GPX) first, with scraping minimized in favor of open
  alternatives even at some cost to data quality. Don't add a scraper for these without
  checking in - it's a deliberate, revisitable call, not an oversight.
- **Garmin export**: planned as a GPX/TCX file download, not a live device push (no public
  Garmin BLE course-transfer protocol exists, and Garmin Connect's Course API requires partner
  approval).
- **"Fun drive" / twisty-road routing**: not built. No mapping API scores route curvature; this
  will need a custom scoring layer over OSM road geometry (the open-source "Curvature" project
  is the reference design) feeding a router like GraphHopper/OSRM/Valhalla.

### Sensitive-species handling

eBird withholds precise coordinates for sensitive species (owls, rare raptors, etc.) and
returns a coarser location instead. `WildlifeSighting.is_obscured` passes that through as-is.
Never attempt to recover a more precise location for an obscured record - the product intent is
trail-level likelihood ("this trail has good owl odds"), not pinpointing roosts or nests.
