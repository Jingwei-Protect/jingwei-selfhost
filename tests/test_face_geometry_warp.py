"""Unit tests for ``core.face_geometry_warp``.

This module is now a pure geometric attack (the asymmetric hue shift has been
removed in favour of :mod:`core.face_blob_disruption`).
"""

from __future__ import annotations

import numpy as np
import pytest

from core.face_geometry_warp import apply_face_geometry_warp


def _make_image(h: int = 128, w: int = 128, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(30, 220, size=(h, w, 3), dtype=np.uint8)


def test_shape_dtype() -> None:
    img = _make_image()
    out = apply_face_geometry_warp(img, warp_amplitude=2.5, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_deterministic() -> None:
    img = _make_image(seed=1)
    a = apply_face_geometry_warp(img, warp_amplitude=2.5, seed=42)
    b = apply_face_geometry_warp(img, warp_amplitude=2.5, seed=42)
    assert np.array_equal(a, b)


def test_different_seeds() -> None:
    img = _make_image(seed=2)
    a = apply_face_geometry_warp(img, seed=1, allow_fallback=True)
    b = apply_face_geometry_warp(img, seed=2, allow_fallback=True)
    assert not np.array_equal(a, b)


def test_modifies_image() -> None:
    img = _make_image(seed=3)
    out = apply_face_geometry_warp(
        img, warp_amplitude=3.0, seed=42, allow_fallback=True,
    )
    assert not np.array_equal(out, img)


def test_high_psnr_low_visual_impact() -> None:
    """Warp should be subtle — PSNR should stay above 20 dB on synthetic image."""
    img = _make_image(h=256, w=256, seed=5)
    out = apply_face_geometry_warp(
        img, warp_amplitude=2.5, seed=42, allow_fallback=True,
    )
    mse = float(np.mean((img.astype(float) - out.astype(float)) ** 2))
    if mse > 0:
        psnr = 10.0 * np.log10(255.0 ** 2 / mse)
        assert psnr > 20.0, f"PSNR too low: {psnr:.1f} dB"


def test_amplitude_clamping() -> None:
    img = _make_image(seed=6)
    a = apply_face_geometry_warp(
        img, warp_amplitude=100.0, seed=42, allow_fallback=True,
    )
    b = apply_face_geometry_warp(
        img, warp_amplitude=6.0, seed=42, allow_fallback=True,
    )
    assert np.array_equal(a, b)


def test_no_fallback_leaves_illustration_unchanged() -> None:
    img = _make_image(h=400, w=300, seed=7)
    out = apply_face_geometry_warp(img, seed=42, allow_fallback=False)
    assert np.array_equal(out, img)


def test_invalid_dtype_raises() -> None:
    img = _make_image().astype(np.float32)
    with pytest.raises(ValueError):
        apply_face_geometry_warp(img)
