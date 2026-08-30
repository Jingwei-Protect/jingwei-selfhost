"""M6：頻譜可控的紋理污染層模組。

在影像上以低不透明度（3–8%）疊加自研生成的擾動紋理，紋理頻譜能量
集中於正規化頻率 [0.3, 0.5] 區間——此頻段為 SD 系列 VAE encoder
（含 SD 1.5 / SDXL，皆採 8 倍下取樣）對結構特徵最敏感的範圍，
同時人眼 CSF 在此區段已快速衰減，視覺擾動微小。

提供三種紋理類型：
- 'moire'   ：兩條微小角差的 sine grating 疊加，產生莫爾干涉條紋。
- 'halftone'：規則點陣（每點振幅與位置微擾），近似印刷半色調網點。
- 'noise'   ：白噪聲經 FFT 帶通濾波後的偽隨機紋理。

法律聲明（PRD §5.5）：
本模組所有演算法為獨立設計，僅參考公開學術文獻中之對抗擾動概念，
未引用 Mist / Glaze / Nightshade 任何程式碼或目標紋理；所有實作
僅使用傳統信號處理（numpy / scipy / opencv-python），不依賴任何
深度學習框架。
"""

# Legal notice (PRD §5.5):
# Algorithm independently designed. Inspired by adversarial perturbation
# concepts in academic literature. No code from Mist / Glaze / Nightshade
# was referenced. All implementations use traditional signal processing
# (numpy / scipy / opencv-python) without any deep learning framework.

from __future__ import annotations

from typing import Literal

import numpy as np

# 紋理擾動最大幅度（pattern 已正規化至 [-1, 1]）。
# 預設 opacity=0.05 時最大像素改動 = 1.0 × 0.05 × 25.0 = 1.25 pixel，
# 對應 PSNR ≈ 46 dB（理論上限）；opacity=0.08 時 PSNR ≈ 42 dB，
# 符合 PRD §6.4 中度門檻。
_MAX_TEXTURE_AMP: float = 25.0

# SD VAE 敏感頻段（正規化頻率，0=DC、0.5=Nyquist）
_TARGET_BAND: tuple[float, float] = (0.3, 0.5)

_VALID_TEXTURE_TYPES = ("moire", "halftone", "noise")


def _validate_input(image: np.ndarray) -> None:
    """驗證輸入影像格式，不符合時 raise ValueError。"""
    if image.dtype != np.uint8:
        raise ValueError(
            f"Input dtype must be uint8, got {image.dtype}. "
            "Float inputs are rejected by design; convert to uint8 first."
        )
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(
            f"Input must be an HxWx3 RGB array, got shape {image.shape}."
        )
    h, w = image.shape[:2]
    if h < 8 or w < 8:
        raise ValueError(
            f"Image dimensions must be at least 8×8, got {h}×{w}."
        )


def _frequency_to_norm(frequency: float) -> float:
    """將使用者面 frequency ∈ [0, 1] 線性映射至 freq_norm ∈ [0.30, 0.50]。

    統一映射公式（所有 pattern 類型共用）：
        freq_norm = 0.3 + frequency * 0.2
    - frequency = 0.0 → freq_norm = 0.30（紋理較粗）
    - frequency = 0.5 → freq_norm = 0.40（預設、中心）
    - frequency = 1.0 → freq_norm = 0.50（紋理較細）
    """
    return 0.3 + frequency * 0.2


