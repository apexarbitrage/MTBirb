from fastapi import FastAPI

from app.routers import birdnet, catalog, health, map, sources, trails, trips, wildlife

app = FastAPI(title="MTBirb API")

app.include_router(health.router)
app.include_router(trails.router)
app.include_router(wildlife.router)
app.include_router(sources.router)
app.include_router(catalog.router)
app.include_router(trips.router)
app.include_router(birdnet.router)
app.include_router(map.router)
