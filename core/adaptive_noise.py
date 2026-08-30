"""M2：自適應空間噪聲模組。

根據影像的局部像素變異量，將混合噪聲（Gaussian + Perlin-like）集中
注入至紋理豐富的高方差區域，對平滑區域幾乎不造成影響。

與 M1（DCT 頻域擾動）互補：
- M1 在頻域的中高頻係數注入固定幅度擾動（全域、區塊結構）。
- M2 在像素域以內容感知方式加噪（連續過渡、語意邊界集中）。

兩者組合能更有效干擾 SD VAE encoder 對影像的解讀，同時維持
視覺品質（PSNR ≥ 38 dB，PRD §6.4 中度門檻）。

本模組不依賴任何深度學習框架，僅使用 numpy、opencv-python。
"""

from __future__ import annotations

import cv2
import numpy as np

# 像素域固定擾動上限。
# strength=0.3（PRD 中度預設）時，高方差像素最大注入 = 0.3 × 12.0 = 3.6。
# 若 PSNR 測試未通過，請回報實際數值後由維護者決定是否調整。
_MAX_NOISE: float = 12.0

# Perlin-like 低解析度縮放比例（H/8 × W/8）
_PERLIN_SCALE: int = 8

# Gaussian / Perlin-like 混合比例
_GAUSS_WEIGHT: float = 0.7
_PERLIN_WEIGHT: float = 0.3

# 變異量圖有效門檻：max_var < 此值視為「幾乎無紋理」，回傳全零 map
_VAR_THRESHOLD: float = 1.0


def _validate_input(image: np.ndarray) -> None:
    """驗證輸入影像格式，不符合時 raise ValueError。

    接受條件（均為設計決策，非疏漏）：
    - dtype 必須為 uint8；float32 / float64 等均拒絕，避免呼叫端
      誤傳未正規化的影像。
    - shape 必須為 (H, W, 3)；灰階（2-D）與 4 通道（RGBA）均拒絕。
    - H ≥ 8 且 W ≥ 8；極小影像應由呼叫端先放大。

    Parameters
    ----------
    image:
        待驗證的 numpy 陣列。

    Raises
    ------
    ValueError
        輸入不符合上述任一條件。
    """
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
            f"Image dimensions must be at least 8×8, got {h}×{w}. "
            "Resize the image before calling this function."
        )


def _compute_variance_map(gray: np.ndarray) -> np.ndarray:
    """計算以 7×7 box filter 為基礎的局部像素變異量圖，正規化至 [0, 1]。

    計算方式（利用 Var(X) = E[X²] - E[X]² 避免雙次掃描）：
        mean    = boxFilter(gray, 7×7)
        mean_sq = boxFilter(gray², 7×7)
        var     = mean_sq - mean²
        var     = clip(var, 0)     # 消除浮點數值負數

    Box filter 核心大小選取（7×7）：
    - 5×5：鄰域過小，邊緣估計噪聲大，紋理邊界不穩定。
    - 7×7：覆蓋半徑 3，足以捕捉筆觸、陰影；與 Harris 角點偵測慣例一致。
    - 9×9：過度平滑，噪聲「外溢」至視覺平坦區。

    正規化：
        max_var = percentile(var, 99)   # 排除離群像素
        若 max_var < 1.0 → 回傳全零 map
        否則 → var_norm = clip(var, 0, max_var) / max_var

    max_var 門檻使用 1.0（而非 epsilon）：防止輕微 JPEG 偽影
    （max_var ≈ 0.5）被全域放大，在視覺近平坦的區域造成意外噪聲。

    Parameters
    ----------
    gray:
        float32 灰階通道，shape (H, W)，值域 [0, 255]。

    Returns
    -------
    np.ndarray
        float32 變異量圖，shape (H, W)，範圍 [0, 1]。
        若影像幾乎無紋理（max_var < 1.0），回傳全零陣列。
    """
    gray_sq = gray ** 2

    # boxFilter ddepth=-1 表示輸出與輸入相同 dtype（float32）
    mean = cv2.boxFilter(gray, ddepth=-1, ksize=(7, 7))
    mean_sq = cv2.boxFilter(gray_sq, ddepth=-1, ksize=(7, 7))

    var = mean_sq - mean ** 2
    var = np.clip(var, 0.0, None)

    max_var = float(np.percentile(var, 99))
    if max_var < _VAR_THRESHOLD:
        return np.zeros_like(var, dtype=np.float32)

    var_norm = np.clip(var, 0.0, max_var) / max_var
    return var_norm.astype(np.float32)


