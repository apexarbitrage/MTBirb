"""Hermetic test for the BirdNET client's post-processing (model stubbed - no inference)."""

import asyncio

import app.integrations.birdnet as birdnet
from app.integrations.birdnet import BirdNetClient


def test_identify_dedups_ranks_and_shapes(monkeypatch) -> None:
    fake_detections = [
        {"common_name": "American Robin", "scientific_name": "Turdus migratorius", "confidence": 0.41},
        # A second, stronger window for the same species - should collapse to this one.
        {"common_name": "American Robin", "scientific_name": "Turdus migratorius", "confidence": 0.83},
        {"common_name": "Song Sparrow", "scientific_name": "Melospiza melodia", "confidence": 0.62},
    ]
    monkeypatch.setattr(birdnet, "_analyze", lambda audio, lat, lon, min_conf: fake_detections)

    out = asyncio.run(BirdNetClient().identify_from_audio(b"fake-wav", lat=37.5, lon=-122.3))

    assert [d["commonName"] for d in out] == ["American Robin", "Song Sparrow"]  # deduped, ranked
    assert out[0]["confidence"] == 0.83
    assert out[0]["scientificName"] == "Turdus migratorius"
