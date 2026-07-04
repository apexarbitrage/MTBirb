"""The admin-token guard on the destructive / quota-burning ops endpoints (app/security.py).

Hermetic: exercises the guard logic directly, plus one TestClient check that the dependency is
actually wired to a gated route and fires *before* any DB/external call.
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import security
from app.main import app


class _FakeSettings:
    def __init__(self, token: str) -> None:
        self.admin_token = token


def test_disabled_when_token_unset(monkeypatch):
    # No ADMIN_TOKEN configured -> fail closed (503), even if a header is supplied.
    monkeypatch.setattr(security, "get_settings", lambda: _FakeSettings(""))
    with pytest.raises(HTTPException) as exc:
        security.require_admin(x_admin_token="anything")
    assert exc.value.status_code == 503


def test_rejects_wrong_token(monkeypatch):
    monkeypatch.setattr(security, "get_settings", lambda: _FakeSettings("s3cret"))
    with pytest.raises(HTTPException) as exc:
        security.require_admin(x_admin_token="nope")
    assert exc.value.status_code == 403


def test_rejects_missing_header(monkeypatch):
    monkeypatch.setattr(security, "get_settings", lambda: _FakeSettings("s3cret"))
    with pytest.raises(HTTPException) as exc:
        security.require_admin(x_admin_token="")
    assert exc.value.status_code == 403


def test_accepts_correct_token(monkeypatch):
    monkeypatch.setattr(security, "get_settings", lambda: _FakeSettings("s3cret"))
    assert security.require_admin(x_admin_token="s3cret") is None


def test_ops_endpoint_gated_by_default():
    """The gated route rejects (503, token unset) before touching the DB — proving the dependency
    is wired and runs first. `sync-taxonomy` takes no params, so nothing else can 4xx first."""
    client = TestClient(app)
    resp = client.post("/api/catalog/sync-taxonomy")
    assert resp.status_code == 503


def test_browse_endpoint_not_gated():
    """A read endpoint stays open (no admin token) — it must not accidentally require one.
    Missing required query params surface as 422, never 401/403/503 from the guard."""
    client = TestClient(app)
    resp = client.get("/api/catalog/species-search")
    assert resp.status_code not in (403, 503)
