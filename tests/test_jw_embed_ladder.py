"""JW texture-first embed ladder, LSB fallback, and JW/DWT mutual exclusion."""

from __future__ import annotations

import io

import cv2
import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from core.jingwei_protocol import (
    JwEmbedPriority,
    JwManifest,
    _FLAT_RATIO_CHROMA_BLOCK,
    _FLAT_RATIO_FULL_BLOCK,
    build_jw_embed_ladder,
    embed_jw_lsb_fallback,
    embed_jw_verifiable,
    estimate_flat_ratio,
    extract_jw_for_verify,
    extract_jw_from_lsb,
    extract_jw_watermark,
    jw_write_hint_for_image,
    parse_creation,
    restrictions_from_ids,
)


def _flat_illustration() -> np.ndarray:
    flat = np.zeros((900, 900, 3), dtype=np.uint8)
    flat[:, :, 0] = 180
    flat[200:700, 150:750] = [240, 230, 220]
    flat[100:500, 100:500] = [200, 120, 80]
    return flat


def _interior_flat_max_delta(original: np.ndarray, protected: np.ndarray, *, margin: int = 20) -> int:
    """Max channel delta on eroded uniform regions (ignores colour-block edges)."""
    h, w = original.shape[:2]
    ph, pw = protected.shape[:2]
    h = min(h, ph)
    w = min(w, pw)
    orig = original[:h, :w]
    prot = protected[:h, :w]
    diff = np.abs(prot.astype(np.int16) - orig.astype(np.int16))
    k = margin * 2 + 1
    kernel = np.ones((k, k), dtype=np.uint8)
    best = 0
    for color in np.unique(orig.reshape(-1, 3), axis=0)[:12]:
        mask = np.all(orig == color, axis=2).astype(np.uint8)
        interior = cv2.erode(mask, kernel).astype(bool)
        if interior.sum() < 500:
            continue
        best = max(best, int(diff[interior].max()))
    return best


def test_flat_ratio_detects_illustration() -> None:
    ratio = estimate_flat_ratio(_flat_illustration())
    assert ratio >= 0.55


def test_auto_ladder_on_flat_art_has_no_y_ll2() -> None:
    ratio = estimate_flat_ratio(_flat_illustration())
    ladder = build_jw_embed_ladder(ratio, JwEmbedPriority.AUTO)
    names = [p.name for p in ladder]
    assert "y_ll2" not in names
    assert "full" not in names
    assert "texture_boost" not in names
    assert "texture_max" not in names
    assert names == ["stealth", "y_boost"]


def _mixed_illustration() -> np.ndarray:
    """Half flat / half noise — flat_ratio in mixed band (~0.35–0.55)."""
    img = np.zeros((512, 512, 3), dtype=np.uint8)
    img[:, :256] = [180, 200, 220]
    rng = np.random.default_rng(0)
    img[:, 256:] = rng.integers(0, 256, (512, 256, 3), dtype=np.uint8)
    return img


def test_auto_ladder_on_mixed_art_caps_texture_max() -> None:
    mixed = _mixed_illustration()
    ratio = estimate_flat_ratio(mixed)
    assert _FLAT_RATIO_FULL_BLOCK <= ratio < _FLAT_RATIO_CHROMA_BLOCK
    ladder = build_jw_embed_ladder(ratio, JwEmbedPriority.AUTO)
    names = [p.name for p in ladder]
    assert names == ["stealth", "y_boost", "texture_boost"]
    assert "texture_max" not in names


def test_auto_ladder_on_rich_art_includes_cr_texture() -> None:
    rich = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
    ratio = estimate_flat_ratio(rich)
    ladder = build_jw_embed_ladder(ratio, JwEmbedPriority.AUTO)
    names = [p.name for p in ladder]
    assert "cr_texture" in names
    assert "y_ll2" not in names


