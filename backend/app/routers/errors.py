"""Sink for frontend error reports.

The PWA's ErrorBoundary and global handlers POST here when a render crash or unhandled rejection
happens, so client-side failures land in the same structured logs (and Sentry, if configured) as
backend errors - otherwise a white-screen bug in the field is invisible. Fields are length-bounded
so the endpoint can't be used to dump large payloads into the logs.
"""

import logging

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from app.observability import capture_client_error

router = APIRouter(prefix="/client-errors", tags=["client-errors"])
logger = logging.getLogger("app.client_errors")


class ClientError(BaseModel):
    message: str = Field(max_length=2000)
    kind: str | None = Field(default=None, max_length=50)
    stack: str | None = Field(default=None, max_length=8000)
    url: str | None = Field(default=None, max_length=2000)
    userAgent: str | None = Field(default=None, max_length=500)


@router.post("", status_code=204)
def report_client_error(err: ClientError) -> Response:
    logger.error(
        "frontend error [%s] at %s: %s", err.kind or "error", err.url or "?", err.message
    )
    capture_client_error(
        err.message,
        {"kind": err.kind, "url": err.url, "userAgent": err.userAgent, "stack": err.stack},
    )
    return Response(status_code=204)
