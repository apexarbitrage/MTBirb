# MTBirb

MTBirb helps mountain bikers find trails that are also great for birdwatching and wildlife
viewing. Riders pick a trail by the usual criteria (difficulty, features like rock gardens or
jumps, condition, expected busyness) and by what they want to see (a specific species, the
highest chance of any wildlife encounter, or the highest chance of something unusual). The app
also suggests the best time of day to ride based on weather, and routes drivers to the
trailhead - including a "fun drive" option that maximizes twisty mountain roads.

## Status

Early scaffold. The frontend implements the full hi-fi design - 9 screens (Discover, Birbs,
Trails, Trips, You, plus Trail detail, Optimal time, Fun-drive nav, and Bird ID) - currently on
static sample data; wiring it to the backend is the next step. On the backend, trail data is
OSM-derived/user-uploaded GPX only; eBird-based wildlife scoring exists as a first-pass proxy
(see `app/services/wildlife_likelihood.py`). Strava, Trailforks, and AllTrails integrations, the
curvature-based driving router, BirdNET sound ID, and Garmin export are not built yet - see
`CLAUDE.md` for the full phasing.

## Project layout

- `backend/` - FastAPI + PostgreSQL/PostGIS API
- `frontend/` - React + Vite installable PWA; implements the design screens (`src/screens/`) on
  sample data (`src/data/`). Drop licensed photos into `public/assets/`.

## Running locally

### Database

```bash
docker compose up -d
```

Starts Postgres 16 with PostGIS on `localhost:5432` (user/password/db: `mtbirb`).

> If Docker isn't available in your environment, an equivalent local PostgreSQL 16 install
> with the `postgresql-16-postgis-3` package works the same way - just create the `mtbirb`
> user/database and run `CREATE EXTENSION postgis;` once as a superuser before migrating.

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in EBIRD_API_KEY, etc.
alembic upgrade head
python -m app.seed_sample   # load a Bay Area trail sample (no TrailAPI key needed)
uvicorn app.main:app --reload
```

API runs on `http://localhost:8000`. Run tests with `pytest`, lint with `ruff check .`.

`python -m app.seed_sample` populates ~68 real Bay Area trails from a committed fixture so the app
works immediately with only the free data sources (eBird for wildlife - set `EBIRD_API_KEY`; NWS
weather and Open-Meteo/USGS elevation need no key). A `RAPIDAPI_KEY` (TrailAPI) is only needed to
discover trails in *other* regions on demand, and its free tier is heavily rate-limited - the
sample seed avoids it entirely. `python -m app.seed_catalog` does the full TrailAPI grid sweep.

To **pre-seed whole regions** so testers there never hit the on-demand "cold load," use
`python -m app.seed_region` - it sweeps a grid caching trails (TrailAPI) + wildlife (eBird
recent/notable) + a seasonality backfill, skipping already-populated cells (so runs are resumable):

```bash
python -m app.seed_region --all                 # every known region (norcal, ct, ny)
python -m app.seed_region ny --no-trails         # eBird only (doesn't touch the TrailAPI quota)
python -m app.seed_region ct --max-trail-calls 20
```

Wildlife is the bigger latency win and eBird is lenient, so if TrailAPI quota is tight, seed
wildlife first (`--no-trails`), then add trails in capped batches - a re-run resumes where it left
off. Geometry/elevation aren't seeded here (they load lazily per trail-detail, and bulk Overpass
sweeps risk an IP ban).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dev server runs on `http://localhost:5173` and proxies `/api/*` to the backend on port 8000.

> All backend routes are served under `/api` (e.g. `GET /api/catalog/trails`), except the
> root `/health` probe. The PWA's api client and the dev proxy both target `/api`, so the same
> paths work in dev and in the production container below.
>
> The **ops endpoints** (`/api/catalog/sync`, `/sync-taxonomy`, `/backfill-history`,
> `/enrich-geometry`, `/compute-metrics`, `/api/wildlife/sync`, `/api/sources/osm/sync-geometry`)
> are gated by `ADMIN_TOKEN` — send it as an `X-Admin-Token` header. They fan out to metered APIs
> and the public Overpass instance, so they're disabled (503) unless `ADMIN_TOKEN` is set:
> `curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" "http://localhost:8000/api/catalog/backfill-history?..."`.
> (The `python -m app.seed_*` scripts talk to the services directly and need no token.)

## Deploying (single-origin container)

For a beta deploy, one container serves both the API and the built PWA from the same origin, so
there's no CORS or reverse-proxy layer to configure - the frontend's `/api` contract just works.

```bash
docker compose up --build         # Postgres + the app on http://localhost:8000
```

This brings up PostGIS and the `app` image (built from the root `Dockerfile`: a Vite build stage
feeds its `dist/` into the FastAPI runtime, which serves it via `FRONTEND_DIST`). Migrations run
automatically on start (`backend/docker-entrypoint.sh`). API keys are read from `backend/.env` if
present (optional; the app degrades gracefully without them).

To run somewhere real (Fly.io, Railway, Render, a VM, ...):

1. Build and push the root `Dockerfile` (add `--build-arg INSTALL_BIRDNET=true` to include the
   optional local BirdNET sound-ID model; off by default to keep the image small).
2. Provision managed **Postgres + PostGIS** and set `DATABASE_URL` (use `sslmode=require` for most
   managed providers). The extension is created by the first migration.
3. Inject secrets as **environment variables** (not a committed `.env`): `EBIRD_API_KEY`,
   `RAPIDAPI_KEY`, `TOMTOM_API_KEY`, `WEATHER_USER_AGENT` (NWS requires a real contact string), and
   `ADMIN_TOKEN` (gates the ops endpoints; leave unset in prod to keep them disabled). For
   observability set `LOG_FORMAT=json` (machine-readable logs) and, optionally, `SENTRY_DSN`
   (error tracking — captures backend exceptions and forwarded frontend crashes; inert when unset).
4. The container runs `alembic upgrade head` on start, then `uvicorn` on `:8000`
   (set `WEB_CONCURRENCY` for worker count). Point a **liveness** check at `/health` (cheap, no
   DB) and a **readiness** check at `/ready` (verifies Postgres answers; 503 when it doesn't).
5. Seed the region once it's up, e.g. `docker compose exec app python -m app.seed_catalog`
   (needs `RAPIDAPI_KEY`), then run the per-region history backfill for wildlife seasonality.

## License

GPLv3 - see `LICENSE`.
