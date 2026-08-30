"""M7：邊緣梯度方向干擾模組。

對影像強邊緣處沿「梯度的垂直方向」（即邊緣切線方向）施加 sub-pixel
位移擾動，使 AI 結構引導模型（ControlNet、IP-Adapter 等）對邊緣
方向的判讀產生微小偏移；邊緣位置幾乎不變，人眼難以察覺。

整體流程：
    Sobel → magnitude / direction → mask (magnitude > threshold)
    → perpendicular sub-pixel offset → cv2.remap (INTER_LINEAR)

法律聲明（PRD §5.5）：
本模組所有演算法為獨立設計，僅參考公開學術文獻中之對抗擾動概念，
未引用 Mist / Glaze / Nightshade 任何程式碼；所有實作僅使用傳統
信號處理（numpy / opencv-python），不依賴任何深度學習框架。
"""

# Legal notice (PRD §5.5):
# Algorithm independently designed. Inspired by adversarial perturbation
# concepts in academic literature. No code from Mist / Glaze / Nightshade
# was referenced. All implementations use traditional signal processing
# (numpy / opencv-python) without any deep learning framework.

from __future__ import annotations

import cv2
import numpy as np

# 邊緣最大位移（pixel）。
# 預設 strength=0.3 時最大位移 = 0.3 × 3.0 = 0.9 pixel（sub-pixel），
# 透過 INTER_LINEAR 平滑分散；PSNR 預估 > 36 dB。
# strength=1.0 對應 3.0 pixel，屬 PRD §6.4 強度模式（PSNR ≈ 32 dB）。
_MAX_GRADIENT_SHIFT: float = 3.0


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


