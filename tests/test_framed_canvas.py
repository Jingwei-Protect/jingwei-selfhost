"""Unit tests for ``core.framed_canvas``."""

from __future__ import annotations

import numpy as np
import pytest

from core.framed_canvas import DEFAULT_FRAMED_CANVAS_TEXT, apply_framed_canvas


def _make_image(h: int, w: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)


def test_output_dimensions() -> None:
    """800 (W) x 600 (H) input, ratio=0.125 -> ~750x1000x3 (allow +/-2 px)."""
    img = _make_image(600, 800)
    out = apply_framed_canvas(img, border_ratio=0.125, seed=42)
    assert out.ndim == 3 and out.shape[2] == 3
    assert abs(out.shape[0] - 750) <= 2
    assert abs(out.shape[1] - 1000) <= 2


def test_dtype_preserved() -> None:
    img = _make_image(128, 128)
    out = apply_framed_canvas(img, border_ratio=0.125, seed=42)
    assert out.dtype == np.uint8


def test_deterministic() -> None:
    img = _make_image(128, 128, seed=1)
    a = apply_framed_canvas(img, border_text="hello", border_ratio=0.125, seed=42)
    b = apply_framed_canvas(img, border_text="hello", border_ratio=0.125, seed=42)
    assert np.array_equal(a, b)


def test_center_contains_original() -> None:
    img = _make_image(96, 96, seed=2)
    out = apply_framed_canvas(img, border_ratio=0.125, seed=42)
    h, w = img.shape[:2]
    out_h, out_w = out.shape[:2]
    border_h = (out_h - h) // 2
    border_w = (out_w - w) // 2
    inner = out[border_h:border_h + h, border_w:border_w + w]
    assert np.array_equal(inner, img)


def test_empty_text_uses_default() -> None:
    img = _make_image(96, 96, seed=3)
    out_default = apply_framed_canvas(img, border_text="", border_ratio=0.125, seed=42)
    out_explicit = apply_framed_canvas(
        img, border_text=DEFAULT_FRAMED_CANVAS_TEXT, border_ratio=0.125, seed=42
    )
    assert out_default.dtype == np.uint8
    assert np.array_equal(out_default, out_explicit)


def test_border_ratio_clamping() -> None:
    img = _make_image(96, 96, seed=4)
    out_low = apply_framed_canvas(img, border_ratio=0.05, seed=42)
    out_high = apply_framed_canvas(img, border_ratio=0.30, seed=42)
    h, w = img.shape[:2]
    for out, expected_ratio in ((out_low, 0.08), (out_high, 0.20)):
        bh = (out.shape[0] - h) // 2
        bw = (out.shape[1] - w) // 2
        assert abs(bh - int(h * expected_ratio)) <= 1
        assert abs(bw - int(w * expected_ratio)) <= 1


def test_invalid_dtype_raises() -> None:
    img = _make_image(64, 64).astype(np.float32)
    with pytest.raises(ValueError):
        apply_framed_canvas(img)
