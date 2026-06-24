from fastapi import FastAPI

from app.routers import health, sources, trails, wildlife

app = FastAPI(title="MTBirb API")

app.include_router(health.router)
app.include_router(trails.router)
app.include_router(wildlife.router)
app.include_router(sources.router)
