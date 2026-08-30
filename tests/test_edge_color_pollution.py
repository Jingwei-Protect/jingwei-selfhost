"""Unit tests for ``core.edge_color_pollution``."""

from __future__ import annotations

import numpy as np
import pytest

from core.edge_color_pollution import _POLLUTION_COLORS, apply_edge_color_pollution


def _make_image(h: int = 128, w: int = 128, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(30, 220, size=(h, w, 3), dtype=np.uint8)


def _edge_image() -> np.ndarray:
    """Image with strong vertical edge down the middle."""
    img = np.zeros((128, 128, 3), dtype=np.uint8)
    img[:, :64] = 40
    img[:, 64:] = 200
    return img


def test_shape_dtype() -> None:
    img = _make_image()
    out = apply_edge_color_pollution(img, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_deterministic() -> None:
    img = _make_image(seed=1)
    a = apply_edge_color_pollution(img, seed=42)
    b = apply_edge_color_pollution(img, seed=42)
    assert np.array_equal(a, b)


def test_different_seeds() -> None:
    img = _make_image(seed=2)
    a = apply_edge_color_pollution(img, seed=1)
    b = apply_edge_color_pollution(img, seed=2)
    assert not np.array_equal(a, b)


def test_modifies_image() -> None:
    img = _make_image(seed=3)
    out = apply_edge_color_pollution(img, opacity=0.5, seed=42)
    assert not np.array_equal(out, img)


def test_edge_regions_affected() -> None:
    """On an image with a sharp edge, pollution must appear near that edge."""
    img = _edge_image()
    out = apply_edge_color_pollution(img, opacity=0.6, band_width=3, seed=42)
    edge_col = 64
    near_edge = out[:, edge_col - 6:edge_col + 6, :]
    orig_near = img[:, edge_col - 6:edge_col + 6, :]
    diff = np.abs(near_edge.astype(int) - orig_near.astype(int))
    assert diff.mean() > 5.0, "Edge region should show significant colour change"


def test_high_saturation_in_diff() -> None:
    """Pollution colours should inject hue absent from a grayscale input."""
    img = np.full((128, 128, 3), 128, dtype=np.uint8)
    img[:, 64:] = 60
    out = apply_edge_color_pollution(img, opacity=0.6, seed=42)
    diff = (out.astype(int) - img.astype(int))
    r_diff = diff[..., 0]
    b_diff = diff[..., 2]
    assert np.abs(r_diff).max() > 20 or np.abs(b_diff).max() > 20


def test_parameter_clamping() -> None:
    img = _make_image(seed=4)
    out_low = apply_edge_color_pollution(
        img, opacity=0.01, band_width=0, n_passes=0, edge_percentile=30, seed=42
    )
    out_high = apply_edge_color_pollution(
        img, opacity=1.0, band_width=20, n_passes=20, edge_percentile=99, seed=42
    )
    assert out_low.shape == img.shape
    assert out_high.shape == img.shape


def test_invalid_dtype_raises() -> None:
    img = _make_image().astype(np.float32)
    with pytest.raises(ValueError):
        apply_edge_color_pollution(img)
