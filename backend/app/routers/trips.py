"""Logged rides: the user's trip history with the species they saw.

Single-user for now (no accounts), so this is one global history. "Lifers" - first-ever
sightings - are derived from the whole history in chronological order at read time, so they
stay correct as trips are added or back-dated.
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Trip
from app.schemas.trip import TripCreate, TripOut

router = APIRouter(prefix="/trips", tags=["trips"])


def _bird_key(bird: dict) -> str:
    """Identity for lifer counting: the eBird code if present, else the typed name."""
    return (bird.get("species_code") or bird.get("common_name", "")).strip().lower()


@router.get("")
def list_trips(db: Session = Depends(get_db)) -> dict:
    # Chronological pass so each species is a lifer on its earliest trip; ties broken by insert order.
    chronological = list(db.scalars(select(Trip).order_by(Trip.ridden_on, Trip.created_at, Trip.id)))
    seen: set[str] = set()
    lifers: dict[int, int] = {}
    life_list: set[str] = set()
    total_birds = 0
    for t in chronological:
        count = 0
        for bird in t.birds or []:
            key = _bird_key(bird)
            total_birds += 1
            if key:
                life_list.add(key)
                if key not in seen:
                    seen.add(key)
                    count += 1
        lifers[t.id] = count

    newest_first = sorted(chronological, key=lambda t: (t.ridden_on, t.created_at, t.id), reverse=True)
    return {
        "trips": [TripOut.from_model(t, lifers[t.id]) for t in newest_first],
        "stats": {"rides": len(chronological), "birds": total_birds, "lifeList": len(life_list)},
    }


@router.post("")
def create_trip(body: TripCreate, db: Session = Depends(get_db)) -> TripOut:
    trip = Trip(
        trail_external_id=body.trailExternalId,
        trail_name=body.trailName,
        difficulty=body.difficulty,
        miles=body.miles,
        ridden_on=body.riddenOn or date.today(),
        birds=[{"species_code": b.speciesCode, "common_name": b.commonName} for b in body.birds],
        photos=[
            {"lat": p.lat, "lon": p.lon, "taken_at": p.takenAt, "thumb": p.thumb} for p in body.photos
        ],
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return TripOut.from_model(trip, 0)  # lifers are recomputed on the next list call
