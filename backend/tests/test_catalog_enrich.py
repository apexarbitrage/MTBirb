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


def test_background_enrichment_is_concurrency_bounded(monkeypatch):
    """A burst of trail opens must never pin more than 2 DB sessions at once - the queued tasks
    wait on the slot semaphore *before* opening a session (the 502/pool-exhaustion guard)."""
    import asyncio

    from app.routers import catalog

    active = {"now": 0, "peak": 0, "sessions": 0}

    class FakeSession:
        def __init__(self):
            active["sessions"] += 1

        def scalar(self, *a, **kw):
            return None  # trail not found -> body returns immediately after the tracked window

        def close(self):
            active["sessions"] -= 1

    real_enrich_one = catalog._enrich_one

    async def tracked(external_id):
        active["now"] += 1
        active["peak"] = max(active["peak"], active["now"])
        await asyncio.sleep(0.01)  # let other queued tasks try to overlap
        try:
            await real_enrich_one(external_id)
        finally:
            active["now"] -= 1

    monkeypatch.setattr(catalog, "SessionLocal", FakeSession)
    monkeypatch.setattr(catalog, "_enrich_one", tracked)

    async def burst():
        await asyncio.gather(*(catalog._enrich_trail_background(f"t{i}") for i in range(8)))

    asyncio.run(burst())
    assert active["peak"] <= 2  # the two slots, never the whole burst
    assert active["sessions"] == 0  # every session closed
    assert catalog._enriching_trails == set()  # dedup set fully drained
