"""DWT standalone layer is separate from JW; protect API skips DWT when JW is enabled."""

from __future__ import annotations

import io

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from core.dwt_watermark import embed_dwt_watermark, extract_dwt_watermark
from core.jingwei_protocol import (
    JwManifest,
    apply_jw_visible_badge,
    embed_jw_watermark,
    encode_jw_payload,
    parse_creation,
    restrictions_from_ids,
)
from core.pipeline import protect_image


def _img() -> np.ndarray:
    rng = np.random.default_rng(3)
    return rng.integers(30, 220, (512, 512, 3), dtype=np.uint8)


def test_legacy_stack_jw_then_dwt_still_roundtrip() -> None:
    """Historical double-stack (JW + independent DWT) remains decodable for old exports."""
    base = protect_image(
        _img(),
        level="standard",
        delivery_mode=True,
        protection_mode="stealth",
        dwt_payload="",
        watermark_text="",
    )
    manifest = JwManifest(
        creation=parse_creation("OC"),
        restrictions=restrictions_from_ids(["NO-TR", "NO-ED", "NO-RM"]),
        visible_badge=True,
        artist="Jingwei",
    )
    dwt_text = encode_jw_payload(manifest)
    after_jw = embed_jw_watermark(base, manifest)
    after_dwt = embed_dwt_watermark(after_jw, payload_text=dwt_text)
    out = apply_jw_visible_badge(after_dwt, manifest)

    dwt = extract_dwt_watermark(out)
    assert dwt.get("payload_text") == dwt_text
    assert dwt.get("confidence", 0) >= 0.60


def test_protect_api_jw_enabled_skips_standalone_dwt() -> None:
    from api.main import app

    buf = io.BytesIO()
    Image.fromarray(_img()).save(buf, format="PNG")
    client = TestClient(app)
    res = client.post(
        "/api/protect",
        files={"image": ("t.png", buf.getvalue(), "image/png")},
        data={
            "mode": "stealth",
            "artist": "Jingwei",
            "embed_metadata": "false",
            "output_format": "png",
            "jw_enabled": "true",
            "jw_creation": "OC",
            "dwt_payload": "SHOULD_NOT_WRITE",
        },
    )
    body = res.json()
    assert body.get("ok") is True
    assert body.get("jw_applied") is True
    assert body.get("dwt_applied") is False

