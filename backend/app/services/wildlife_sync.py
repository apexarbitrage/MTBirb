"""Pull recent eBird observations into the wildlife_sightings cache.

This is the integration glue between the eBird client (one external API call) and the
WildlifeSighting model the likelihood scoring reads from. It only caches what eBird returns;
it never tries to recover precise coordinates for records eBird coarsened or withheld.
"""

from __future__ import annotations

from datetime import datetime, timezone

from geoalchemy2.elements import WKTElement
from sqlalchemy import select, tuple_, update
from sqlalchemy.orm import Session

from app.integrations.ebird import EBirdClient
from app.models import WildlifeSighting


def _parse_obs_dt(value: str) -> datetime:
    # eBird returns local wall-clock time with no offset; "YYYY-MM-DD HH:MM", or just the
    # date when the observer logged no time. We treat it as UTC - good enough for an N-day
    # lookback proxy, and avoids a naive/aware mismatch against the tz-aware column.
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"unrecognized eBird obsDt: {value!r}")


def observation_to_sighting(obs: dict, is_notable: bool = False) -> WildlifeSighting | None:
    """Map one eBird record to a WildlifeSighting, or None if it has no usable point.

    Records without coordinates are eBird's coarsened/withheld sensitive observations; we
    skip them rather than guess a location.
    """
    lat, lng = obs.get("lat"), obs.get("lng")
    if lat is None or lng is None:
        return None
    return WildlifeSighting(
        source="ebird",
        species_code=obs["speciesCode"],
        common_name=obs["comName"],
        observed_at=_parse_obs_dt(obs["obsDt"]),
        checklist_id=obs.get("subId"),
        # obs/geo/recent doesn't flag sensitive records inline (they arrive already coarsened
        # or omitted), so there's nothing to pass through here.
        is_obscured=False,
        is_notable=is_notable,
        geom=WKTElement(f"POINT({lng} {lat})", srid=4326),
    )


def upsert_sightings(db: Session, observations: list[dict], is_notable: bool = False) -> int:
    """Insert observations not already cached. Idempotent on (checklist_id, species_code).

    When `is_notable`, also promotes any already-cached matching row to notable (a species can
    arrive first via the plain recent feed, then again via the notable feed).
    """
    mapped = [
        (obs, s)
        for obs in observations
        if (s := observation_to_sighting(obs, is_notable=is_notable)) is not None
    ]
    if not mapped:
        return 0

    keys = {(obs.get("subId"), obs["speciesCode"]) for obs, _ in mapped}
    existing = {
        tuple(row)
        for row in db.execute(
            select(WildlifeSighting.checklist_id, WildlifeSighting.species_code).where(
                tuple_(WildlifeSighting.checklist_id, WildlifeSighting.species_code).in_(keys)
            )
        )
    }

    added = 0
    for obs, sighting in mapped:
        key = (obs.get("subId"), obs["speciesCode"])
        if key in existing:
            continue
        db.add(sighting)
        existing.add(key)
        added += 1
    if is_notable:
        # Flag any rows (new or pre-existing) for these checklists as notable.
        db.execute(
            update(WildlifeSighting)
            .where(tuple_(WildlifeSighting.checklist_id, WildlifeSighting.species_code).in_(keys))
            .values(is_notable=True)
        )
    db.commit()
    return added


async def sync_recent_observations(
    db: Session,
    lat: float,
    lng: float,
    dist_km: int = 25,
    back_days: int = 14,
    client: EBirdClient | None = None,
) -> int:
    """Fetch recent observations around a point and cache the new ones. Returns rows added."""
    client = client or EBirdClient()
    observations = await client.recent_observations(lat, lng, dist_km, back_days)
    return upsert_sightings(db, observations)


async def sync_notable_observations(
    db: Session,
    lat: float,
    lng: float,
    dist_km: int = 25,
    back_days: int = 14,
    client: EBirdClient | None = None,
) -> int:
    """Fetch recent *notable* observations around a point and cache them flagged. Rows added."""
    client = client or EBirdClient()
    observations = await client.notable_observations(lat, lng, dist_km, back_days)
    return upsert_sightings(db, observations, is_notable=True)
