"""Unit tests for ``core.triple_watermark``."""

from __future__ import annotations

import numpy as np
import pytest

from core.triple_watermark import (
    DEFAULT_TRIPLE_COLORS,
    DEFAULT_TRIPLE_TEXTS,
    apply_triple_watermark,
)


def _make_image(h: int = 128, w: int = 128, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)


def test_shape_dtype() -> None:
    img = _make_image()
    out = apply_triple_watermark(img, opacity=0.18, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_deterministic() -> None:
    img = _make_image(seed=1)
    a = apply_triple_watermark(img, opacity=0.18, seed=42)
    b = apply_triple_watermark(img, opacity=0.18, seed=42)
    assert np.array_equal(a, b)


def test_default_texts_and_colors() -> None:
    img = _make_image(seed=2)
    a = apply_triple_watermark(img, opacity=0.18, seed=42)
    b = apply_triple_watermark(
        img,
        texts=list(DEFAULT_TRIPLE_TEXTS),
        colors=list(DEFAULT_TRIPLE_COLORS),
        opacity=0.18,
        seed=42,
    )
    assert np.array_equal(a, b)


def test_modifies_image() -> None:
    img = _make_image(seed=3)
    out = apply_triple_watermark(img, opacity=0.18, seed=42)
    assert not np.array_equal(out, img)


def test_invalid_list_length() -> None:
    img = _make_image(seed=4)
    with pytest.raises(ValueError):
        apply_triple_watermark(img, texts=["only one"])
    with pytest.raises(ValueError):
        apply_triple_watermark(img, colors=[(255, 0, 0), (0, 255, 0)])
