"""M1 DCT 頻域擾動模組單元測試。

涵蓋：shape 不變、strength=0 近乎無損、中度強度 PSNR 門檻、
確定性保證、輸入驗證、非 8 倍數尺寸處理。
"""

import numpy as np
import pytest

from core.dct_perturb import apply_dct_perturbation


# ---------------------------------------------------------------------------
# 測試輔助
# ---------------------------------------------------------------------------

def _psnr(a: np.ndarray, b: np.ndarray) -> float:
    """計算兩張 uint8 影像的 PSNR（dB）。不依賴外部評估模組。"""
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    if mse == 0.0:
        return float("inf")
    return 20.0 * np.log10(255.0 / np.sqrt(mse))


def _synthetic_image(h: int = 256, w: int = 256, seed: int = 0) -> np.ndarray:
    """生成可重現的合成 uint8 RGB 影像。"""
    return np.random.default_rng(seed).integers(0, 256, (h, w, 3), dtype=np.uint8)


# ---------------------------------------------------------------------------
# 測試
# ---------------------------------------------------------------------------

def test_output_shape_unchanged() -> None:
    """輸出 shape 與 dtype 必須與輸入完全相同。"""
    img = _synthetic_image(256, 256)
    out = apply_dct_perturbation(img, strength=0.5, seed=42)

    assert out.shape == img.shape, f"shape mismatch: {out.shape} != {img.shape}"
    assert out.dtype == np.uint8, f"dtype mismatch: {out.dtype}"


def test_strength_zero_returns_near_identical() -> None:
    """strength=0 時擾動量為零，PSNR 應 > 50 dB（僅有色彩空間往返誤差）。"""
    img = _synthetic_image(256, 256)
    out = apply_dct_perturbation(img, strength=0.0, seed=42)

    psnr_val = _psnr(img, out)
    assert psnr_val > 50.0, (
        f"strength=0 PSNR expected > 50 dB, got {psnr_val:.2f} dB"
    )


def test_strength_half_meets_quality() -> None:
    """strength=0.5 對合成 256×256 影像，PSNR 應 ≥ 38 dB（PRD §6.4 中度門檻）。"""
    img = _synthetic_image(256, 256)
    out = apply_dct_perturbation(img, strength=0.5, seed=42)

    psnr_val = _psnr(img, out)
    assert psnr_val >= 38.0, (
        f"strength=0.5 PSNR expected >= 38 dB, got {psnr_val:.2f} dB"
    )


def test_deterministic_with_seed() -> None:
    """相同 (image, strength, seed) 必須產生逐像素相同的輸出。"""
    img = _synthetic_image(256, 256)
    out1 = apply_dct_perturbation(img, strength=0.5, seed=42)
    out2 = apply_dct_perturbation(img, strength=0.5, seed=42)

    assert np.array_equal(out1, out2), "Outputs differ with identical inputs and seed."


def test_input_validation() -> None:
    """不合法輸入應 raise ValueError。

    測試三種情況：
    (a) 2-D 灰階陣列（shape HxW）
    (b) float32 dtype（非 uint8）
    (c) 4 通道 RGBA（shape HxWx4）
    """
    h, w = 64, 64

    # (a) 灰階
    with pytest.raises(ValueError):
        apply_dct_perturbation(np.zeros((h, w), dtype=np.uint8))

    # (b) float32
    with pytest.raises(ValueError):
        apply_dct_perturbation(np.zeros((h, w, 3), dtype=np.float32))

    # (c) 4 通道
    with pytest.raises(ValueError):
        apply_dct_perturbation(np.zeros((h, w, 4), dtype=np.uint8))


def test_non_multiple_of_8_dimensions() -> None:
    """非 8 倍數尺寸（250×300）應能正常處理並回傳相同尺寸。"""
    img = _synthetic_image(250, 300)
    out = apply_dct_perturbation(img, strength=0.5, seed=42)

    assert out.shape == (250, 300, 3), (
        f"Expected (250, 300, 3), got {out.shape}"
    )
    assert out.dtype == np.uint8
