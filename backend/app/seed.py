"""Seed the trails table with the curated sample trails.

This is the migration of the frontend's former static `src/data/trails.ts` into the
database, so the app runs on backend-served data over HTTP. The wildlife/weather fields
live under `derived` and are seeded placeholders until eBird/NWS integrations replace them
(see app/models/trail.py).

Run idempotently with:  python -m app.seed
"""

from __future__ import annotations

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Trail

# A short synthetic polyline near each trail's real-ish locale (lon, lat). Real geometry
# arrives later from OSM/Trailforks/GPX ingestion; these exist so spatial queries (the
# wildlife-likelihood buffer/intersect) have something to run against.
_TRACKS: dict[str, list[tuple[float, float]]] = {
    "raptor": [(-122.4060, 48.7240), (-122.4030, 48.7258), (-122.3995, 48.7271), (-122.3968, 48.7289)],
    "owl": [(-122.4455, 48.7030), (-122.4432, 48.7045), (-122.4408, 48.7053), (-122.4388, 48.7064)],
    "cedar": [(-122.3340, 48.7185), (-122.3312, 48.7201), (-122.3286, 48.7216), (-122.3262, 48.7228)],
    "marsh": [(-122.5870, 48.8222), (-122.5852, 48.8235), (-122.5835, 48.8241), (-122.5818, 48.8249)],
}


def _wkt(slug: str) -> WKTElement:
    pts = ", ".join(f"{lon} {lat}" for lon, lat in _TRACKS[slug])
    return WKTElement(f"LINESTRING({pts})", srid=4326)


