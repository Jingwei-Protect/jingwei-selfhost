"""Unit tests for ``core.perlin_structural_noise``."""

from __future__ import annotations

import numpy as np
import pytest

from core.perlin_structural_noise import apply_perlin_structural_noise


def _make_image(h: int = 128, w: int = 128, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(30, 220, size=(h, w, 3), dtype=np.uint8)


def test_shape_dtype() -> None:
    img = _make_image()
    out = apply_perlin_structural_noise(img, strength=0.4, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_deterministic() -> None:
    img = _make_image(seed=1)
    a = apply_perlin_structural_noise(img, strength=0.4, seed=42)
    b = apply_perlin_structural_noise(img, strength=0.4, seed=42)
    assert np.array_equal(a, b)


def test_different_seeds() -> None:
    img = _make_image(seed=2)
    a = apply_perlin_structural_noise(img, seed=1)
    b = apply_perlin_structural_noise(img, seed=2)
    assert not np.array_equal(a, b)


def test_modifies_image() -> None:
    img = _make_image(seed=3)
    out = apply_perlin_structural_noise(img, strength=0.5, seed=42)
    assert not np.array_equal(out, img)


def test_high_psnr() -> None:
    """Perlin noise at moderate strength should preserve quality — PSNR > 35 dB."""
    img = _make_image(h=256, w=256, seed=5)
    out = apply_perlin_structural_noise(img, strength=0.4, seed=42)
    mse = float(np.mean((img.astype(float) - out.astype(float)) ** 2))
    if mse > 0:
        psnr = 10.0 * np.log10(255.0 ** 2 / mse)
        assert psnr > 35.0, f"PSNR too low: {psnr:.1f} dB"


def test_strength_clamping_low() -> None:
    img = _make_image(seed=6)
    a = apply_perlin_structural_noise(img, strength=0.0, seed=42)
    b = apply_perlin_structural_noise(img, strength=0.1, seed=42)
    assert np.array_equal(a, b), "strength below 0.1 should clamp to 0.1"


def test_strength_clamping_high() -> None:
    img = _make_image(seed=7)
    a = apply_perlin_structural_noise(img, strength=5.0, seed=42)
    b = apply_perlin_structural_noise(img, strength=1.0, seed=42)
    assert np.array_equal(a, b), "strength above 1.0 should clamp to 1.0"


def test_higher_strength_more_change() -> None:
    img = _make_image(h=256, w=256, seed=8)
    lo = apply_perlin_structural_noise(img, strength=0.2, seed=42)
    hi = apply_perlin_structural_noise(img, strength=0.8, seed=42)
    diff_lo = float(np.mean(np.abs(img.astype(float) - lo.astype(float))))
    diff_hi = float(np.mean(np.abs(img.astype(float) - hi.astype(float))))
    assert diff_hi > diff_lo, "Higher strength should produce more change"


def test_invalid_dtype_raises() -> None:
    img = _make_image().astype(np.float32)
    with pytest.raises(ValueError):
        apply_perlin_structural_noise(img)


def test_invalid_shape_raises() -> None:
    img = np.zeros((128, 128), dtype=np.uint8)
    with pytest.raises(ValueError):
        apply_perlin_structural_noise(img)


def test_small_image_raises() -> None:
    img = np.zeros((16, 16, 3), dtype=np.uint8)
    with pytest.raises(ValueError):
        apply_perlin_structural_noise(img)


def test_rectangular_image() -> None:
    img = _make_image(h=200, w=100, seed=10)
    out = apply_perlin_structural_noise(img, strength=0.4, seed=42)
    assert out.shape == (200, 100, 3)
    assert out.dtype == np.uint8
