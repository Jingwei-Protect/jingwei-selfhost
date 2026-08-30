"""ICC-aware upload decode and stealth surface gating."""

from __future__ import annotations

import numpy as np
from PIL import Image

from core.color_profile import decode_upload_pil
from core.visible_preview import compute_stealth_surface, render_visible_preview


def _flat_blue() -> np.ndarray:
    img = np.zeros((128, 128, 3), dtype=np.uint8)
    img[:, :, 2] = 220
    return img


def test_decode_upload_pil_rgb_passthrough() -> None:
    pil = Image.fromarray(_flat_blue(), "RGB")
    rgb, alpha = decode_upload_pil(pil)
    assert alpha is None
    assert rgb.shape == (128, 128, 3)
    assert np.allclose(rgb[0, 0], [0, 0, 220])


def test_decode_upload_pil_rgba_splits_alpha() -> None:
    rgba = np.dstack([_flat_blue(), np.full((128, 128), 200, dtype=np.uint8)])
    pil = Image.fromarray(rgba, "RGBA")
    rgb, alpha = decode_upload_pil(pil)
    assert alpha is not None and alpha.shape == (128, 128)
    assert rgb.shape == (128, 128, 3)


def test_compute_stealth_surface_signature_only_false() -> None:
    assert not compute_stealth_surface(mode="stealth")


def test_compute_stealth_surface_displacement_requires_text() -> None:
    assert not compute_stealth_surface(
        mode="stealth", displacement_enabled=True, displacement_text="",
    )
    assert compute_stealth_surface(
        mode="stealth", displacement_enabled=True, displacement_text="JW",
    )


def test_render_visible_preview_signature_skips_stealth_stack() -> None:
    """Relief signature alone must not run the anti-AI surface stack."""
    img = _flat_blue()
    out = render_visible_preview(img, signature_text="Sig")
    diff = np.abs(out.astype(np.int16) - img.astype(np.int16))
    assert diff.max() <= 45
