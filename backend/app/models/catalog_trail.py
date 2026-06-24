from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, String, func
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
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
