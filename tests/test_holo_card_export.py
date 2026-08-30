"""Holo-card MP4 export — CSS frames in, downloadable clip out."""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from core.holo_card_export import (
    HOLO_CLIP_FPS,
    HOLO_CLIP_FRAMES,
    HoloCaptureError,
    encode_holo_mp4,
    export_holo_mp4_from_image,
    fit_holo_face,
)


def test_holo_clip_is_at_least_six_seconds() -> None:
    assert HOLO_CLIP_FRAMES / HOLO_CLIP_FPS >= 6.0


def _solid(h: int, w: int, color: tuple[int, int, int]) -> np.ndarray:
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = color
    return img


def test_fit_holo_face_shrinks_long_edge() -> None:
    out = fit_holo_face(_solid(2000, 1200, (20, 40, 80)), max_edge=800)
    assert max(out.shape[:2]) == 800
    assert out.dtype == np.uint8


def test_encode_holo_mp4_returns_mp4_bytes() -> None:
    frames = [_solid(80, 120, (30, 60, 90)), _solid(80, 120, (90, 40, 20))]
    blob = encode_holo_mp4(frames, fps=8)
    assert blob[:8]  # non-empty
    assert blob[4:8] == b"ftyp" or blob[:4] == b"\x00\x00\x00"


def test_export_holo_mp4_uses_injected_capture(tmp_path: Path) -> None:
    face = _solid(96, 128, (12, 80, 140))
    seen: list[Path] = []

    def fake_capture(image_path: Path, *, n_frames: int) -> list[np.ndarray]:
        seen.append(image_path)
        assert image_path.is_file()
        assert n_frames == 4
        return [_solid(64, 80, (i * 20, 40, 80)) for i in range(n_frames)]

    blob = export_holo_mp4_from_image(face, n_frames=4, fps=8, capture_frames=fake_capture)
    assert len(seen) == 1
    assert len(blob) > 32


def test_export_holo_mp4_maps_selenium_missing() -> None:
    def boom(image_path: Path, *, n_frames: int) -> list[np.ndarray]:
        raise RuntimeError("需要 selenium：pip install selenium")

    with pytest.raises(HoloCaptureError, match="selenium"):
        export_holo_mp4_from_image(_solid(96, 128, (8, 8, 8)), capture_frames=boom)


def test_holo_clip_route_returns_mp4(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from api.main import app

    def fake_export(image: np.ndarray, **kwargs: object) -> bytes:
        assert image.shape[2] == 3
        return b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64

    monkeypatch.setattr("api.routes.protect.export_holo_mp4_from_image", fake_export)
    buf = io.BytesIO()
    Image.fromarray(_solid(80, 96, (40, 50, 60))).save(buf, format="PNG")
    client = TestClient(app)
    res = client.post(
        "/api/protect/holo-clip",
        files={"image": ("p.png", buf.getvalue(), "image/png")},
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("video/mp4")
    assert res.content.startswith(b"\x00\x00\x00\x18ftyp")


def test_holo_clip_route_reports_missing_chrome(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from api.error_codes import HOLO_CAPTURE_UNAVAILABLE
    from api.main import app

    def boom(image: np.ndarray, **kwargs: object) -> bytes:
        raise HoloCaptureError("需要 selenium：pip install selenium")

    monkeypatch.setattr("api.routes.protect.export_holo_mp4_from_image", boom)
    buf = io.BytesIO()
    Image.fromarray(_solid(80, 96, (40, 50, 60))).save(buf, format="PNG")
    client = TestClient(app)
    res = client.post(
        "/api/protect/holo-clip",
        files={"image": ("p.png", buf.getvalue(), "image/png")},
    )
    assert res.status_code == 503
    body = res.json()
    assert body["ok"] is False
    assert body["error_code"] == HOLO_CAPTURE_UNAVAILABLE
