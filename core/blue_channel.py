"""M3：藍色通道棋盤擾動模組。

利用人眼對藍色（S-cone）靈敏度低約 10 倍的視覺感知特性，
對影像的 B 通道注入以 2×2 cell 為基礎的棋盤結構擾動，
R、G 通道完全不改動。

棋盤圖在頻域為 Nyquist 頻率附近的結構化尖峰，比 i.i.d. 噪聲更難被
AI 前處理的均值濾波消除；per-cell 隨機符號翻轉使全域圖案不可預測，
防止對手以已知圖案過濾。

本模組不依賴任何深度學習框架，僅使用 numpy。
"""

from __future__ import annotations

import math

import numpy as np

# 藍色通道固定擾動上限（像素值）。
# 人眼 S-cone 的 JND 約為 6–8 LSB；5.0 低於此門檻，
# 確保 PSNR > 42 dB（PRD §6.4 輕度門檻）。
# 若測試失敗請回報實際 PSNR，不自動調整此常數。
_MAX_BLUE_DELTA: float = 5.0

# 棋盤 cell 大小（像素）
_CELL_SIZE: int = 2


def _validate_input(image: np.ndarray) -> None:
    """驗證輸入影像格式，不符合時 raise ValueError。

    接受條件（均為設計決策，非疏漏）：
    - dtype 必須為 uint8。
    - shape 必須為 (H, W, 3)。
    - H ≥ 8 且 W ≥ 8。

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


def _build_checkerboard(
    h: int,
    w: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """建構 2×2 cell 棋盤擾動圖案，範圍 {-1, +1}。

    建構流程：
    1. 基礎棋盤：`base[i, j] = +1 if (i//2 + j//2) % 2 == 0 else -1`
       （以 2×2 cell 為單位交替正負）。
    2. 隨機符號翻轉：對每個 cell (ci, cj) 生成一個 ±1 符號，
       使全域圖案偽隨機而局部仍維持棋盤結構。
    3. `pattern = base × signs_expanded`。

    注意：`np.repeat` 展開後若 H 或 W 為奇數，需以 `[:h, :w]` 裁切
    至確切尺寸，避免 shape mismatch。

    2×2 cell 選取理由：
    - 1×1（像素級）等同 i.i.d. 噪聲，局部可相消。
    - 2×2 使擾動頻率落在 SD VAE encoder 步進卷積（stride-2）最敏感頻段。
    - 4×4 頻率過低，肉眼可察覺有色色斑。

    Parameters
    ----------
    h, w:
        目標影像高度與寬度。
    rng:
        已初始化的 numpy Generator，由呼叫端傳入以確保確定性。

    Returns
    -------
    np.ndarray
        float32 擾動圖，shape (h, w)，值域 {-1.0, +1.0}。
    """
    n_cells_h = math.ceil(h / _CELL_SIZE)
    n_cells_w = math.ceil(w / _CELL_SIZE)

    # 基礎棋盤（cell 層級）
    ci = np.arange(n_cells_h)
    cj = np.arange(n_cells_w)
    base_cells = np.where((ci[:, None] + cj[None, :]) % 2 == 0, 1.0, -1.0)

    # 每個 cell 的隨機符號翻轉
    signs = rng.choice(np.array([-1.0, 1.0]), size=(n_cells_h, n_cells_w))

    pattern_cells = base_cells * signs

    # 將 cell 展開至像素層級
    pattern = np.repeat(np.repeat(pattern_cells, _CELL_SIZE, axis=0), _CELL_SIZE, axis=1)

    # 裁切至確切尺寸（處理 H 或 W 為奇數的情況）
    return pattern[:h, :w].astype(np.float32)


def apply_blue_channel_perturbation(
    image: np.ndarray,
    strength: float = 0.5,
    seed: int = 42,
) -> np.ndarray:
    """M3：對影像的 B 通道施加棋盤擾動，R、G 通道不改動。

    演算法概述
    ----------
    1. 驗證輸入（uint8 RGB，H×W×3，H≥8，W≥8）。
    2. 提取 B 通道（image[:, :, 2]）。
    3. 建構 2×2 cell 棋盤擾動圖（值域 {-1, +1}），per-cell 符號以 seed 偽隨機翻轉。
    4. perturbation = pattern × strength × MAX_BLUE_DELTA（MAX_BLUE_DELTA = 5.0）。
    5. B_new = clip(B + perturbation, 0, 255)。
    6. 複製原始影像，僅替換 B 通道，回傳 uint8 RGB。

    僅修改 B 通道的理由
    --------------------
    人眼 S-cone（藍色）受體的 JND（Just Noticeable Difference）約為 6–8 LSB，
    比紅/綠高約 10 倍；相同像素改動量在 B 通道的視覺代價最小，
    最大 ±5 pixel 擾動仍低於 JND，保持 PSNR > 42 dB。

    Parameters
    ----------
    image:
        輸入影像，必須為 uint8 RGB ndarray，shape (H, W, 3)。
        僅接受 uint8；float32 / BGR / 灰階等均由設計拒絕。
    strength:
        擾動強度，範圍 [0.0, 1.0]。
        0.0 → 幾乎無變化（PSNR > 60 dB）；
        0.5 → 中度（PSNR > 42 dB，PRD 輕度門檻）；
        1.0 → 最大擾動（±5 pixel on B channel）。
    seed:
        亂數種子，確保確定性輸出。
        確定性保證：相同 (image, strength, seed) → 相同輸出。

    Returns
    -------
    np.ndarray
        擾動後影像，uint8 RGB，shape 與輸入完全相同。
        R、G 通道逐像素與輸入相同；B 通道已加入棋盤擾動。

    Raises
    ------
    ValueError
        輸入 dtype 非 uint8、shape 非 (H, W, 3)，或 H/W < 8。

    Examples
    --------
    >>> import numpy as np
    >>> img = np.random.default_rng(0).integers(0, 256, (256, 256, 3), dtype=np.uint8)
    >>> out = apply_blue_channel_perturbation(img, strength=0.5, seed=42)
    >>> out.shape, out.dtype
    ((256, 256, 3), dtype('uint8'))
    """
    _validate_input(image)

    h, w = image.shape[:2]
    rng = np.random.default_rng(seed)

    pattern = _build_checkerboard(h, w, rng)
    perturbation = pattern * strength * _MAX_BLUE_DELTA

    b = image[:, :, 2].astype(np.float32)
    b_new = np.clip(b + perturbation, 0.0, 255.0).astype(np.uint8)

    result = image.copy()
    result[:, :, 2] = b_new
    return result
