from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class WildlifeSighting(Base):
    """A cached species observation (currently sourced from eBird) used for likelihood scoring.

    `is_obscured` mirrors eBird's own sensitive-species handling: when true, `geom` is the
    coarse hotspot/region location eBird returned, not a precise sighting point. We never
    attempt to recover a more precise location for obscured records.
    """

    __tablename__ = "wildlife_sightings"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(20), default="ebird")
    species_code: Mapped[str] = mapped_column(String(20))
    common_name: Mapped[str] = mapped_column(String(200))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    checklist_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_obscured: Mapped[bool] = mapped_column(Boolean, default=False)
    geom: Mapped[str] = mapped_column(Geometry(geometry_type="POINT", srid=4326))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
