"""In-trail sound bird ID via BirdNET (Cornell Lab's open model). See integrations/birdnet.py.

The client uploads a WAV clip as the raw request body (so no multipart/ffmpeg is needed) with
optional lat/lon query params for BirdNET's location filter.
"""

from fastapi import APIRouter, HTTPException, Query, Request

from app.integrations.birdnet import BirdNetClient

router = APIRouter(prefix="/birdnet", tags=["birdnet"])

_MAX_AUDIO_BYTES = 12 * 1024 * 1024  # ~12 MB - a generous cap for a few seconds of WAV


@router.post("/identify")
async def identify(
    request: Request,
    lat: float | None = Query(None, ge=-90, le=90),
    lon: float | None = Query(None, ge=-180, le=180),
) -> dict:
    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=400, detail="no audio uploaded")
    if len(audio) > _MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="audio clip too large")
    try:
        detections = await BirdNetClient().identify_from_audio(audio, lat, lon)
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="BirdNET inference isn't installed on the server (pip install '.[birdnet]')",
        ) from exc
    return {"detections": detections}
