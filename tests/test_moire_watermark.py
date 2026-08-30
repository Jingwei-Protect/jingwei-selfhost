"""Unit tests for core.moire_watermark."""

from __future__ import annotations

import numpy as np

from core.moire_watermark import (
    _generate_visible_moire_field,
    apply_moire_watermark,
)


def _solid(h: int, w: int, rgb: tuple[int, int, int]) -> np.ndarray:
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = rgb
    return img


def test_output_shape_and_dtype() -> None:
    img = _solid(128, 160, (140, 150, 160))
    out = apply_moire_watermark(img, opacity=0.14, seed=1)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_opacity_zero_returns_copy() -> None:
    img = _solid(64, 64, (100, 110, 120))
    out = apply_moire_watermark(img, opacity=0.0)
    np.testing.assert_array_equal(out, img)


def test_swirl_and_wave_change_pixels() -> None:
    img = _solid(120, 140, (180, 190, 200))
    for mode in ("swirl", "wave"):
        out = apply_moire_watermark(img, mode=mode, opacity=0.16, seed=2)
        assert np.any(out != img)


def test_deterministic_with_seed() -> None:
    img = _solid(96, 96, (130, 140, 150))
    a = apply_moire_watermark(img, opacity=0.15, seed=99)
    b = apply_moire_watermark(img, opacity=0.15, seed=99)
    np.testing.assert_array_equal(a, b)


def test_author_signature_adds_change() -> None:
    img = _solid(160, 200, (170, 175, 180))
    bare = apply_moire_watermark(img, mode="swirl", opacity=0.16, seed=3)
    signed = apply_moire_watermark(
        img, mode="swirl", opacity=0.16, seed=3, author_text="Jingwei",
    )
    assert np.any(signed != bare)


def test_moire_field_normalized() -> None:
    rng = np.random.default_rng(0)
    field = _generate_visible_moire_field(
        80, 100, mode="swirl", frequency=0.5,
        swirl_strength=1.2, wave_amplitude=10.0, rng=rng,
    )
    assert field.shape == (80, 100)
    assert float(np.max(np.abs(field))) <= 1.0 + 1e-5
