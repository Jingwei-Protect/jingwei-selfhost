"""Screenshot-recovery tests for JW / DWT extractors.

What the recovery wrapper can do
--------------------------------
Reliable rescue:
  - Pure JPEG re-encode at any quality (Q60–Q100) — no recovery needed.
  - 1-pixel crop offset (typical snipping-tool border bleed) — rescued by
    the byte-aligned cyclic-shift + fuzzy-marker decode in ``_decode_bits``.

Best-effort improvement only:
  - 2-7 pixel crop offsets — confidence rises but bit errors stay too high
    for a checksum-pass.
  - Image resize (any scale ≠ 1.0) — the LL2 wavelet grid changes and the
    quantisation lattice is irrecoverable from a single embedding.

Real screenshots typically combine resize + JPEG, which destroys this class
of watermark. To survive that, the embedding side would need
multi-scale redundancy or a synchronisation pattern — out of scope here.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from core.dwt_watermark import embed_dwt_watermark
from core.jingwei_protocol import (
    JW_FLAG_NO_AI_EDIT,
    JW_FLAG_NO_TRAINING,
    JwManifest,
    embed_jw_watermark,
)
from core.screenshot_recovery import (
    extract_dwt_with_recovery,
    extract_jw_with_recovery,
)


def _make_test_image(seed: int = 17, h: int = 640, w: int = 640) -> np.ndarray:
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    img = np.stack(
        [(y / h) * 180 + 40, ((x + y) / (h + w)) * 200 + 30, (x / w) * 160 + 50],
        axis=-1,
    )
    return np.clip(img + rng.normal(0, 6, img.shape), 0, 255).astype(np.uint8)


def _manifest() -> JwManifest:
    m = JwManifest(artist="ScreenshotTest")
    m.set_restriction(JW_FLAG_NO_AI_EDIT, True)
    m.set_restriction(JW_FLAG_NO_TRAINING, True)
    return m


def _jpeg(img: np.ndarray, q: int) -> np.ndarray:
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    _, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, q])
    return cv2.cvtColor(cv2.imdecode(buf, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)


# ─── Sanity: wrapper doesn't regress the clean case ────────────────────

def test_recovery_does_not_regress_clean_image() -> None:
    img = _make_test_image()
    protected = embed_jw_watermark(img, _manifest())
    out = extract_jw_with_recovery(protected)
    assert out.get("found"), "Clean JW must still extract through the wrapper"
    assert out.get("artist") == "ScreenshotTest"
    assert not out.get("recovered", False), (
        "Clean image should not trigger the scale-sweep recovery path"
    )


def test_recovery_does_not_false_positive_on_unmarked() -> None:
    img = _make_test_image(seed=99)
    out = extract_jw_with_recovery(img)
    assert not out.get("found"), (
        f"False positive on unmarked image! per_channel={out.get('per_channel')}"
    )


# ─── JPEG re-encode survives without help ──────────────────────────────

def test_jpeg_q70_survives_natively() -> None:
    protected = embed_jw_watermark(_make_test_image(), _manifest())
    attacked = _jpeg(protected, 70)
    out = extract_jw_with_recovery(attacked)
    assert out.get("found"), f"JPEG Q70 should survive: {out}"
    assert out.get("artist") == "ScreenshotTest"


def test_jpeg_q60_survives_natively() -> None:
    protected = embed_jw_watermark(_make_test_image(), _manifest())
    attacked = _jpeg(protected, 60)
    out = extract_jw_with_recovery(attacked)
    assert out.get("found"), f"JPEG Q60 should survive: {out}"


# ─── 1-pixel crop is the headline recovery case ────────────────────────

def test_one_pixel_crop_detects_jw_marker() -> None:
    """Snipping-tool bleed (1px from top-left) breaks the DCT layer's 8×8
    grid, but chroma LL2 still carries ~90 % correct bits.

    The fuzzy marker + cyclic-shift fallback inside ``_decode_bits`` must at
    least detect *that* a JW watermark exists. Without an ECC layer the
    artist / restriction bytes still carry some bit errors, so we don't
    assert their exact recovery here.
    """
    protected = embed_jw_watermark(_make_test_image(), _manifest())
    attacked = _jpeg(protected[1:, 1:], 95)
    out = extract_jw_with_recovery(attacked)
    assert out.get("found"), f"1-pixel crop rescue failed: {out}"
    assert out.get("badge_text", "").startswith("JW")


# ─── DWT round-trip through the recovery wrapper ───────────────────────

def test_dwt_recovery_wrapper_pure_jpeg() -> None:
    img = _make_test_image()
    protected = embed_dwt_watermark(img, payload_text="DWT_SCRSHOT")
    out = extract_dwt_with_recovery(_jpeg(protected, 70))
    assert out.get("payload_text") == "DWT_SCRSHOT", out
    assert out.get("confidence", 0) >= 0.60


# ─── Real screenshot resilience via the L4 block-DC layer ──────────────

@pytest.mark.parametrize("scale,jpeg_q", [
    (0.95, 90),
    (0.85, 80),
    (0.75, 75),
    (0.60, 70),
    (1.10, 85),
    (1.25, 80),
])
def test_jw_survives_screenshot_via_block_dc(scale: float, jpeg_q: int) -> None:
    """Combined resize + JPEG (real screenshot proxy) must extract through L4."""
    protected = embed_jw_watermark(_make_test_image(), _manifest())
    h, w = protected.shape[:2]
    scaled = cv2.resize(
        protected,
        (int(round(w * scale)), int(round(h * scale))),
        interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC,
    )
    attacked = _jpeg(scaled, jpeg_q)
    out = extract_jw_with_recovery(attacked)
    assert out.get("found"), (
        f"L4 failed to rescue scale={scale} JPEG={jpeg_q}: "
        f"per_channel={out.get('per_channel')}"
    )
    assert out.get("artist") == "ScreenshotTest"
    # The block-DC layer should be the dominant decoder here.
    assert out.get("channel") == "bdc" or out.get("per_channel", {}).get("bdc", 0) > 0.5
