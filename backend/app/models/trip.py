from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Trip(Base):
    """A logged ride: which trail, when, and which species the rider saw.

    Single-user for now (no accounts yet), so this is one global ride history. `birds` is a
    list of {"species_code": str | None, "common_name": str} - some checked off from the
    trail's likely/recent eBird species, some typed in by hand. "Lifers" (first-ever sightings)
    are derived from the whole history at read time, not stored.
    """

    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    trail_external_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    trail_name: Mapped[str] = mapped_column(String(200))
    difficulty: Mapped[str | None] = mapped_column(String(40), nullable=True)
    miles: Mapped[float | None] = mapped_column(Float, nullable=True)
    ridden_on: Mapped[date] = mapped_column(Date)
    birds: Mapped[list[dict]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