def test_flat_art_lsb_fallback_decodes() -> None:
    manifest = JwManifest(
        creation=parse_creation("OC"),
        restrictions=restrictions_from_ids(["NO-TR", "NO-ED"]),
        artist="FlatTest",
    )
    img = embed_jw_lsb_fallback(_flat_illustration(), manifest)
    hit = extract_jw_from_lsb(img)
    assert hit and hit["found"]
    assert hit["channel"] == "lsb"


def test_lsb_fallback_embeds_and_reads_timestamp() -> None:
    manifest = JwManifest(
        creation=parse_creation("OC"),
        restrictions=restrictions_from_ids(["NO-TR"]),
        artist="TimeTest",
    )
    from core.jingwei_protocol import _format_jw_protected_at

    ts = 1_700_000_000
    img = embed_jw_lsb_fallback(_flat_illustration(), manifest, embed_timestamp=ts)
    hit = extract_jw_from_lsb(img)
    assert hit and hit["found"]
    assert hit.get("timestamp") == ts
    assert hit.get("protected_at") == _format_jw_protected_at(ts)


def test_auto_embed_on_flat_skips_freq_uses_lsb() -> None:
    manifest = JwManifest(
        creation=parse_creation("OC"),
        restrictions=restrictions_from_ids(["NO-TR", "NO-ED"]),
        artist="FlatTest",
    )
    img, applied, tier = embed_jw_verifiable(
        _flat_illustration(), manifest, priority=JwEmbedPriority.AUTO,
    )
    assert applied is False
    assert tier is None
    img2 = embed_jw_lsb_fallback(img, manifest)
    hit = extract_jw_from_lsb(img2)
    assert hit and hit["found"]
    assert _interior_flat_max_delta(_flat_illustration(), img2) <= 2


def test_extract_jw_for_verify_lsb_before_freq() -> None:
    manifest = JwManifest(
        creation=parse_creation("OC"),
        restrictions=restrictions_from_ids(["NO-TR"]),
        artist="FastVerify",
    )
    img = embed_jw_lsb_fallback(_flat_illustration(), manifest, embed_timestamp=1_700_000_000)
    hit = extract_jw_for_verify(img)
    assert hit["found"]
    assert hit.get("channel") == "lsb"


def test_extract_jw_for_verify_skips_recovery_without_decode_hint() -> None:
    hit = extract_jw_for_verify(_flat_illustration())
    assert not hit.get("found")
    assert not hit.get("decode_hint")
    assert not hit.get("recovered")


def test_jw_write_hint_flat_kind() -> None:
    hint = jw_write_hint_for_image(_flat_illustration())
    assert hint["kind"] == "flat"
    assert "大色块" in hint["summary"]


def test_protect_api_jw_skips_standalone_dwt() -> None:
    from api.main import app

    buf = io.BytesIO()
    Image.fromarray(_flat_illustration()).save(buf, format="PNG")
    client = TestClient(app)
    res = client.post(
        "/api/protect",
        files={"image": ("flat.png", buf.getvalue(), "image/png")},
        data={
            "mode": "stealth",
            "artist": "Jingwei",
            "embed_metadata": "false",
            "output_format": "png",
            "jw_enabled": "true",
            "jw_creation": "OC",
            "jw_restrictions": "NO-TR,NO-ED",
            "dwt_payload": "SHOULD_NOT_WRITE",
        },
    )
    body = res.json()
    assert body.get("ok") is True
    assert body.get("jw_applied") is True
    assert body.get("dwt_applied") is False
    assert body.get("jw_embed_priority") == "auto"


def test_protect_jw_hint_endpoint() -> None:
    from api.main import app

    buf = io.BytesIO()
    Image.fromarray(_flat_illustration()).save(buf, format="PNG")
    client = TestClient(app)
    res = client.post(
        "/api/protect/jw-hint",
        files={"image": ("flat.png", buf.getvalue(), "image/png")},
    )
    body = res.json()
    assert body.get("ok") is True
    assert body.get("kind") == "flat"