TRAIL_SEED: list[dict] = [
    {
        "slug": "raptor",
        "name": "Raptor Ridge",
        "difficulty": "Advanced",
        "features": ["Rock garden", "Drops", "Tech climb"],
        "miles": 8.4,
        "effort": 8.7,
        "ride_time_min": 65,
        "location": "Galbraith Mtn · Bellingham, WA",
        "gain_ft": 2050,
        "climb_ft": 2050,
        "descent_ft": 2180,
        "avg_up_grade": "9.2%",
        "avg_down_grade": "7.8%",
        "elevation": [0.1, 0.22, 0.38, 0.48, 0.66, 0.8, 0.58, 0.44, 0.3, 0.2, 0.13],
        "derived": {
            "score": 94,
            "window": "6:10–8:30 AM · best light & activity",
            "realfeel": "54°",
            "sky": "Clear",
            "condition": "Tacky",
            "dirt": "Tacky",
            "peak": "Northern Goshawk, Pileated Woodpecker",
            "metaTime": "AM",
            "metaBird": "Goshawk",
            "likelyBirds": ["Northern Goshawk", "Pileated Woodpecker", "Sooty Grouse"],
            "sightingHeadline": "94% chance of a notable encounter this morning",
            "factors": [
                {"label": "Seasonality", "value": "Peak", "pct": 90, "tone": "terracotta"},
                {"label": "Time of day", "value": "Dawn — ideal", "pct": 96, "tone": "terracotta"},
                {"label": "Weather match", "value": "Calm, clear", "pct": 84, "tone": "sage"},
                {"label": "Recent reports (14d)", "value": "23 checklists", "pct": 72, "tone": "sage"},
            ],
            "bestWindow": "6:10 – 8:30 AM",
            "bestWindowWhy": "Dry dirt, calm wind, and peak wildlife activity overlap.",
        },
    },
    {
        "slug": "owl",
        "name": "Owl Hollow",
        "difficulty": "Intermediate",
        "features": ["Jumps", "Berms", "Flow"],
        "miles": 5.5,
        "effort": 6.1,
        "ride_time_min": 48,
        "location": "Lake Padden · Bellingham, WA",
        "gain_ft": 1180,
        "climb_ft": 1180,
        "descent_ft": 1210,
        "avg_up_grade": "6.4%",
        "avg_down_grade": "6.0%",
        "elevation": [0.15, 0.28, 0.4, 0.52, 0.46, 0.6, 0.7, 0.55, 0.4, 0.28, 0.18],
        "derived": {
            "score": 91,
            "window": "Dusk · 7:40–8:50 PM · peak owl calls",
            "realfeel": "58°",
            "sky": "Clear",
            "condition": "Tacky",
            "dirt": "Tacky",
            "peak": "Northern Pygmy-Owl",
            "metaTime": "dusk",
            "metaBird": "Pygmy-Owl",
            "likelyBirds": ["Northern Pygmy-Owl", "Varied Thrush", "Pacific Wren"],
            "sightingHeadline": "91% chance of a notable encounter at dusk",
            "factors": [
                {"label": "Seasonality", "value": "Peak", "pct": 88, "tone": "terracotta"},
                {"label": "Time of day", "value": "Dusk — ideal", "pct": 92, "tone": "terracotta"},
                {"label": "Weather match", "value": "Calm, clear", "pct": 80, "tone": "sage"},
                {"label": "Recent reports (14d)", "value": "18 checklists", "pct": 64, "tone": "sage"},
            ],
            "bestWindow": "7:40 – 8:50 PM",
            "bestWindowWhy": "Cooling air and peak owl calls overlap at dusk.",
        },
    },
    {
        "slug": "cedar",
        "name": "Cedar Dust",
        "difficulty": "Intermediate",
        "features": ["Flow", "Roots"],
        "miles": 6.2,
        "effort": 6.8,
        "ride_time_min": 52,
        "location": "Stewart Mtn · Bellingham, WA",
        "gain_ft": 1420,
        "climb_ft": 1420,
        "descent_ft": 1450,
        "avg_up_grade": "7.1%",
        "avg_down_grade": "6.6%",
        "elevation": [0.12, 0.3, 0.42, 0.5, 0.62, 0.72, 0.6, 0.48, 0.36, 0.24, 0.16],
        "derived": {
            "score": 88,
            "window": "Morning · 6:30–9:00 AM · cool & calm",
            "realfeel": "52°",
            "sky": "Part cloud",
            "condition": "Tacky",
            "dirt": "Tacky",
            "peak": "Pileated Woodpecker",
            "metaTime": "AM",
            "metaBird": "Pileated Woodpecker",
            "likelyBirds": ["Pileated Woodpecker", "Red Crossbill", "Gray Jay"],
            "sightingHeadline": "88% chance of a notable encounter this morning",
            "factors": [
                {"label": "Seasonality", "value": "High", "pct": 82, "tone": "terracotta"},
                {"label": "Time of day", "value": "Morning — good", "pct": 86, "tone": "terracotta"},
                {"label": "Weather match", "value": "Cool, calm", "pct": 78, "tone": "sage"},
                {"label": "Recent reports (14d)", "value": "15 checklists", "pct": 58, "tone": "sage"},
            ],
            "bestWindow": "6:30 – 9:00 AM",
            "bestWindowWhy": "Cool, calm morning with low traffic and good light.",
        },
    },
    {
        "slug": "marsh",
        "name": "Marsh Loop",
        "difficulty": "Easy",
        "features": ["Boardwalk", "Flowy"],
        "miles": 3.1,
        "effort": 3.4,
        "ride_time_min": 26,
        "location": "Tennant Lake · Ferndale, WA",
        "gain_ft": 240,
        "climb_ft": 240,
        "descent_ft": 240,
        "avg_up_grade": "2.1%",
        "avg_down_grade": "2.0%",
        "elevation": [0.4, 0.46, 0.42, 0.5, 0.45, 0.52, 0.48, 0.54, 0.46, 0.5, 0.44],
        "derived": {
            "score": 76,
            "window": "Midday · 11 AM–1 PM · wetland activity",
            "realfeel": "63°",
            "sky": "Clear",
            "condition": "Dry",
            "dirt": "Dry",
            "peak": "Great Blue Heron",
            "metaTime": "midday",
            "metaBird": "Heron",
            "likelyBirds": ["Great Blue Heron", "Green Heron", "Belted Kingfisher"],
            "sightingHeadline": "76% chance of a wildlife encounter midday",
            "factors": [
                {"label": "Seasonality", "value": "Moderate", "pct": 70, "tone": "terracotta"},
                {"label": "Time of day", "value": "Midday — fair", "pct": 64, "tone": "sage"},
                {"label": "Weather match", "value": "Warm, clear", "pct": 72, "tone": "sage"},
                {"label": "Recent reports (14d)", "value": "31 checklists", "pct": 80, "tone": "terracotta"},
            ],
            "bestWindow": "11:00 AM – 1:00 PM",
            "bestWindowWhy": "Midday wetland activity with warm, clear skies.",
        },
    },
]


def seed_trails(db: Session) -> int:
    """Upsert the curated trails by slug. Returns the number of trails seeded."""
    for entry in TRAIL_SEED:
        slug = entry["slug"]
        trail = db.scalar(select(Trail).where(Trail.slug == slug))
        if trail is None:
            trail = Trail(slug=slug, source="seed")
            db.add(trail)
        trail.name = entry["name"]
        trail.source = "seed"
        trail.difficulty = entry["difficulty"]
        trail.features = entry["features"]
        trail.miles = entry["miles"]
        trail.length_m = round(entry["miles"] * 1609.34, 1)
        trail.effort = entry["effort"]
        trail.ride_time_min = entry["ride_time_min"]
        trail.location = entry["location"]
        trail.gain_ft = entry["gain_ft"]
        trail.climb_ft = entry["climb_ft"]
        trail.descent_ft = entry["descent_ft"]
        trail.avg_up_grade = entry["avg_up_grade"]
        trail.avg_down_grade = entry["avg_down_grade"]
        trail.elevation = entry["elevation"]
        trail.derived = entry["derived"]
        trail.geom = _wkt(slug)
    db.commit()
    return len(TRAIL_SEED)


def main() -> None:
    db = SessionLocal()
    try:
        count = seed_trails(db)
        print(f"seeded {count} trails")
    finally:
        db.close()


if __name__ == "__main__":
    main()
