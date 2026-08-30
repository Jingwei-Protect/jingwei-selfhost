"""M3 藍色通道棋盤擾動模組單元測試。"""

import numpy as np
import pytest

from core.blue_channel import apply_blue_channel_perturbation


def _psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    if mse == 0.0:
        return float("inf")
    return 20.0 * np.log10(255.0 / np.sqrt(mse))


def _img(seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 256, (256, 256, 3), dtype=np.uint8)


def test_output_shape_unchanged() -> None:
    img = _img()
    out = apply_blue_channel_perturbation(img, strength=0.5, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_strength_zero_returns_identical() -> None:
    """strength=0 → PSNR > 60 dB（B 通道亦完全不變）。"""
    img = _img()
    out = apply_blue_channel_perturbation(img, strength=0.0, seed=42)
    psnr_val = _psnr(img, out)
    assert psnr_val > 60.0, f"strength=0 PSNR expected > 60 dB, got {psnr_val:.2f} dB"


def test_only_blue_channel_modified() -> None:
    """R、G 通道必須與輸入逐像素完全相同；B 通道允許有差異。"""
    img = _img()
    out = apply_blue_channel_perturbation(img, strength=0.5, seed=42)
    assert np.array_equal(out[:, :, 0], img[:, :, 0]), "R channel was modified"
    assert np.array_equal(out[:, :, 1], img[:, :, 1]), "G channel was modified"


def test_strength_default_high_psnr() -> None:
    """strength=0.5 → PSNR > 42 dB（PRD §6.4 輕度門檻，僅 B 通道改動）。"""
    img = _img()
    out = apply_blue_channel_perturbation(img, strength=0.5, seed=42)
    psnr_val = _psnr(img, out)
    assert psnr_val > 42.0, f"strength=0.5 PSNR expected > 42 dB, got {psnr_val:.2f} dB"


def test_deterministic_with_seed() -> None:
    img = _img()
    out1 = apply_blue_channel_perturbation(img, strength=0.5, seed=42)
    out2 = apply_blue_channel_perturbation(img, strength=0.5, seed=42)
    assert np.array_equal(out1, out2)


def test_input_validation() -> None:
    h, w = 64, 64
    with pytest.raises(ValueError):
        apply_blue_channel_perturbation(np.zeros((h, w), dtype=np.uint8))
    with pytest.raises(ValueError):
        apply_blue_channel_perturbation(np.zeros((h, w, 3), dtype=np.float32))
    with pytest.raises(ValueError):
        apply_blue_channel_perturbation(np.zeros((h, w, 4), dtype=np.uint8))
