from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Trail

router = APIRouter(prefix="/trails", tags=["trails"])


@router.get("")
def list_trails(db: Session = Depends(get_db)) -> list[dict]:
    trails = db.scalars(select(Trail)).all()
    return [
        {"id": t.id, "name": t.name, "source": t.source, "difficulty": t.difficulty}
        for t in trails
    ]


@router.get("/{trail_id}")
def get_trail(trail_id: int, db: Session = Depends(get_db)) -> dict:
    trail = db.get(Trail, trail_id)
    if trail is None:
        raise HTTPException(status_code=404, detail="trail not found")
    return {
        "id": trail.id,
        "name": trail.name,
        "source": trail.source,
        "difficulty": trail.difficulty,
        "features": trail.features,
        "length_m": trail.length_m,
    }
