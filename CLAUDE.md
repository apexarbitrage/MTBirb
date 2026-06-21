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
  `birdnet.py`). Each wraps a single external API; this is where new data sources get added.
- `app/services/` - cross-cutting logic that doesn't belong to one model or one integration.
  Currently just `wildlife_likelihood.py`.
- `app/routers/` - FastAPI route modules, included in `app/main.py`.

### The wildlife-likelihood model is the product's core differentiator, and is intentionally unfinished

`app/services/wildlife_likelihood.py` buffers a trail's geometry and counts nearby cached
`WildlifeSighting` rows within a lookback window. That's a raw-count proxy, not a calibrated
"highest chance of seeing an owl" probability - it doesn't yet account for eBird search effort
(checklists per area), seasonality, or time of day. Treat this as the area needing the most
design work, not as a finished feature to extend incrementally.

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
- **BirdNET** (`app/integrations/birdnet.py`) is an interface-only stub. There is no
  third-party integration path into Merlin Bird ID itself (it's a closed consumer app); BirdNET
  is Cornell's open sound-ID model and the intended substitute, but inference isn't wired up.
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
