"""Feature flag gates for /api/adv-protect."""

from __future__ import annotations

import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from api.main import app
from api.error_codes import ADV_FEATURE_DISABLED


def _tiny_png() -> bytes:
    arr = np.zeros((96, 96, 3), dtype=np.uint8)
    arr[:, :] = (40, 80, 120)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_status_reports_disabled_by_default(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ENABLE_ADV_PROTECT", "0")
    res = client.get("/api/adv-protect/status")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["enabled"] is False


def test_post_forbidden_when_disabled(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ENABLE_ADV_PROTECT", "0")
    res = client.post(
        "/api/adv-protect",
        files={"image": ("t.png", _tiny_png(), "image/png")},
        data={"steps": "1", "eps": "0.06"},
    )
    assert res.status_code == 403
    body = res.json()
    assert body["ok"] is False
    assert body["error_code"] == ADV_FEATURE_DISABLED


def test_status_enabled_flag(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ENABLE_ADV_PROTECT", "1")
    res = client.get("/api/adv-protect/status")
    assert res.status_code == 200
    assert res.json()["enabled"] is True
