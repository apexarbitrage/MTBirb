"""Structured logging, the Sentry opt-in, and the /client-errors sink.

Hermetic - Sentry stays disabled (no DSN), and the endpoint logs without any DB/external call.
"""

import json
import logging
import sys

from fastapi.testclient import TestClient

from app import observability
from app.logging_config import JsonFormatter, configure_logging
from app.main import app


def test_json_formatter_emits_valid_json():
    rec = logging.LogRecord("mylogger", logging.INFO, __file__, 1, "hello %s", ("world",), None)
    out = json.loads(JsonFormatter().format(rec))
    assert out["level"] == "INFO"
    assert out["logger"] == "mylogger"
    assert out["message"] == "hello world"


def test_json_formatter_includes_traceback():
    try:
        raise ValueError("boom")
    except ValueError:
        rec = logging.LogRecord("x", logging.ERROR, __file__, 1, "failed", (), sys.exc_info())
    out = json.loads(JsonFormatter().format(rec))
    assert "boom" in out["exc"]


def test_configure_logging_runs_without_error():
    configure_logging()  # must not raise for either format
    logging.getLogger("app.test").info("configured")


def test_sentry_disabled_without_dsn(monkeypatch):
    class _S:
        sentry_dsn = ""
        sentry_environment = "test"

    monkeypatch.setattr(observability, "get_settings", lambda: _S())
    assert observability.init_sentry() is False
    # capture must be a safe no-op when disabled
    observability.capture_client_error("something", {"url": "/x"})


def test_client_error_endpoint_accepts_report():
    resp = TestClient(app).post(
        "/api/client-errors",
        json={"message": "boom", "kind": "react", "url": "/trail", "stack": "at foo"},
    )
    assert resp.status_code == 204


def test_client_error_endpoint_bounds_message():
    resp = TestClient(app).post("/api/client-errors", json={"message": "x" * 2001})
    assert resp.status_code == 422
