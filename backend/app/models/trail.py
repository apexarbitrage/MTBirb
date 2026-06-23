from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import JSON, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Trail(Base):
    """A mountain biking trail, sourced from OSM, Trailforks, or a user-uploaded GPX."""

    __tablename__ = "trails"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stable, human-readable handle ("raptor", "owl"). Exposed to the frontend as the trail
    # `id` so client-side routing and cross-references stay string-keyed and source-independent.
    slug: Mapped[str | None] = mapped_column(String(60), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    features: Mapped[list[str]] = mapped_column(JSON, default=list)
    length_m: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Trail-intrinsic ride attributes (facts about the trail itself) ---
    miles: Mapped[float | None] = mapped_column(Float, nullable=True)
    effort: Mapped[float | None] = mapped_column(Float, nullable=True)
    ride_time_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gain_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    climb_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    descent_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_up_grade: Mapped[str | None] = mapped_column(String(10), nullable=True)
    avg_down_grade: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Normalized 0..1 elevation profile sample points, left -> right.
    elevation: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)

    # --- Integration-derived overlay (SEED PLACEHOLDER) ---
    # Holds the wildlife- and weather-derived presentation fields the UI shows today
    # (score, sighting factors, likely birds, forecast window, surface condition, etc.).
    # These are currently seeded constants, NOT live computations. They get replaced by:
    #   - wildlife fields  -> services/wildlife_likelihood.py over eBird-sourced sightings
    #   - weather fields   -> integrations/weather.py (NWS forecast)
    # Kept as one JSON blob (rather than columns) precisely because it is not yet real data.
    derived: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    geom: Mapped[str] = mapped_column(Geometry(geometry_type="LINESTRING", srid=4326))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
