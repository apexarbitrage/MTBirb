"""Hermetic tests for GPX course generation (no network, no database)."""

from xml.etree import ElementTree

from app.services.gpx import build_gpx, slugify

_NS = "{http://www.topografix.com/GPX/1/1}"


def test_slugify() -> None:
    assert slugify("Sawyer Camp Trail") == "sawyer-camp-trail"
    assert slugify("Purisima Creek (Redwoods)!") == "purisima-creek-redwoods"
    assert slugify("") == "trail"
    assert slugify("   ") == "trail"


def test_build_gpx_structure_and_order() -> None:
    points = [[-122.45, 37.50], [-122.46, 37.51], [-122.47, 37.52]]
    xml = build_gpx("Sawyer Camp Trail", points, desc="Easy · 6.0 mi")
    root = ElementTree.fromstring(xml)  # parses -> well-formed
    assert root.tag == f"{_NS}gpx"

    pts = root.findall(f"{_NS}trk/{_NS}trkseg/{_NS}trkpt")
    assert len(pts) == 3
    # Order preserved, lon/lat mapped correctly (GPX is lat/lon).
    assert pts[0].attrib["lat"] == "37.500000" and pts[0].attrib["lon"] == "-122.450000"
    assert pts[2].attrib["lat"] == "37.520000"

    assert root.find(f"{_NS}trk/{_NS}name").text == "Sawyer Camp Trail"
    assert root.find(f"{_NS}trk/{_NS}desc").text == "Easy · 6.0 mi"


def test_build_gpx_escapes_name() -> None:
    xml = build_gpx("Rock & Roll <Trail>", [[-122.0, 37.0]])
    assert "Rock & Roll <Trail>" not in xml  # raw chars must be escaped
    root = ElementTree.fromstring(xml)
    assert root.find(f"{_NS}trk/{_NS}name").text == "Rock & Roll <Trail>"


def test_build_gpx_empty_points_is_valid() -> None:
    root = ElementTree.fromstring(build_gpx("Empty", []))
    assert root.findall(f"{_NS}trk/{_NS}trkseg/{_NS}trkpt") == []
