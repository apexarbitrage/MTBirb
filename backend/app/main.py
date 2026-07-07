import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.logging_config import configure_logging
from app.observability import init_sentry
from app.routers import (
    birdnet,
    catalog,
    errors,
    health,
    map,
    sources,
    trail_routes,
    trails,
    trips,
    wildlife,
)

# Configure structured logging + optional Sentry before anything logs or the app is built.
configure_logging()
init_sentry()

logger = logging.getLogger(__name__)


async def _warm_taxonomy() -> None:
    """Populate ebird_taxa on first startup if the table is empty and EBIRD_API_KEY is set.

    Runs as a fire-and-forget background task so it never delays server startup.
    Subsequent restarts are a no-op because has_taxonomy() returns True once populated."""
    from app.db import SessionLocal
    from app.services.species_taxonomy import has_taxonomy, sync_taxonomy

    if not get_settings().ebird_api_key:
        return
    db = SessionLocal()
    try:
        if not has_taxonomy(db):
            logger.info("ebird_taxa is empty — syncing eBird taxonomy in background")
            count = await sync_taxonomy(db)
            logger.info("eBird taxonomy ready: %d species", count)
    except Exception:
        logger.exception("Background taxonomy warm-up failed (will retry on next search)")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(_warm_taxonomy())
    yield
    # Release the pooled TomTom HTTP connections on shutdown.
    from app.integrations.tomtom import aclose_shared_client

    await aclose_shared_client()


app = FastAPI(title="MTBirb API", lifespan=lifespan)

# /health stays at the root so load balancers / orchestrators can probe it without the /api
# namespace. Everything the frontend calls is grouped under /api - the one stable contract the
# PWA's api client (frontend/src/api/client.ts) and the dev proxy (vite.config.ts) both target,
# so the same paths work in local dev (Vite proxies /api here) and in the single-origin container.
app.include_router(health.router)

api = APIRouter(prefix="/api")
api.include_router(trails.router)
api.include_router(wildlife.router)
api.include_router(sources.router)
api.include_router(catalog.router)
api.include_router(trail_routes.router)
api.include_router(trips.router)
api.include_router(birdnet.router)
api.include_router(map.router)
api.include_router(errors.router)
app.include_router(api)


def _mount_frontend(app: FastAPI, dist: Path) -> None:
    """Serve the built PWA from the same origin as the API (production single-origin deploy).

    Vite's hashed assets are served by StaticFiles under /assets; every other unmatched path
    falls back to index.html so client-side (React Router) deep links and refreshes resolve.
    Skipped entirely when FRONTEND_DIST is unset (local dev / tests), so nothing here affects the
    Vite dev server or pytest.
    """
    index_file = dist / "index.html"
    assets_dir = dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    root = dist.resolve()

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> Response:
        # Never let the SPA catch-all shadow the API or health namespace - return a real 404 so
        # a bad /api call is a JSON 404, not a 200 of index.html.
        if full_path == "health" or full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = (root / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(index_file)


_dist = get_settings().frontend_dist
if _dist:
    _dist_path = Path(_dist)
    if (_dist_path / "index.html").is_file():
        _mount_frontend(app, _dist_path)
    else:
        logger.warning("FRONTEND_DIST=%s has no index.html; not serving the SPA", _dist)
