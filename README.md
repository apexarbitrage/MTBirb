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
uvicorn app.main:app --reload
```

API runs on `http://localhost:8000`. Run tests with `pytest`, lint with `ruff check .`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dev server runs on `http://localhost:5173` and proxies `/api/*` to the backend on port 8000.

## License

GPLv3 - see `LICENSE`.
