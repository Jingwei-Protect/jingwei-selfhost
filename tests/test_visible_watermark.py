"""M5 可見水印模組單元測試。"""

import numpy as np
import pytest

from core.visible_watermark import apply_visible_watermark


def _img(seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 256, (256, 256, 3), dtype=np.uint8)


def test_output_shape_unchanged() -> None:
    img = _img()
    out = apply_visible_watermark(img, "Test", opacity=0.1)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_text_actually_visible() -> None:
    """水印文字必須對影像有可量測的影響（mean abs diff > 1.0）。"""
    img = _img()
    out = apply_visible_watermark(img, "Copyright 2024", opacity=0.3, density="dense")
    diff = np.mean(np.abs(out.astype(np.float64) - img.astype(np.float64)))
    assert diff > 1.0, f"Watermark not visible: mean abs diff = {diff:.4f}"


def test_opacity_zero_returns_near_identical() -> None:
    """opacity=0 觸發 fast-path，輸出與輸入逐像素完全相同。"""
    img = _img()
    out = apply_visible_watermark(img, "Test", opacity=0.0)
    assert np.array_equal(img, out), "opacity=0 should return exact copy of input"


def test_density_levels_produce_different_results() -> None:
    """三種密度設定的輸出應兩兩不等。"""
    img = _img()
    sparse = apply_visible_watermark(img, "Test", opacity=0.3, density="sparse")
    normal = apply_visible_watermark(img, "Test", opacity=0.3, density="normal")
    dense = apply_visible_watermark(img, "Test", opacity=0.3, density="dense")

    assert not np.array_equal(sparse, normal), "sparse == normal"
    assert not np.array_equal(normal, dense), "normal == dense"
    assert not np.array_equal(sparse, dense), "sparse == dense"


def test_empty_text_raises() -> None:
    img = _img()
    with pytest.raises(ValueError):
        apply_visible_watermark(img, "")


def test_input_validation() -> None:
    h, w = 64, 64
    with pytest.raises(ValueError):
        apply_visible_watermark(np.zeros((h, w), dtype=np.uint8), "Test")
    with pytest.raises(ValueError):
        apply_visible_watermark(np.zeros((h, w, 3), dtype=np.float32), "Test")
    with pytest.raises(ValueError):
        apply_visible_watermark(np.zeros((h, w, 4), dtype=np.uint8), "Test")
