"""evaluation.psnr_ssim 單元測試。"""

from __future__ import annotations

import numpy as np
import pytest

from evaluation.psnr_ssim import (
    calculate_psnr,
    calculate_ssim,
    evaluate_protection,
)


def test_psnr_identical_returns_inf() -> None:
    img = np.random.default_rng(0).integers(0, 256, (16, 16, 3), dtype=np.uint8)
    assert calculate_psnr(img, img) == float("inf")


def test_psnr_known_value() -> None:
    """MSE=100 → PSNR = 20*log10(255/10) ≈ 28.130803… dB（預期硬編碼）。"""
    img1 = np.full((4, 4, 3), 100, dtype=np.uint8)
    img2 = np.full((4, 4, 3), 110, dtype=np.uint8)
    assert calculate_psnr(img1, img2) == pytest.approx(28.13080, abs=0.001)


def test_ssim_identical_returns_one() -> None:
    img = np.random.default_rng(1).integers(0, 256, (32, 32, 3), dtype=np.uint8)
    assert calculate_ssim(img, img) == pytest.approx(1.0, abs=1e-9)


def test_ssim_range_zero_to_one() -> None:
    a = np.zeros((24, 24, 3), dtype=np.uint8)
    b = np.full((24, 24, 3), 255, dtype=np.uint8)
    s_dis = calculate_ssim(a, b)
    assert 0.0 <= s_dis <= 1.0
    c = np.full((24, 24, 3), 200, dtype=np.uint8)
    d = np.full((24, 24, 3), 205, dtype=np.uint8)
    s_sim = calculate_ssim(c, d)
    assert 0.0 <= s_sim <= 1.0
    assert s_sim > s_dis


def test_evaluate_returns_all_keys() -> None:
    o = np.random.default_rng(2).integers(0, 256, (20, 20, 3), dtype=np.uint8)
    p = np.clip(o.astype(np.int16) + 3, 0, 255).astype(np.uint8)
    out = evaluate_protection(o, p)
    assert set(out.keys()) == {"psnr", "ssim", "max_diff", "mean_diff"}
    assert isinstance(out["max_diff"], int)
    assert isinstance(out["mean_diff"], float)
    assert isinstance(out["psnr"], float)
    assert isinstance(out["ssim"], float)


def test_input_validation() -> None:
    a = np.zeros((10, 10, 3), dtype=np.uint8)
    b = np.zeros((10, 11, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="Shape"):
        calculate_psnr(a, b)
    with pytest.raises(ValueError):
        calculate_psnr(np.zeros((10, 10), dtype=np.uint8), np.zeros((10, 10), dtype=np.uint8))
    with pytest.raises(ValueError):
        calculate_ssim(
            np.zeros((10, 10, 3), dtype=np.float32),
            np.zeros((10, 10, 3), dtype=np.float32),
        )


def test_ssim_too_small_raises() -> None:
    a = np.zeros((10, 10, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="SSIM requires"):
        calculate_ssim(a, a)
