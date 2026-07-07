from datetime import datetime

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TrailRoute(Base):
    """A saved multi-trail route: an ordered chain of catalog trails linked in the route builder.

    `trail_external_ids` is the ordered list of member CatalogTrail.external_id values (chain
    order = the order they were added, each connecting to the chain built so far). Only the name
    and membership are stored - the combined line, stats, and wildlife overlay are recomputed from
    the member rows at read time, so a route improves as its members' metrics refine. Single-user
    for now (no accounts yet), so this is one global set, like trips.

    Named TrailRoute (not Route) because "route" already means car routing here - see
    services/drive_route.py and the /catalog/trails/{id}/drive endpoint.
    """

    __tablename__ = "trail_routes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    trail_external_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
