"""JW must remain verifiable after stealth pipeline + relief signature."""

from __future__ import annotations

import base64
import io

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image


def _flat_illustration() -> np.ndarray:
    flat = np.zeros((900, 900, 3), dtype=np.uint8)
    flat[:, :, 0] = 180
    flat[200:700, 150:750] = [240, 230, 220]
    flat[100:500, 100:500] = [200, 120, 80]
    return flat


def test_stealth_signature_only_does_not_enable_surface_stack() -> None:
    from api.routes.protect import _wants_stealth_surface

    assert _wants_stealth_surface(
        mode="stealth",
        is_ultimate=False,
        blur_bar_enabled=False,
        emboss_enabled=False,
        displacement_enabled=False,
        face_emboss_enabled=False,
    ) is False


def test_protect_balanced_jw_with_relief_signature_on_flat_art() -> None:
    from api.main import app

    buf = io.BytesIO()
    Image.fromarray(_flat_illustration()).save(buf, format="PNG")
    client = TestClient(app)
    res = client.post(
        "/api/protect",
        files={"image": ("flat.png", buf.getvalue(), "image/png")},
        data={
            "mode": "stealth",
            "watermark_text": "",
            "signature_text": "JW",
            "signature_position": "bottom_right",
            "artist": "JW",
            "embed_metadata": "false",
            "output_format": "png",
            "jw_enabled": "true",
            "jw_creation": "OC",
            "jw_restrictions": "NO-TR,NO-ED",
            "jw_badge": "false",
            "jw_footer_strip": "true",
        },
    )
    body = res.json()
    assert body.get("ok") is True, body
    assert body.get("jw_applied") is True, body.get("status")
    assert body.get("jw_embed_method") in ("invisible", "lsb"), body
    raw = base64.b64decode(body["image"].split(",", 1)[1])
    verify = client.post(
        "/api/verify",
        files={"image": ("out.png", raw, "image/png")},
    ).json()
    assert verify["jw"]["found"], verify["jw"]
