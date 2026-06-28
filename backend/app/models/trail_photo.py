from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TrailPhoto(Base):
    """A rider-supplied hero photo for a catalog trail, stored as image bytes.

    No accounts yet, so (like `Trip`) this is one global photo per trail - the latest upload
    replaces the previous one. Keyed loosely by the catalog `external_id`, so it survives the
    catalog row being re-fetched. `updated_at` doubles as a cache-busting version token for the
    image URL (`GET /catalog/trails/{id}/photo?v=...`), so a long browser cache stays correct.
    """

    __tablename__ = "trail_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    trail_external_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    image: Mapped[bytes] = mapped_column(LargeBinary)
    content_type: Mapped[str] = mapped_column(String(60), default="image/jpeg")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
