"""The trail-detail background-enrichment gate (routers/catalog._needs_enrichment)."""

from types import SimpleNamespace

from app.routers.catalog import _needs_enrichment


def _t(line, source):
    return SimpleNamespace(line_geom=line, elev_source=source)


def test_needs_enrichment_when_line_or_metrics_missing():
    assert _needs_enrichment(_t(None, None)) is True          # brand new: no line, no metrics
    assert _needs_enrichment(_t(None, "usgs")) is True         # no line yet
    assert _needs_enrichment(_t("LINESTRING(...)", None)) is True        # line but no metrics
    assert _needs_enrichment(_t("LINESTRING(...)", "open-meteo")) is True  # coarse metrics -> refine


def test_no_enrichment_when_terminal():
    assert _needs_enrichment(_t("LINESTRING(...)", "usgs")) is False       # fully refined
    assert _needs_enrichment(_t("LINESTRING(...)", "too-short")) is False  # can't improve; terminal