def _generate_moire_pattern(
    shape: tuple[int, int],
    frequency: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """生成莫爾干涉條紋圖案。

    兩個 sine grating 在略不同角度（5°–11°）疊加，產生 beat
    frequency 視覺效果即莫爾條紋。

    空間頻率公式（修正 1，統一映射）：
        freq_norm = 0.3 + frequency * 0.2
        k = freq_norm * π    (弧度/像素)

    Parameters
    ----------
    shape:
        (H, W) tuple。
    frequency:
        使用者面頻率參數，[0, 1]。
    rng:
        Generator，控制角度與相位。

    Returns
    -------
    np.ndarray
        float32 pattern，shape (H, W)，值域 [-1, 1]。
    """
    h, w = shape
    freq_norm = _frequency_to_norm(frequency)
    k = freq_norm * np.pi

    theta1 = float(rng.uniform(0.0, np.pi))
    theta2 = theta1 + float(rng.uniform(0.05, 0.20))  # 約 3°–11° 角差
    phase1 = float(rng.uniform(0.0, 2.0 * np.pi))
    phase2 = float(rng.uniform(0.0, 2.0 * np.pi))

    ys, xs = np.meshgrid(
        np.arange(h, dtype=np.float32),
        np.arange(w, dtype=np.float32),
        indexing="ij",
    )

    g1 = np.sin(k * (xs * np.cos(theta1) + ys * np.sin(theta1)) + phase1)
    g2 = np.sin(k * (xs * np.cos(theta2) + ys * np.sin(theta2)) + phase2)
    pattern = ((g1 + g2) / 2.0).astype(np.float32)
    return pattern


def _generate_halftone_pattern(
    shape: tuple[int, int],
    frequency: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """生成半色調點陣紋理。

    Grid spacing 公式（修正 1，統一映射）：
        freq_norm = 0.3 + frequency * 0.2
        d = max(2, round(1.0 / freq_norm))   (像素)

    每個網格中心放一個高斯凸點（σ ≈ d/3），振幅由 rng 在 [0.5, 1.0]
    隨機調變；中心位置 ±1 pixel 內隨機抖動，避免完全規律 pattern
    被對手以已知圖案過濾。

    Returns
    -------
    np.ndarray
        float32 pattern，shape (H, W)，值域 [-1, 1]。
    """
    h, w = shape
    freq_norm = _frequency_to_norm(frequency)
    d = max(2, int(round(1.0 / freq_norm)))
    sigma = max(0.6, d / 3.0)

    pattern = np.zeros((h, w), dtype=np.float32)

    # 在每個 grid cell (i*d, j*d) 中心畫一個高斯凸點
    ys, xs = np.meshgrid(
        np.arange(h, dtype=np.float32),
        np.arange(w, dtype=np.float32),
        indexing="ij",
    )

    # 預先生成所有 cell 的隨機振幅與位置抖動（為了確定性）
    n_cells_y = (h + d - 1) // d
    n_cells_x = (w + d - 1) // d
    amps = rng.uniform(0.5, 1.0, size=(n_cells_y, n_cells_x)).astype(np.float32)
    jitter = rng.uniform(-1.0, 1.0, size=(n_cells_y, n_cells_x, 2)).astype(np.float32)

    two_sigma_sq = 2.0 * sigma * sigma

    for ci in range(n_cells_y):
        for cj in range(n_cells_x):
            cy = ci * d + d / 2.0 + jitter[ci, cj, 0]
            cx = cj * d + d / 2.0 + jitter[ci, cj, 1]
            dy = ys - cy
            dx = xs - cx
            # 高斯凸點僅在半徑 3σ 範圍內貢獻顯著能量，
            # 為效能可裁切範圍；此處全圖計算以保程式碼簡潔
            blob = amps[ci, cj] * np.exp(-(dx * dx + dy * dy) / two_sigma_sq)
            pattern += blob.astype(np.float32)

    # 正規化至 [-1, 1]：減全圖平均後除以最大絕對值
    pattern -= float(pattern.mean())
    max_abs = float(np.max(np.abs(pattern)))
    if max_abs > 1e-8:
        pattern = pattern / max_abs
    return pattern.astype(np.float32)


def _generate_spectral_noise(
    shape: tuple[int, int],
    freq_band: tuple[float, float],
    rng: np.random.Generator,
) -> np.ndarray:
    """生成帶通濾波後的偽隨機紋理。

    流程：
        white = rng.standard_normal(shape)
        F = fft2(white)
        mask = (freq_band[0] ≤ r ≤ freq_band[1])  (環狀帶通)
        filtered = ifft2(F * mask).real
        pattern = filtered / max(|filtered|)

    Parameters
    ----------
    shape:
        (H, W)。
    freq_band:
        (low, high)，正規化頻率（0=DC，0.5=Nyquist）。
    rng:
        Generator，控制白噪聲。

    Returns
    -------
    np.ndarray
        float32 pattern，shape (H, W)，值域 [-1, 1]。
    """
    h, w = shape
    white = rng.standard_normal((h, w)).astype(np.float32)
    F = np.fft.fft2(white)

    fy = np.fft.fftfreq(h)  # 範圍 [-0.5, 0.5)
    fx = np.fft.fftfreq(w)
    R = np.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2)

    low, high = freq_band
    mask = ((R >= low) & (R <= high)).astype(np.float32)

    filtered = np.fft.ifft2(F * mask).real.astype(np.float32)
    max_abs = float(np.max(np.abs(filtered)))
    if max_abs > 1e-8:
        filtered = filtered / max_abs
    return filtered.astype(np.float32)


def _shape_spectrum(
    pattern: np.ndarray,
    target_band: tuple[float, float],
) -> np.ndarray:
    """對任意 pattern 套用環狀帶通濾波，再正規化至 [-1, 1]。

    對 'noise' pattern 為（近似）冪等操作；對 'moire' / 'halftone'
    可切除主頻外的諧波，使所有 texture type 最終頻譜能量集中於
    target_band。

    Parameters
    ----------
    pattern:
        float32 (H, W)。
    target_band:
        (low, high)，正規化頻率。

    Returns
    -------
    np.ndarray
        float32 shaped pattern，值域 [-1, 1]。
    """
    h, w = pattern.shape
    F = np.fft.fft2(pattern)

    fy = np.fft.fftfreq(h)
    fx = np.fft.fftfreq(w)
    R = np.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2)

    low, high = target_band
    mask = ((R >= low) & (R <= high)).astype(np.float32)

    shaped = np.fft.ifft2(F * mask).real.astype(np.float32)
    max_abs = float(np.max(np.abs(shaped)))
    if max_abs > 1e-8:
        shaped = shaped / max_abs
    return shaped.astype(np.float32)


