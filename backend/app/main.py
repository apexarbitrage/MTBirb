from fastapi import FastAPI

from app.routers import health, trails

app = FastAPI(title="MTBirb API")

app.include_router(health.router)
app.include_router(trails.router)
