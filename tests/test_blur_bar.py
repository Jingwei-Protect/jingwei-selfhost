"""Unit tests for core/blur_bar.py."""

from __future__ import annotations

import numpy as np
import pytest

from core.blur_bar import apply_blur_bar


@pytest.fixture()
def rgb_image() -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.integers(0, 256, (300, 400, 3), dtype=np.uint8)


class TestApplyBlurBar:
    def test_shape_dtype_preserved(self, rgb_image: np.ndarray) -> None:
        out = apply_blur_bar(rgb_image, position="waist")
        assert out.shape == rgb_image.shape
        assert out.dtype == np.uint8

    def test_deterministic(self, rgb_image: np.ndarray) -> None:
        a = apply_blur_bar(rgb_image, position="waist", seed=99)
        b = apply_blur_bar(rgb_image, position="waist", seed=99)
        np.testing.assert_array_equal(a, b)

    def test_modifies_image(self, rgb_image: np.ndarray) -> None:
        out = apply_blur_bar(rgb_image, position="waist")
        assert not np.array_equal(out, rgb_image)

    def test_below_face_position(self, rgb_image: np.ndarray) -> None:
        out = apply_blur_bar(rgb_image, position="below_face")
        assert out.shape == rgb_image.shape
        assert not np.array_equal(out, rgb_image)

    def test_bottom_position(self, rgb_image: np.ndarray) -> None:
        out = apply_blur_bar(rgb_image, position="bottom")
        assert out.shape == rgb_image.shape

    def test_custom_position(self, rgb_image: np.ndarray) -> None:
        out = apply_blur_bar(
            rgb_image, position="custom", x_ratio=0.1, y_ratio=0.3
        )
        assert out.shape == rgb_image.shape

    def test_with_text(self, rgb_image: np.ndarray) -> None:
        out = apply_blur_bar(rgb_image, text="© Artist", position="waist")
        assert out.shape == rgb_image.shape

    def test_sigma_clamping_low(self, rgb_image: np.ndarray) -> None:
        out = apply_blur_bar(rgb_image, blur_sigma=1, position="waist")
        assert out.dtype == np.uint8

    def test_sigma_clamping_high(self, rgb_image: np.ndarray) -> None:
        out = apply_blur_bar(rgb_image, blur_sigma=100, position="waist")
        assert out.dtype == np.uint8

    def test_width_height_ratios(self, rgb_image: np.ndarray) -> None:
        out = apply_blur_bar(
            rgb_image,
            position="waist",
            width_ratio=1.0,
            height_ratio=0.15,
        )
        assert out.shape == rgb_image.shape

    def test_bad_dtype_raises(self) -> None:
        bad = np.zeros((100, 100, 3), dtype=np.float32)
        with pytest.raises(ValueError, match="uint8"):
            apply_blur_bar(bad)

    def test_too_small_raises(self) -> None:
        tiny = np.zeros((10, 10, 3), dtype=np.uint8)
        with pytest.raises(ValueError, match="32"):
            apply_blur_bar(tiny)
