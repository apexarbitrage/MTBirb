"""Proxies TomTom raster map tiles so the API key stays server-side.

The frontend's Leaflet base layer points at `/api/map/tile/{z}/{x}/{y}`; we fetch the matching
TomTom tile with the key from `.env` and stream the PNG back. Tiles are immutable, so we let the
browser cache them aggressively. Returns 503 when TOMTOM_API_KEY isn't set.
"""

from fastapi import APIRouter, HTTPException, Response

from app.integrations.tomtom import TomTomClient, TomTomNotConfigured

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/tile/{z}/{x}/{y}")
async def map_tile(z: int, x: int, y: int) -> Response:
    try:
        data = await TomTomClient().fetch_tile(z, x, y)
    except TomTomNotConfigured as exc:
        raise HTTPException(status_code=503, detail="set TOMTOM_API_KEY to enable map tiles") from exc
    except Exception as exc:  # noqa: BLE001 - upstream tile error / out-of-range tile
        raise HTTPException(status_code=502, detail="tile fetch failed") from exc
    return Response(
        content=data,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=604800, immutable"},
    )
