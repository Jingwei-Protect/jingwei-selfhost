"""tests/test_semantic_injection.py — semantic injection patch unit tests."""

from __future__ import annotations

import numpy as np

from core.semantic_injection import apply_semantic_injection


def _synth(h: int = 64, w: int = 64) -> np.ndarray:
    return np.random.default_rng(0).integers(0, 256, (h, w, 3), dtype=np.uint8)


def test_shape_dtype():
    img = _synth()
    out = apply_semantic_injection(img, opacity=0.25, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_deterministic():
    img = _synth()
    a = apply_semantic_injection(img, opacity=0.25, seed=42)
    b = apply_semantic_injection(img, opacity=0.25, seed=42)
    assert np.array_equal(a, b)


def test_custom_keywords():
    img = _synth()
    out = apply_semantic_injection(img, keywords=["Test"], opacity=0.25, seed=42)
    assert out.shape == img.shape


def test_opacity_clamped():
    img = _synth()
    apply_semantic_injection(img, opacity=0.05, seed=42)
    apply_semantic_injection(img, opacity=0.50, seed=42)


def test_patches_modify_image():
    img = _synth()
    out = apply_semantic_injection(img, opacity=0.25, seed=42)
    assert not np.array_equal(out, img)
