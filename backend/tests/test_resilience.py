"""P1 resilience/hardening: media sniffing, the /ready DB probe, upload validation, trip bounds.

All hermetic - the /ready tests override get_db with a fake session, and the upload-validation
checks reject before any DB/model/external call.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.db import get_db
from app.main import app
from app.media import is_wav, sniff_image
from app.schemas.trip import TripCreate, TripPhoto

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 8
WAV = b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 8


def test_sniff_image_recognizes_real_signatures():
    assert sniff_image(PNG) == "image/png"
    assert sniff_image(JPEG) == "image/jpeg"
    assert sniff_image(WEBP) == "image/webp"
    assert sniff_image(b"GIF89a" + b"\x00" * 10) == "image/gif"


def test_sniff_image_rejects_non_images():
    assert sniff_image(b"not an image at all") is None
    assert sniff_image(WAV) is None  # audio is not an image
    assert sniff_image(b"") is None


def test_is_wav():
    assert is_wav(WAV) is True
    assert is_wav(b"RIFF\x00\x00\x00\x00AVI ") is False
    assert is_wav(PNG) is False


def test_ready_returns_200_when_db_answers():
    class OkSession:
        def execute(self, *a, **k):
            return None

    app.dependency_overrides[get_db] = lambda: OkSession()
    try:
        resp = TestClient(app).get("/ready")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ready"}
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_ready_returns_503_when_db_down():
    class FailSession:
        def execute(self, *a, **k):
            raise RuntimeError("db down")

    app.dependency_overrides[get_db] = lambda: FailSession()
    try:
        resp = TestClient(app).get("/ready")
        assert resp.status_code == 503
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_health_stays_liveness_only():
    # /health must not depend on the DB (it's the liveness probe).
    assert TestClient(app).get("/health").json() == {"status": "ok"}


def test_birdnet_rejects_empty_body():
    assert TestClient(app).post("/api/birdnet/identify", content=b"").status_code == 400


def test_birdnet_rejects_non_wav():
    # Arbitrary bytes are turned away (415) before ever reaching the audio decoder.
    assert TestClient(app).post("/api/birdnet/identify", content=b"totally not audio").status_code == 415


def test_trip_photo_count_is_bounded():
    photo = {"thumb": "data:image/jpeg;base64,AAAA"}
    with pytest.raises(ValidationError):
        TripCreate(trailName="X", photos=[photo] * 13)


def test_trip_thumb_size_is_bounded():
    with pytest.raises(ValidationError):
        TripPhoto(thumb="x" * 400_001)
