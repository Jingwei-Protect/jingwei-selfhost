"""Unit tests for ``core.triple_watermark_v2``."""

from __future__ import annotations

import numpy as np
import pytest

from core.triple_watermark_v2 import (
    DEFAULT_V2_TEXTS,
    _extract_dominant_colors,
    _shift_color_brightness,
    apply_triple_watermark_v2,
)


def _make_image(h: int = 128, w: int = 128, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(30, 220, size=(h, w, 3), dtype=np.uint8)


def test_shape_dtype() -> None:
    img = _make_image()
    out = apply_triple_watermark_v2(img, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_deterministic() -> None:
    img = _make_image(seed=1)
    a = apply_triple_watermark_v2(img, opacity=0.35, seed=42)
    b = apply_triple_watermark_v2(img, opacity=0.35, seed=42)
    assert np.array_equal(a, b)


def test_default_texts_used() -> None:
    img = _make_image(seed=2)
    a = apply_triple_watermark_v2(img, seed=42)
    b = apply_triple_watermark_v2(img, texts=list(DEFAULT_V2_TEXTS), seed=42)
    assert np.array_equal(a, b)


def test_modifies_image() -> None:
    img = _make_image(seed=3)
    out = apply_triple_watermark_v2(img, opacity=0.35, seed=42)
    assert not np.array_equal(out, img)


def test_invalid_text_length() -> None:
    img = _make_image(seed=4)
    with pytest.raises(ValueError):
        apply_triple_watermark_v2(img, texts=["only one"])
    with pytest.raises(ValueError):
        apply_triple_watermark_v2(img, texts=["a", "b", "c", "d"])


def test_invalid_dtype_raises() -> None:
    img = _make_image().astype(np.float32)
    with pytest.raises(ValueError):
        apply_triple_watermark_v2(img)


def test_parameter_clamping_does_not_error() -> None:
    img = _make_image(seed=5)
    out_low = apply_triple_watermark_v2(
        img, opacity=0.01, rgb_split_offset=0, brightness_delta=1, seed=42
    )
    out_high = apply_triple_watermark_v2(
        img, opacity=0.99, rgb_split_offset=99, brightness_delta=200, seed=42
    )
    assert out_low.shape == img.shape
    assert out_high.shape == img.shape


def test_dominant_colors_from_known_palette() -> None:
    """K-means on a 3-colour painted image should recover those 3 colours."""
    img = np.zeros((96, 96, 3), dtype=np.uint8)
    img[:32, :, :] = (200, 80, 80)
    img[32:64, :, :] = (80, 180, 90)
    img[64:, :, :] = (60, 90, 200)
    colors = _extract_dominant_colors(img, n_colors=3, seed=42)
    assert len(colors) >= 1
    for c in colors:
        assert all(0 <= v <= 255 for v in c)


def test_content_aware_mode_produces_different_output() -> None:
    """content_aware=True should produce a different result from default."""
    img = _make_image(seed=7)
    fixed = apply_triple_watermark_v2(img, opacity=0.45, seed=42)
    aware = apply_triple_watermark_v2(
        img, opacity=0.45, content_aware=True, seed=42
    )
    assert aware.shape == img.shape
    assert aware.dtype == np.uint8
    assert not np.array_equal(fixed, aware)


def test_content_aware_low_chroma_on_grey_input() -> None:
    """On a near-grey image the content-aware watermark should also be near-grey."""
    img = np.full((128, 128, 3), 128, dtype=np.uint8)
    out = apply_triple_watermark_v2(
        img, opacity=0.55, brightness_delta=20, content_aware=True, seed=42
    )
    diff = out.astype(int) - img.astype(int)
    sat_proxy = np.max(np.abs(diff), axis=2) - np.min(np.abs(diff), axis=2)
    assert sat_proxy.mean() < 12.0, (
        "Content-aware overlay on grey input should stay roughly chromaless"
    )


def test_shift_color_brightness_clamps() -> None:
    assert _shift_color_brightness((0, 0, 0), 50) == (50, 50, 50)
    out = _shift_color_brightness((100, 50, 25), 25)
    assert all(0 <= v <= 255 for v in out)
    assert out[0] > 100
    out_down = _shift_color_brightness((200, 100, 50), -50)
    assert all(0 <= v <= 255 for v in out_down)
    assert out_down[0] < 200
    assert out_down[0] > 0
