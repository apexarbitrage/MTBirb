"""Builds a GPX course file from a trail's line, for the "export to Garmin" download.

GPX is the universal course format - Garmin Connect imports it (and applies its own elevation
correction to courses), and it also works with Strava/Komoot/RideWithGPS/Wahoo. We emit a single
track of lat/lon points; elevation is intentionally omitted (Garmin recomputes it, and it keeps the
export fast + offline). Pure string generation so it's unit-testable.
"""

from __future__ import annotations

import re
from xml.sax.saxutils import escape, quoteattr


def slugify(name: str) -> str:
    """A filename-safe slug, e.g. "Sawyer Camp Trail" -> "sawyer-camp-trail"."""
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "trail").lower()).strip("-")
    return slug or "trail"


def build_gpx(name: str, points: list[list[float]], *, desc: str | None = None) -> str:
    """A GPX 1.1 document with one track. `points` are [[lon, lat], ...] (as line_points returns)."""
    trkpts = "\n".join(
        f'      <trkpt lat={quoteattr(f"{lat:.6f}")} lon={quoteattr(f"{lon:.6f}")}/>'
        for lon, lat in points
    )
    desc_el = f"\n    <desc>{escape(desc)}</desc>" if desc else ""
    safe_name = escape(name or "Trail")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<gpx version="1.1" creator="MTBirb" xmlns="http://www.topografix.com/GPX/1/1">\n'
        f"  <metadata>\n    <name>{safe_name}</name>\n  </metadata>\n"
        f"  <trk>\n    <name>{safe_name}</name>{desc_el}\n"
        f"    <trkseg>\n{trkpts}\n    </trkseg>\n"
        "  </trk>\n"
        "</gpx>\n"
    )
