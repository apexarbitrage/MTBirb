from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Trail
from app.schemas.trail import TrailOut

router = APIRouter(prefix="/trails", tags=["trails"])


@router.get("")
def list_trails(db: Session = Depends(get_db)) -> list[TrailOut]:
    trails = db.scalars(select(Trail).order_by(Trail.id)).all()
    return [TrailOut.from_model(t) for t in trails]


@router.get("/{slug}")
def get_trail(slug: str, db: Session = Depends(get_db)) -> TrailOut:
    trail = db.scalar(select(Trail).where(Trail.slug == slug))
    if trail is None:
        raise HTTPException(status_code=404, detail="trail not found")
    return TrailOut.from_model(trail)
