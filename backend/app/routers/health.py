import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: the process is up. Cheap and dependency-free (no DB), so a load balancer can
    tell the app apart from the database being down - use /ready for that."""
    return {"status": "ok"}


@router.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    """Readiness: the app can actually serve traffic, i.e. the database answers. Returns 503 when
    it doesn't, so an orchestrator doesn't route to an instance that can't reach Postgres."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - any DB failure means not ready
        logger.warning("readiness probe failed: database unavailable", exc_info=True)
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ready"}
