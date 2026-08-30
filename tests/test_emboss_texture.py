"""Unit tests for core/emboss_texture.py."""

from __future__ import annotations

import numpy as np
import pytest

from core.emboss_texture import apply_emboss_texture


@pytest.fixture()
def sample_image() -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.integers(30, 220, (200, 200, 3), dtype=np.uint8)


class TestEmbossTexture:
    def test_shape_dtype(self, sample_image: np.ndarray) -> None:
        out = apply_emboss_texture(sample_image)
        assert out.shape == sample_image.shape
        assert out.dtype == np.uint8

    def test_deterministic(self, sample_image: np.ndarray) -> None:
        a = apply_emboss_texture(sample_image, seed=42)
        b = apply_emboss_texture(sample_image, seed=42)
        np.testing.assert_array_equal(a, b)

    def test_modifies_image(self, sample_image: np.ndarray) -> None:
        out = apply_emboss_texture(sample_image)
        assert not np.array_equal(out, sample_image)

    def test_diagonal_pattern(self, sample_image: np.ndarray) -> None:
        out = apply_emboss_texture(sample_image, pattern="diagonal")
        assert out.dtype == np.uint8

    def test_dots_pattern(self, sample_image: np.ndarray) -> None:
        out = apply_emboss_texture(sample_image, pattern="dots")
        assert not np.array_equal(out, sample_image)

    def test_crosshatch_pattern(self, sample_image: np.ndarray) -> None:
        out = apply_emboss_texture(sample_image, pattern="crosshatch")
        assert not np.array_equal(out, sample_image)

    def test_with_text(self, sample_image: np.ndarray) -> None:
        out = apply_emboss_texture(sample_image, text="© Test")
        assert out.dtype == np.uint8

    def test_intensity_clamping(self, sample_image: np.ndarray) -> None:
        out_low = apply_emboss_texture(sample_image, intensity=0.01)
        out_high = apply_emboss_texture(sample_image, intensity=0.99)
        assert out_low.dtype == np.uint8
        assert out_high.dtype == np.uint8

    def test_bad_dtype_raises(self) -> None:
        bad = np.zeros((100, 100, 3), dtype=np.float32)
        with pytest.raises(ValueError, match="uint8"):
            apply_emboss_texture(bad)

    def test_too_small_raises(self) -> None:
        tiny = np.zeros((10, 10, 3), dtype=np.uint8)
        with pytest.raises(ValueError, match="32"):
            apply_emboss_texture(tiny)