def _compute_gradients(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """以 Sobel 算子計算邊緣強度（magnitude）與方向（direction）。

    流程：
        gx = Sobel(gray, dx=1, dy=0, ksize=3)
        gy = Sobel(gray, dx=0, dy=1, ksize=3)
        magnitude = sqrt(gx² + gy²)
        direction = atan2(gy, gx)        # 弧度，[-π, π]

    回傳 2-tuple（gx、gy 為內部中間量，刻意不對外暴露——
    後續模組不應依賴 gx/gy，需要邊緣資訊時請呼叫此函式取 magnitude/direction）。

    Parameters
    ----------
    gray:
        float32 灰階影像，shape (H, W)，值域 [0, 255]。

    Returns
    -------
    magnitude:
        float32 (H, W)，值域 [0, ~1020]（Sobel 3×3 理論上限約 4·255）。
    direction:
        float32 (H, W)，值域 [-π, π]。
    """
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = np.sqrt(gx * gx + gy * gy).astype(np.float32)
    direction = np.arctan2(gy, gx).astype(np.float32)
    return magnitude, direction


def _generate_edge_perturbation(
    magnitude: np.ndarray,
    direction: np.ndarray,
    threshold: float,
    strength: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """為強邊緣像素生成「垂直於梯度方向」的 sub-pixel 位移向量。

    為什麼是「垂直方向」：
    梯度向量指向影像強度增加最快的方向（即跨越邊緣的方向），
    其垂直方向則沿邊緣切線。沿切線位移：邊緣的視覺位置幾乎不變
    （人眼追蹤邊緣，僅看到「邊緣略長/略短」），但梯度方向被微微
    旋轉，足以讓 ControlNet 等結構引導模型產生錯誤的結構提示。

    位移公式：
        amount = uniform(-1, 1) * strength * MAX_GRADIENT_SHIFT  (pixel)
        perpendicular unit vector = (-sin(direction), cos(direction))
        dx = amount * (-sin(direction))
        dy = amount * cos(direction)

    Parameters
    ----------
    magnitude:
        float32 (H, W)，邊緣強度。
    direction:
        float32 (H, W)，邊緣方向（弧度）。
    threshold:
        magnitude > threshold 的像素才施加擾動。
    strength:
        [0, 1] 擾動強度。
    rng:
        Generator，控制隨機幅度。

    Returns
    -------
    dx_map, dy_map:
        float32 (H, W)，非邊緣像素為 0。
    """
    mask = magnitude > threshold
    n_edge = int(mask.sum())

    dx_map = np.zeros_like(magnitude, dtype=np.float32)
    dy_map = np.zeros_like(magnitude, dtype=np.float32)

    if n_edge == 0:
        return dx_map, dy_map

    amount = rng.uniform(-1.0, 1.0, size=n_edge).astype(np.float32)
    amount *= strength * _MAX_GRADIENT_SHIFT

    edge_dir = direction[mask]
    dx_map[mask] = amount * (-np.sin(edge_dir))
    dy_map[mask] = amount * np.cos(edge_dir)

    return dx_map, dy_map


def _apply_pixel_displacement(
    image: np.ndarray,
    dx_map: np.ndarray,
    dy_map: np.ndarray,
) -> np.ndarray:
    """依 (dx, dy) 位移映射對影像進行 sub-pixel 重採樣。

    使用 `cv2.remap` 配合 INTER_LINEAR：
    - 對 RGB 三通道自動同步處理（同一位移映射作用於三通道）。
    - INTER_CUBIC 會在邊緣產生 ringing artifact，故採線性插值。
    - 邊界外像素以 BORDER_REFLECT_101 反射補齊。

    Parameters
    ----------
    image:
        uint8 RGB (H, W, 3)。
    dx_map, dy_map:
        float32 (H, W)，水平與垂直位移（像素）。

    Returns
    -------
    np.ndarray
        uint8 RGB，shape 與輸入相同。
    """
    h, w = image.shape[:2]
    xs, ys = np.meshgrid(
        np.arange(w, dtype=np.float32),
        np.arange(h, dtype=np.float32),
    )
    map_x = (xs + dx_map).astype(np.float32)
    map_y = (ys + dy_map).astype(np.float32)

    return cv2.remap(
        image,
        map_x,
        map_y,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )


def apply_gradient_disturbance(
    image: np.ndarray,
    strength: float = 0.3,
    edge_threshold: float = 30.0,
    seed: int = 42,
) -> np.ndarray:
    """M7：對強邊緣處施加沿切線方向的 sub-pixel 位移擾動。

    演算法概述
    ----------
    1. 驗證輸入（uint8 RGB，H≥8, W≥8）。
    2. strength ≤ 0.0 fast-path：return image.copy()。
    3. 轉灰階 → Sobel → magnitude / direction。
    4. 對 magnitude > edge_threshold 的邊緣像素生成隨機 sub-pixel 位移：
           amount = uniform(-1, 1) × strength × MAX_GRADIENT_SHIFT
           dx, dy 沿（-sin(direction), cos(direction)）方向。
    5. cv2.remap（INTER_LINEAR + BORDER_REFLECT_101）套用位移。
    6. 回傳 uint8。

    位移幾何
    --------
    沿「邊緣切線方向」（梯度的垂直方向）位移：邊緣視覺位置幾乎不變，
    但梯度方向被微微旋轉，破壞 ControlNet 等結構引導模型的方向場
    估計。隨機方向位移會造成可見邊緣抖動，故不採用。

    edge_threshold 的選取
    ---------------------
    Sobel ksize=3 的 magnitude 範圍約 [0, 1020]。實測：
    平滑區 < 10、弱邊緣 10–30、強邊緣 50–200、極尖銳邊緣 > 300。
    預設 30 為「弱-強邊緣分界」：低於此值的紋理區不擾動，避免可見雜訊。

    Parameters
    ----------
    image:
        uint8 RGB ndarray，shape (H, W, 3)。
    strength:
        擾動強度，[0.0, 1.0]，預設 0.3（PRD 中度配方）。
        strength ≤ 0 觸發 fast-path（直接回傳輸入副本，零 cv2.remap 誤差）。
    edge_threshold:
        Sobel magnitude 門檻，預設 30.0；極大值（如 1000）→ 幾無邊緣
        被選中 → 輸出近似輸入。
    seed:
        亂數種子。確定性保證：相同 (image, params, seed) → 相同輸出。

    Returns
    -------
    np.ndarray
        uint8 RGB，shape 與輸入相同。

    Raises
    ------
    ValueError
        image 格式不符。

    Examples
    --------
    >>> import numpy as np
    >>> img = np.random.default_rng(0).integers(0, 256, (256, 256, 3), dtype=np.uint8)
    >>> out = apply_gradient_disturbance(img, strength=0.3, seed=42)
    >>> out.shape, out.dtype
    ((256, 256, 3), dtype('uint8'))
    """
    _validate_input(image)

    if strength <= 0.0:
        return image.copy()

    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)
    magnitude, direction = _compute_gradients(gray)

    rng = np.random.default_rng(seed)
    dx_map, dy_map = _generate_edge_perturbation(
        magnitude, direction, edge_threshold, strength, rng
    )

    return _apply_pixel_displacement(image, dx_map, dy_map)
