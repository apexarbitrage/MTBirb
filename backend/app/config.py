from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://mtbirb:mtbirb@localhost:5432/mtbirb"

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, url: str) -> str:
        """Managed Postgres hosts (Render, Neon, ...) hand out `postgres://` / `postgresql://`
        URLs; force the psycopg (v3) driver we depend on so SQLAlchemy doesn't reach for psycopg2."""
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        if url.startswith("postgresql://") and "+" not in url.split("://", 1)[0]:
            url = "postgresql+psycopg://" + url[len("postgresql://") :]
        return url
    ebird_api_key: str = ""
    weather_user_agent: str = "mtbirb (set WEATHER_USER_AGENT in .env)"
    # Overpass endpoint for OSM trail geometry/discovery. The public instance rate-limits
    # sustained sweeps; point heavy seeding runs at a mirror (e.g.
    # https://overpass.kumi.systems/api/interpreter) and switch back afterwards.
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    rapidapi_key: str = ""  # for TrailAPI (RapidAPI); see app/integrations/trailapi.py
    tomtom_api_key: str = ""  # for "fun drive" routing; see app/integrations/tomtom.py
    # Shared secret gating the destructive / quota-burning ops endpoints (seeding, backfills,
    # Overpass sweeps) via the X-Admin-Token header - see app/security.py. Empty = those endpoints
    # are disabled (fail closed) so a public deploy can't be abused; set it to run ops.
    admin_token: str = ""
    # Observability (all optional). SENTRY_DSN enables error tracking (backend exceptions + the
    # forwarded frontend client-errors); empty = disabled. LOG_LEVEL/LOG_FORMAT tune the structured
    # logger (see app/logging_config.py); LOG_FORMAT=json is what you want in a deployed container.
    sentry_dsn: str = ""
    sentry_environment: str = "production"
    log_level: str = "INFO"
    log_format: str = "plain"  # "plain" (readable, dev) or "json" (aggregation, prod)
    # Absolute path to the built frontend (Vite `dist/`). Set in the production container so the
    # API also serves the PWA from the same origin (see app/main.py). Empty in local dev, where
    # Vite serves the SPA and proxies /api to this backend - so the SPA-serving block is skipped.
    frontend_dist: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
