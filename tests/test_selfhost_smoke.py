"""Smoke tests for the self-host API surface."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


def test_health() -> None:
    res = TestClient(app).get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body.get("ok") == "true"
    assert body.get("service") == "jingwei-selfhost"


def test_adv_protect_disabled_by_default() -> None:
    res = TestClient(app).get("/api/adv-protect/status")
    assert res.status_code == 200
    assert res.json().get("enabled") is False
