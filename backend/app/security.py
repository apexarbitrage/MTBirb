"""Admin-token guard for the destructive / quota-burning ops endpoints.

The catalog/wildlife/sources sync + backfill endpoints fan out to metered third-party APIs
(eBird quota) and the public Overpass instance (a bulk sweep gets the server IP rate-limited or
banned), and some reset shared data (sync-taxonomy deletes and re-inserts the whole taxonomy). On
a public deploy with no accounts, leaving them open is an abuse/cost vector. This dependency
requires the `X-Admin-Token` header to match `ADMIN_TOKEN`.

Fail closed: if `ADMIN_TOKEN` is unset the endpoints are disabled (503), so a deploy that forgot
to configure it can't be abused. Browse/read endpoints and genuine user actions (log a ride,
BirdNET identify, set a hero photo) are intentionally NOT gated.
"""

import secrets

from fastapi import Header, HTTPException

from app.config import get_settings


def require_admin(x_admin_token: str = Header(default="", alias="X-Admin-Token")) -> None:
    expected = get_settings().admin_token
    if not expected:
        raise HTTPException(status_code=503, detail="admin endpoints are disabled (set ADMIN_TOKEN)")
    # Constant-time compare so a wrong token can't be recovered by timing.
    if not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=403, detail="invalid or missing admin token")
