"""Unit tests for core/luminance_inversion.py."""

from __future__ import annotations

import numpy as np
import pytest

from core.luminance_inversion import apply_luminance_inversion


@pytest.fixture()
def gray_image() -> np.ndarray:
    """A grayscale image stored as RGB (R=G=B)."""
    rng = np.random.default_rng(0)
    gray = rng.integers(20, 230, (200, 200), dtype=np.uint8)
    return np.stack([gray, gray, gray], axis=-1)


@pytest.fixture()
def color_image() -> np.ndarray:
    rng = np.random.default_rng(1)
    return rng.integers(0, 256, (200, 200, 3), dtype=np.uint8)


class TestLuminanceInversion:
    def test_shape_dtype(self, gray_image: np.ndarray) -> None:
        out = apply_luminance_inversion(gray_image)
        assert out.shape == gray_image.shape
        assert out.dtype == np.uint8

    def test_deterministic(self, gray_image: np.ndarray) -> None:
        a = apply_luminance_inversion(gray_image, seed=42)
        b = apply_luminance_inversion(gray_image, seed=42)
        np.testing.assert_array_equal(a, b)

    def test_different_seeds(self, gray_image: np.ndarray) -> None:
        a = apply_luminance_inversion(gray_image, seed=1)
        b = apply_luminance_inversion(gray_image, seed=2)
        assert not np.array_equal(a, b)

    def test_modifies_image(self, gray_image: np.ndarray) -> None:
        out = apply_luminance_inversion(gray_image)
        assert not np.array_equal(out, gray_image)

    def test_works_on_color(self, color_image: np.ndarray) -> None:
        out = apply_luminance_inversion(color_image)
        assert out.shape == color_image.shape
        assert not np.array_equal(out, color_image)

    def test_strength_clamping(self, gray_image: np.ndarray) -> None:
        out_low = apply_luminance_inversion(gray_image, strength=1)
        out_high = apply_luminance_inversion(gray_image, strength=100)
        assert out_low.dtype == np.uint8
        assert out_high.dtype == np.uint8

    def test_bad_dtype_raises(self) -> None:
        bad = np.zeros((100, 100, 3), dtype=np.float32)
        with pytest.raises(ValueError, match="uint8"):
            apply_luminance_inversion(bad)

    def test_too_small_raises(self) -> None:
        tiny = np.zeros((10, 10, 3), dtype=np.uint8)
        with pytest.raises(ValueError, match="32"):
            apply_luminance_inversion(tiny)
