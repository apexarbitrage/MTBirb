from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import JSON, DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Trail(Base):
    """A mountain biking trail, sourced from OSM, Trailforks, or a user-uploaded GPX."""

    __tablename__ = "trails"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    features: Mapped[list[str]] = mapped_column(JSON, default=list)
    length_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    geom: Mapped[str] = mapped_column(Geometry(geometry_type="LINESTRING", srid=4326))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