def _generate_mixed_noise(
    h: int,
    w: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """生成 Gaussian（0.7）與 Perlin-like（0.3）的混合噪聲。

    Gaussian 分量：
        i.i.d. N(0, 1)，在高頻段製造擾動，與 M1 DCT 互補。

    Perlin-like 分量（以低解析度 + bicubic upsample 近似）：
        1. 在 H/8 × W/8 解析度生成隨機噪聲。
        2. 以 cv2.INTER_CUBIC 放大至 H × W（注意 dsize 為 (w, h)）。
        3. 逐通道正規化至零均值、單位標準差（消除 bicubic 過衝）。
    引入空間相關性，模擬天然紋理的低頻分佈，使 VAE encoder 更難
    將其與圖像內容分離。

    混合：noise = 0.7 × gaussian + 0.3 × perlin_like

    Parameters
    ----------
    h, w:
        目標影像高度與寬度（像素）。
    rng:
        已初始化的 numpy Generator，由呼叫端傳入以確保確定性。

    Returns
    -------
    np.ndarray
        float32 噪聲陣列，shape (H, W, 3)，大致呈 N(0, ~1) 分佈。
    """
    # Gaussian 分量
    gaussian = rng.standard_normal((h, w, 3)).astype(np.float32)

    # Perlin-like 分量：低解析度 → bicubic 放大
    lh = max(1, h // _PERLIN_SCALE)
    lw = max(1, w // _PERLIN_SCALE)
    low_res = rng.standard_normal((lh, lw, 3)).astype(np.float32)

    perlin = np.empty((h, w, 3), dtype=np.float32)
    for c in range(3):
        upsampled = cv2.resize(
            low_res[:, :, c],
            dsize=(w, h),  # cv2 dsize = (width, height)
            interpolation=cv2.INTER_CUBIC,
        )
        # 逐通道正規化消除 bicubic 過衝
        std = upsampled.std()
        if std > 1e-8:
            upsampled = (upsampled - upsampled.mean()) / std
        perlin[:, :, c] = upsampled

    noise = _GAUSS_WEIGHT * gaussian + _PERLIN_WEIGHT * perlin
    return noise


def apply_adaptive_noise(
    image: np.ndarray,
    strength: float = 0.3,
    seed: int = 42,
) -> np.ndarray:
    """M2：依局部變異量對影像施加自適應空間噪聲，保護作品抵抗 AI 改圖工具。

    演算法概述
    ----------
    1. 驗證輸入（uint8 RGB，H×W×3，H≥8，W≥8）。
    2. 轉換為 float32 工作副本。
    3. 轉灰階，以 7×7 box filter 計算局部變異量圖，正規化至 [0, 1]。
    4. 以種子 rng 一次性生成 Gaussian + Perlin-like 混合噪聲（shape H×W×3）。
    5. 加權注入：
           perturbation = noise × var_map[:,:,None] × strength × MAX_NOISE
    6. result = clip(float_img + perturbation, 0, 255).astype(uint8)

    擾動量公式
    ----------
        perturbation = noise × var_weight × strength × MAX_NOISE
        noise ~ 0.7·N(0,1) + 0.3·Perlin-like(0,1)
        MAX_NOISE = 12.0

    採每像素變異量（而非每區塊）的原因：
    M1 已採 8×8 區塊結構；若 M2 同樣以區塊為單位，兩層擾動的
    方格格柵在高強度下會形成明顯視覺偽影（8px 週期方格）。
    每像素圖配合 7×7 box filter 的平滑過渡，使噪聲邊界連續，
    並天然集中在語意邊界（筆觸、陰影輪廓）——ControlNet 最依賴的特徵。

    Parameters
    ----------
    image:
        輸入影像，必須為 uint8 RGB ndarray，shape (H, W, 3)。
        僅接受 uint8；float32 / BGR / 灰階等均由設計拒絕。
    strength:
        擾動強度，範圍 [0.0, 1.0]。
        0.0 → 幾乎無變化（PSNR > 60 dB，僅 float32 往返捨入誤差）；
        0.3 → 中度保護（PSNR ≥ 38 dB，PRD §6.4 中度配方預設）；
        1.0 → 最大擾動。
    seed:
        亂數種子，確保確定性輸出。
        確定性保證：相同 (image, strength, seed) → 相同輸出，
        與作業系統、Python 版本或執行次序無關。

    Returns
    -------
    np.ndarray
        擾動後影像，uint8 RGB，shape 與輸入完全相同。

    Raises
    ------
    ValueError
        輸入 dtype 非 uint8、shape 非 (H, W, 3)，或 H/W < 8。

    Notes
    -----
    strength=0 時 perturbation 為零，輸出與輸入幾乎完全相同（允許
    float32 往返引入的 ±1 pixel 捨入誤差，PSNR > 60 dB）。

    Examples
    --------
    >>> import numpy as np
    >>> img = np.random.default_rng(0).integers(0, 256, (256, 256, 3), dtype=np.uint8)
    >>> out = apply_adaptive_noise(img, strength=0.3, seed=42)
    >>> out.shape, out.dtype
    ((256, 256, 3), dtype('uint8'))
    """
    _validate_input(image)

    h, w = image.shape[:2]
    float_img = image.astype(np.float32)

    # 計算局部變異量圖（以灰階計算，廣播至三通道）
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)
    var_map = _compute_variance_map(gray)  # shape (H, W)

    # 生成混合噪聲
    rng = np.random.default_rng(seed)
    noise = _generate_mixed_noise(h, w, rng)  # shape (H, W, 3)

    # 加權注入
    perturbation = noise * var_map[:, :, np.newaxis] * strength * _MAX_NOISE
    result_f = float_img + perturbation

    return np.clip(result_f, 0.0, 255.0).astype(np.uint8)
