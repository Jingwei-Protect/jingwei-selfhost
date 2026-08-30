"""Unit tests for core/face_stroke_injection.py."""

from __future__ import annotations

import numpy as np
import pytest

from core.face_stroke_injection import apply_face_stroke_injection


@pytest.fixture()
def gray_image() -> np.ndarray:
    """Grayscale image stored as RGB with bright face-like region."""
    rng = np.random.default_rng(0)
    gray = rng.integers(20, 80, (200, 200), dtype=np.uint8)
    gray[30:100, 50:150] = rng.integers(160, 230, (70, 100), dtype=np.uint8)
    return np.stack([gray, gray, gray], axis=-1)


@pytest.fixture()
def color_image() -> np.ndarray:
    rng = np.random.default_rng(1)
    return rng.integers(0, 256, (200, 200, 3), dtype=np.uint8)


class TestFaceStrokeInjection:
    def test_shape_dtype(self, gray_image: np.ndarray) -> None:
        out = apply_face_stroke_injection(gray_image)
        assert out.shape == gray_image.shape
        assert out.dtype == np.uint8

    def test_deterministic(self, gray_image: np.ndarray) -> None:
        a = apply_face_stroke_injection(gray_image, seed=42)
        b = apply_face_stroke_injection(gray_image, seed=42)
        np.testing.assert_array_equal(a, b)

    def test_different_seeds(self, gray_image: np.ndarray) -> None:
        a = apply_face_stroke_injection(gray_image, seed=1)
        b = apply_face_stroke_injection(gray_image, seed=2)
        assert not np.array_equal(a, b)

    def test_modifies_image(self, gray_image: np.ndarray) -> None:
        out = apply_face_stroke_injection(gray_image)
        assert not np.array_equal(out, gray_image)

    def test_works_on_color(self, color_image: np.ndarray) -> None:
        out = apply_face_stroke_injection(color_image)
        assert out.shape == color_image.shape

    def test_bad_dtype_raises(self) -> None:
        bad = np.zeros((100, 100, 3), dtype=np.float32)
        with pytest.raises(ValueError, match="uint8"):
            apply_face_stroke_injection(bad)

    def test_too_small_raises(self) -> None:
        tiny = np.zeros((10, 10, 3), dtype=np.uint8)
        with pytest.raises(ValueError, match="32"):
            apply_face_stroke_injection(tiny)

    def test_high_stroke_count(self, gray_image: np.ndarray) -> None:
        out = apply_face_stroke_injection(gray_image, n_strokes=100, darkness=60)
        assert out.dtype == np.uint8
        diff = np.abs(out.astype(int) - gray_image.astype(int))
        assert diff.sum() > 0
