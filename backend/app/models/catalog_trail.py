from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import JSON, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CatalogTrail(Base):
    """A trail from the external TrailAPI catalog: a trailhead point plus metadata.

    Distinct from `Trail` (the curated, line-geometry trails with the wildlife/weather
    overlay). Catalog rows are the broad TrailAPI dataset - seeded for some regions and
    filled in on demand as areas are browsed, deduped by `external_id`. They carry a POINT
    geometry (TrailAPI gives a trailhead point, not a line); `lat`/`lon` are stored alongside
    so responses don't need a geometry round-trip.
    """

    __tablename__ = "catalog_trails"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(20), default="trailapi")
    external_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    difficulty: Mapped[str | None] = mapped_column(String(40), nullable=True)
    length_mi: Mapped[float | None] = mapped_column(Float, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    url: Mapped[str | None] = mapped_column(String(400), nullable=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    geom: Mapped[str] = mapped_column(Geometry(geometry_type="POINT", srid=4326))
    # Real ridable line from OSM, matched near the trailhead and filled in on demand
    # (null until a detail view or the enrichment job fetches it). See services/catalog_geometry.py.
    line_geom: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326), nullable=True
    )
    # Terrain metrics derived from the line's DEM elevation profile (null until computed). Two
    # tiers fill these: a fast Open-Meteo pass, refined to USGS 3DEP when a detail is opened.
    # `elev_source` records which tier produced the current values. See services/trail_metrics.py.
    metric_length_mi: Mapped[float | None] = mapped_column(Float, nullable=True)
    ascent_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    descent_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_up_grade: Mapped[str | None] = mapped_column(String(12), nullable=True)
    avg_down_grade: Mapped[str | None] = mapped_column(String(12), nullable=True)
    elevation_profile: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    ride_time_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    effort: Mapped[float | None] = mapped_column(Float, nullable=True)
    elev_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Expanded per-trail terrain/surface stats. DEM-derived (set with the elevation metrics):
    max_grade: Mapped[str | None] = mapped_column(String(12), nullable=True)
    high_point_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    low_point_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    longest_climb_mi: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Slope aspect (compass) + sun exposure (0..1), from DEM 2D sampling (services/trail_surface.py):
    aspect: Mapped[str | None] = mapped_column(String(4), nullable=True)
    sun_exposure: Mapped[float | None] = mapped_column(Float, nullable=True)
    # OSM way tags, aggregated when the line is matched (services/catalog_geometry.py):
    surface: Mapped[str | None] = mapped_column(String(40), nullable=True)
    mtb_scale: Mapped[str | None] = mapped_column(String(8), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
