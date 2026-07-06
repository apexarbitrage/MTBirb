"""Optional Sentry error tracking.

Enabled only when SENTRY_DSN is set - otherwise every function here is a no-op, so local dev and
tests behave exactly as before and nothing is sent anywhere. sentry-sdk auto-instruments the
FastAPI/Starlette stack, so unhandled backend exceptions are captured once init runs; forwarded
frontend crashes (POST /api/client-errors) are captured explicitly via capture_client_error.
"""

from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

_sentry_active = False


def init_sentry() -> bool:
    """Initialise Sentry if SENTRY_DSN is configured. Returns whether it was enabled."""
    global _sentry_active
    dsn = get_settings().sentry_dsn
    if not dsn:
        return False
    try:
        import sentry_sdk
    except ImportError:
        logger.warning("SENTRY_DSN is set but sentry-sdk isn't installed; error tracking disabled")
        return False
    sentry_sdk.init(
        dsn=dsn,
        environment=get_settings().sentry_environment,
        traces_sample_rate=0.0,  # errors only; no perf tracing overhead for the beta
        send_default_pii=False,
    )
    _sentry_active = True
    logger.info("Sentry error tracking enabled (environment=%s)", get_settings().sentry_environment)
    return True


def capture_client_error(message: str, context: dict | None = None) -> None:
    """Forward a frontend-reported error to Sentry (tagged source=frontend). No-op if disabled."""
    if not _sentry_active:
        return
    import sentry_sdk

    with sentry_sdk.push_scope() as scope:
        scope.set_tag("source", "frontend")
        for key, value in (context or {}).items():
            if value is not None:
                scope.set_extra(key, value)
        sentry_sdk.capture_message(message, level="error")
