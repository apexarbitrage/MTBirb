import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import birdnet, catalog, health, map, sources, trails, trips, wildlife

logger = logging.getLogger(__name__)


async def _warm_taxonomy() -> None:
    """Populate ebird_taxa on first startup if the table is empty and EBIRD_API_KEY is set.

    Runs as a fire-and-forget background task so it never delays server startup.
    Subsequent restarts are a no-op because has_taxonomy() returns True once populated."""
    from app.config import get_settings
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


app = FastAPI(title="MTBirb API", lifespan=lifespan)

app.include_router(health.router)
app.include_router(trails.router)
app.include_router(wildlife.router)
app.include_router(sources.router)
app.include_router(catalog.router)
app.include_router(trips.router)
app.include_router(birdnet.router)
app.include_router(map.router)
