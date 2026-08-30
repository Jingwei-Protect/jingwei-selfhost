"""Unit tests for ``core.rgb_offset``."""

from __future__ import annotations

import numpy as np
import pytest

from core.rgb_offset import _MAX_ABS_SHIFT, apply_rgb_offset


def _make_image(h: int = 64, w: int = 64, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)


def test_shape_dtype() -> None:
    img = _make_image()
    out = apply_rgb_offset(img, r_shift=(2, 0), b_shift=(-2, 0))
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_deterministic() -> None:
    img = _make_image(seed=1)
    a = apply_rgb_offset(img, r_shift=(3, 1), b_shift=(-3, -1))
    b = apply_rgb_offset(img, r_shift=(3, 1), b_shift=(-3, -1))
    assert np.array_equal(a, b)


def test_modifies_image() -> None:
    img = _make_image(seed=2)
    out = apply_rgb_offset(img, r_shift=(3, 0), b_shift=(-3, 0))
    assert not np.array_equal(out, img)


def test_zero_shift() -> None:
    img = _make_image(seed=3)
    out = apply_rgb_offset(img, r_shift=(0, 0), b_shift=(0, 0))
    assert np.array_equal(out, img)


def test_shift_clamping() -> None:
    img = _make_image(seed=4)
    a = apply_rgb_offset(img, r_shift=(10, 10), b_shift=(-10, -10))
    b = apply_rgb_offset(
        img,
        r_shift=(_MAX_ABS_SHIFT, _MAX_ABS_SHIFT),
        b_shift=(-_MAX_ABS_SHIFT, -_MAX_ABS_SHIFT),
    )
    assert np.array_equal(a, b)


def test_invalid_dtype_raises() -> None:
    img = _make_image().astype(np.float32)
    with pytest.raises(ValueError):
        apply_rgb_offset(img)