def apply_texture_pollution(
    image: np.ndarray,
    texture_type: Literal["moire", "halftone", "noise"] = "moire",
    opacity: float = 0.05,
    frequency: float = 0.5,
    seed: int = 42,
) -> np.ndarray:
    """M6：在影像上疊加頻譜可控的紋理擾動。

    演算法概述
    ----------
    1. 驗證輸入（uint8 RGB，H≥8, W≥8）。
    2. opacity ≤ 0.0 fast-path：return image.copy()。
    3. 依 texture_type 生成單通道 (H, W) 紋理 pattern：
       - moire   ：兩條 sine grating 疊加。
       - halftone：高斯凸點規則陣列。
       - noise   ：白噪聲 FFT 帶通濾波。
    4. _shape_spectrum 套用 [0.3, 0.5] 目標頻段，統一各 type 頻譜輪廓。
    5. 廣播至 RGB 三通道：perturbation = pattern[:,:,None] * opacity * MAX_TEXTURE_AMP。
    6. result = clip(image + perturbation, 0, 255).astype(uint8)。

    frequency 統一映射公式
    -----------------------
        freq_norm = 0.3 + frequency * 0.2
    - frequency = 0.0 → freq_norm = 0.30（粗紋理）
    - frequency = 0.5 → freq_norm = 0.40（預設）
    - frequency = 1.0 → freq_norm = 0.50（細紋理）

    各 pattern 使用此 freq_norm：
    - moire   ：k = freq_norm * π（空間角頻率）
    - halftone：d = max(2, round(1 / freq_norm))（grid spacing）
    - noise   ：band = (max(0.1, freq_norm − 0.1), min(0.5, freq_norm + 0.1))

    為何採同一 pattern 廣播至 RGB（而非三通道獨立）
    -----------------------------------------------
    同一 pattern 廣播 = 灰階亮度疊加，視覺接近紙紋/網點，使用者熟悉；
    三通道獨立會產生彩色噪點（rainbow noise），對線稿色彩純度造成可見
    干擾。本實作以視覺無損優先（PRD §5.3）。

    Parameters
    ----------
    image:
        uint8 RGB ndarray，shape (H, W, 3)。
    texture_type:
        'moire'（預設）、'halftone' 或 'noise'。
    opacity:
        紋理不透明度，[0.0, 1.0]，PRD 建議 0.03–0.08。
        opacity ≤ 0 觸發 fast-path，直接回傳輸入副本。
    frequency:
        紋理頻率細粗度，[0.0, 1.0]，預設 0.5。見上方映射公式。
    seed:
        亂數種子；相同 (image, params, seed) → 相同輸出。

    Returns
    -------
    np.ndarray
        uint8 RGB，shape 與輸入相同。

    Raises
    ------
    ValueError
        image 格式不符、texture_type 非法、opacity/frequency 不在 [0, 1]。

    Examples
    --------
    >>> import numpy as np
    >>> img = np.random.default_rng(0).integers(0, 256, (256, 256, 3), dtype=np.uint8)
    >>> out = apply_texture_pollution(img, texture_type='moire', opacity=0.05, seed=42)
    >>> out.shape, out.dtype
    ((256, 256, 3), dtype('uint8'))
    """
    _validate_input(image)

    if texture_type not in _VALID_TEXTURE_TYPES:
        raise ValueError(
            f"Invalid texture_type {texture_type!r}; "
            f"expected one of {_VALID_TEXTURE_TYPES}."
        )
    if not (0.0 <= opacity <= 1.0):
        raise ValueError(f"opacity must be in [0, 1], got {opacity}.")
    if not (0.0 <= frequency <= 1.0):
        raise ValueError(f"frequency must be in [0, 1], got {frequency}.")

    if opacity <= 0.0:
        return image.copy()

    h, w = image.shape[:2]
    rng = np.random.default_rng(seed)

    if texture_type == "moire":
        pattern = _generate_moire_pattern((h, w), frequency, rng)
    elif texture_type == "halftone":
        pattern = _generate_halftone_pattern((h, w), frequency, rng)
    else:  # noise
        freq_norm = _frequency_to_norm(frequency)
        freq_band = (max(0.1, freq_norm - 0.1), min(0.5, freq_norm + 0.1))
        pattern = _generate_spectral_noise((h, w), freq_band, rng)

    pattern = _shape_spectrum(pattern, _TARGET_BAND)

    perturbation = pattern[:, :, np.newaxis] * opacity * _MAX_TEXTURE_AMP
    result_f = image.astype(np.float32) + perturbation.astype(np.float32)
    return np.clip(result_f, 0.0, 255.0).astype(np.uint8)
