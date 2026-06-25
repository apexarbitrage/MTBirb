"""Sound-based bird ID using Cornell Lab's open BirdNET model (via birdnetlib), in place of the
closed Merlin Bird ID app (no third-party integration path exists for Merlin itself).

Inference runs locally on a bundled BirdNET-Analyzer tflite model. The heavy deps (birdnetlib,
tflite-runtime, librosa, numpy<2) are an optional `birdnet` extra and are imported lazily, so the
rest of the API runs without them - the endpoint returns 503 if they're absent. The model is
loaded once and cached; a lock serialises analysis because the tflite interpreter isn't safe for
concurrent calls. Audio must be a WAV (the client records 48 kHz mono WAV so the server needs no
ffmpeg); pass lat/lon to apply BirdNET's location + season species filter.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import datetime

_analyzer = None
_lock = asyncio.Lock()


def _analyze(audio: bytes, lat: float | None, lon: float | None, min_conf: float) -> list[dict]:
    from birdnetlib import Recording
    from birdnetlib.analyzer import Analyzer

    global _analyzer
    if _analyzer is None:
        _analyzer = Analyzer()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        handle.write(audio)
        path = handle.name
    try:
        kwargs: dict = {"min_conf": min_conf}
        if lat is not None and lon is not None:
            # Location + today's date narrow BirdNET to species plausible here and now.
            kwargs.update(lat=lat, lon=lon, date=datetime.now())
        recording = Recording(_analyzer, path, **kwargs)
        recording.analyze()
        return recording.detections
    finally:
        os.unlink(path)


class BirdNetClient:
    async def identify_from_audio(
        self,
        audio: bytes,
        lat: float | None = None,
        lon: float | None = None,
        min_conf: float = 0.25,
        limit: int = 5,
    ) -> list[dict]:
        """Identify birds in a WAV clip. Returns the top species by confidence (deduped).

        Raises ModuleNotFoundError if the optional birdnet deps aren't installed - callers turn
        that into a 503 so the rest of the API still works without them.
        """
        async with _lock:
            detections = await asyncio.to_thread(_analyze, audio, lat, lon, min_conf)

        # BirdNET emits one detection per 3-second window; collapse to the best per species.
        best: dict[str, dict] = {}
        for det in detections:
            key = det["scientific_name"]
            if key not in best or det["confidence"] > best[key]["confidence"]:
                best[key] = det
        ranked = sorted(best.values(), key=lambda d: d["confidence"], reverse=True)[:limit]
        return [
            {
                "commonName": d["common_name"],
                "scientificName": d["scientific_name"],
                "confidence": round(float(d["confidence"]), 3),
            }
            for d in ranked
        ]
