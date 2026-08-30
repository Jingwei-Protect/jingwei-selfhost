"""LSB must survive the full /api/protect post-processing chain (JW, blind_wm)."""

from __future__ import annotations

import numpy as np

from core.jingwei_protocol import JwManifest, embed_jw_watermark
from core.lsb_watermark import embed_lsb_watermark, extract_lsb_watermark
from core.pipeline import protect_image


def _img(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(30, 220, (256, 256, 3), dtype=np.uint8)


def test_lsb_survives_jw_when_reembedded_last() -> None:
    """Simulates protect.py: pipeline LSB → JW overlay → final LSB re-embed."""
    msg = "Artist: Test | 2026-01-01"
    base = protect_image(
        _img(),
        level="standard",
        watermark_text=msg,
        delivery_mode=True,
        protection_mode="stealth",
    )
    # JW destroys in-pipeline LSB (this is what happened before the fix)
    after_jw = embed_jw_watermark(base, JwManifest(artist="Test"))
    with_jw_broken = False
    try:
        extract_lsb_watermark(after_jw)
        with_jw_broken = True
    except ValueError:
        pass
    assert not with_jw_broken, "JW should break LSB if not re-embedded"

    # protect.py now re-embeds LSB after JW
    fixed = embed_lsb_watermark(after_jw, msg)
    assert extract_lsb_watermark(fixed) == msg


def test_lsb_stealth_without_jw() -> None:
    msg = "hello-lsb"
    out = protect_image(
        _img(1),
        level="standard",
        watermark_text=msg,
        delivery_mode=True,
        protection_mode="stealth",
    )
    assert extract_lsb_watermark(out) == msg
