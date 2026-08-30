"""PSNR / SSIM 品質評估（純 NumPy + SciPy，不依賴 scikit-image）。

SSIM 採 Wang et al. 經典定義：11×11 歸一化高斯視窗（σ=1.5）、`reflect` 邊界、
K1=0.01、K2=0.03、L=255；逐通道計算後對 R/G/B 取算術平均。
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.ndimage import convolve

_K1 = 0.01
_K2 = 0.03
_L = 255.0
_C1 = (_K1 * _L) ** 2
_C2 = (_K2 * _L) ** 2
_SSIM_WINDOW_SIZE = 11
_SSIM_SIGMA = 1.5
_DENOM_EPS = 1e-12


def _gaussian_kernel_11(sigma: float = _SSIM_SIGMA) -> np.ndarray:
    """可分離高斯之 11×11 外積，和為 1。"""
    half = _SSIM_WINDOW_SIZE // 2
    xs = np.arange(_SSIM_WINDOW_SIZE, dtype=np.float64) - half
    g1 = np.exp(-(xs**2) / (2.0 * sigma**2))
    g1 /= g1.sum()
    w = np.outer(g1, g1)
    w /= w.sum()
    return w.astype(np.float64)


_WINDOW = _gaussian_kernel_11()


def _validate_pair(img1: np.ndarray, img2: np.ndarray) -> None:
    if img1.dtype != np.uint8 or img2.dtype != np.uint8:
        raise ValueError("Images must be uint8 RGB arrays.")
    if img1.ndim != 3 or img2.ndim != 3 or img1.shape[2] != 3 or img2.shape[2] != 3:
        raise ValueError(f"Expected HxWx3 RGB, got shapes {img1.shape}, {img2.shape}.")
    if img1.shape != img2.shape:
        raise ValueError(
            f"Shape mismatch: {img1.shape} vs {img2.shape}."
        )


def calculate_psnr(img1: np.ndarray, img2: np.ndarray) -> float:
    """標準 PSNR（uint8 RGB）。逐像素三通道平均 MSE。

    ``MSE == 0`` 時回傳 ``float('inf')``。
    """
    _validate_pair(img1, img2)
    a = img1.astype(np.float32)
    b = img2.astype(np.float32)
    mse = float(np.mean((a - b) ** 2))
    if mse == 0.0:
        return float("inf")
    return 20.0 * np.log10(_L / np.sqrt(mse))


def _ssim_single_channel(ch1: np.ndarray, ch2: np.ndarray) -> float:
    """單通道 float64 SSIM 標量（ch1/ch2 同 shape 2D）。"""
    mu1 = convolve(ch1, _WINDOW, mode="reflect")
    mu2 = convolve(ch2, _WINDOW, mode="reflect")
    # 浮點下 convolve(x*x) - mu*mu 可能為極小負值，裁切避免數值問題
    mu1_sq = mu1 * mu1
    mu2_sq = mu2 * mu2
    sigma1_sq = np.maximum(convolve(ch1 * ch1, _WINDOW, mode="reflect") - mu1_sq, 0.0)
    sigma2_sq = np.maximum(convolve(ch2 * ch2, _WINDOW, mode="reflect") - mu2_sq, 0.0)
    sigma12 = convolve(ch1 * ch2, _WINDOW, mode="reflect") - mu1 * mu2
    numer = (2.0 * mu1 * mu2 + _C1) * (2.0 * sigma12 + _C2)
    denom = (mu1_sq + mu2_sq + _C1) * (sigma1_sq + sigma2_sq + _C2)
    denom = np.maximum(denom, _DENOM_EPS)
    ssim_map = numer / denom
    return float(np.mean(ssim_map))


def calculate_ssim(img1: np.ndarray, img2: np.ndarray) -> float:
    """SSIM，三通道各算一個標量後取平均。範圍約 [0, 1]。

    需 **H ≥ 11** 且 **W ≥ 11** 以容納視窗與 reflect 邊界。
    """
    _validate_pair(img1, img2)
    h, w = img1.shape[:2]
    if h < _SSIM_WINDOW_SIZE or w < _SSIM_WINDOW_SIZE:
        raise ValueError(
            f"SSIM requires size at least {_SSIM_WINDOW_SIZE}×{_SSIM_WINDOW_SIZE}, "
            f"got {h}×{w}."
        )
    scores: list[float] = []
    x = img1.astype(np.float64)
    y = img2.astype(np.float64)
    for c in range(3):
        scores.append(_ssim_single_channel(x[:, :, c], y[:, :, c]))
    return float(np.mean(scores))


_SSIM_MAX_DIM = 512


def evaluate_protection(
    original: np.ndarray,
    protected: np.ndarray,
) -> dict[str, Any]:
    """回傳 PSNR、SSIM、最大／平均絕對像素差。

    For images larger than 512px, SSIM is computed on a downscaled copy
    for speed (SSIM is scale-invariant for perceptual quality).
    PSNR and diff stats are always computed at full resolution.
    """
    _validate_pair(original, protected)
    h, w = original.shape[:2]
    if h < _SSIM_WINDOW_SIZE or w < _SSIM_WINDOW_SIZE:
        raise ValueError(
            f"evaluate_protection requires size at least "
            f"{_SSIM_WINDOW_SIZE}×{_SSIM_WINDOW_SIZE} for SSIM, got {h}×{w}."
        )
    diff = np.abs(original.astype(np.int16) - protected.astype(np.int16))

    if max(h, w) > _SSIM_MAX_DIM:
        import cv2
        scale = _SSIM_MAX_DIM / max(h, w)
        sh = max(_SSIM_WINDOW_SIZE, int(h * scale))
        sw = max(_SSIM_WINDOW_SIZE, int(w * scale))
        o_small = cv2.resize(original, (sw, sh), interpolation=cv2.INTER_AREA)
        p_small = cv2.resize(protected, (sw, sh), interpolation=cv2.INTER_AREA)
        ssim_val = calculate_ssim(o_small, p_small)
    else:
        ssim_val = calculate_ssim(original, protected)

    return {
        "psnr": calculate_psnr(original, protected),
        "ssim": ssim_val,
        "max_diff": int(np.max(diff)),
        "mean_diff": float(np.mean(diff.astype(np.float32))),
    }
