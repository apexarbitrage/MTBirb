"""Search the full eBird taxonomy by name, independent of any local sightings.

`WildlifeSighting`-backed search (`species_near` in wildlife_likelihood.py) only knows species
someone has actually reported nearby. This lets the targeting picker find *any* eBird species by
name - useful for a rider chasing something that hasn't (yet) been seen near them. eBird's
taxonomy endpoint has no free-text search, so we cache the whole list (`EbirdTaxon`, ~16k rows)
once and filter it locally.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.ebird import EBirdClient
from app.models import EbirdTaxon


def taxon_from_record(record: dict) -> EbirdTaxon | None:
    """Map one eBird taxonomy row to an EbirdTaxon, or None if it lacks a code/name."""
    code, name = record.get("speciesCode"), record.get("comName")
    if not code or not name:
        return None
    return EbirdTaxon(species_code=code, common_name=name, scientific_name=record.get("sciName", ""))


def rank_by_name(matches: list[dict], query: str) -> list[dict]:
    """Lift common-name-prefix matches above mid-string matches; alphabetical within each tier."""
    lowered = query.strip().lower()
    return sorted(matches, key=lambda m: (not m["common_name"].lower().startswith(lowered), m["common_name"]))


def has_taxonomy(db: Session) -> bool:
    try:
        return db.scalar(select(EbirdTaxon.species_code).limit(1)) is not None
    except Exception:
        return False  # table probably doesn't exist yet (migration pending)


async def sync_taxonomy(db: Session, client: EBirdClient | None = None) -> int:
    """Fetch the full taxonomy from eBird and (re)populate the local cache. Returns row count."""
    from sqlalchemy import delete as sa_delete, insert as sa_insert

    client = client or EBirdClient()
    records = await client.taxonomy()
    rows = [
        {"species_code": t.species_code, "common_name": t.common_name, "scientific_name": t.scientific_name}
        for r in records
        if (t := taxon_from_record(r)) is not None
    ]
    if not rows:
        return 0
    db.execute(sa_delete(EbirdTaxon))
    db.execute(sa_insert(EbirdTaxon), rows)
    db.commit()
    return len(rows)


def search_taxonomy(db: Session, query: str, limit: int = 20) -> list[dict]:
    """Species whose common name contains `query` (case-insensitive), name-first matches lifted.

    Plain substring match - fine at this scale (~16k rows) without a trigram index.
    """
    q = query.strip()
    if not q:
        return []
    rows = db.execute(
        select(EbirdTaxon.species_code, EbirdTaxon.common_name, EbirdTaxon.scientific_name)
        .where(EbirdTaxon.common_name.ilike(f"%{q}%"))
        .limit(limit * 4)  # over-fetch so prefix matches can be ranked first, then trim
    ).all()
    matches = [
        {"species_code": r.species_code, "common_name": r.common_name, "scientific_name": r.scientific_name}
        for r in rows
    ]
    return rank_by_name(matches, q)[:limit]
