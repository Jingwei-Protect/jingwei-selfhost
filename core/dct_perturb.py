"""M1：DCT 頻域擾動模組。

對影像的 Y（亮度）通道進行 8×8 DCT 分塊，在中高頻係數位置
（block[3:7, 3:7]）注入固定幅度偽隨機擾動，再經 IDCT 還原。
擾動在人眼可察覺能力的門檻以下（PSNR ≥ 38 dB），但能干擾以
SD VAE encoder 為核心的 AI 改圖工具對影像的解讀。

本模組不依賴任何深度學習框架，僅使用 numpy、scipy、opencv-python。
"""

from __future__ import annotations

import cv2
import numpy as np
from scipy.fft import dctn, idctn

# DCT ortho 域固定擾動上限。
# Y 通道置中後範圍為 [-128, 127]，中頻係數典型幅值約 ±30–80。
# MAX_DELTA = 15.0 在 strength=0.5 時等效注入 7.5 單位，
# 預估 PSNR ≈ 38–44 dB；如需調整請先執行 pytest 確認後告知維護者。
_MAX_DELTA: float = 15.0

# 注入擾動的 DCT 係數位置（8×8 block 中高頻區，共 16 個係數）。
# 避開 DC 係數 [0,0]（影響整體亮度）與極高頻 [7:,7:]（效果有限）。
_FREQ_SLICE = (slice(3, 7), slice(3, 7))


def _validate_input(image: np.ndarray) -> None:
    """驗證輸入影像格式，不符合時 raise ValueError。

    接受條件（均為設計決策，非疏漏）：
    - dtype 必須為 uint8；float32 / float64 等均拒絕，避免呼叫端
      誤傳未正規化的影像。
    - shape 必須為 (H, W, 3)；灰階（2-D）與 4 通道（RGBA）均拒絕。
    - H ≥ 8 且 W ≥ 8；無法形成完整 8×8 DCT 區塊的影像應由呼叫端放大。

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


def _pad_to_multiple(
    channel: np.ndarray,
    block_size: int = 8,
) -> tuple[np.ndarray, tuple[int, int]]:
    """以 reflect 模式將通道尺寸補至 block_size 的倍數。

    填補公式（關鍵：雙重 % 確保已是倍數時 pad == 0）：

        pad_h = (block_size - h % block_size) % block_size
        pad_w = (block_size - w % block_size) % block_size
        np.pad(channel, ((0, pad_h), (0, pad_w)), mode='reflect')

    當 h 已為 block_size 的倍數時，h % block_size == 0，
    (block_size - 0) % block_size == 0，故 pad_h 正確為 0 而非 block_size。

    Parameters
    ----------
    channel:
        2-D float32 單通道陣列，shape (H, W)。
    block_size:
        區塊大小，預設 8。

    Returns
    -------
    padded:
        填補後陣列，shape (H + pad_h, W + pad_w)。
    (pad_h, pad_w):
        實際填補的像素數，供後續裁切還原。
    """
    h, w = channel.shape
    pad_h = (block_size - h % block_size) % block_size
    pad_w = (block_size - w % block_size) % block_size
    if pad_h == 0 and pad_w == 0:
        return channel, (0, 0)
    padded = np.pad(channel, ((0, pad_h), (0, pad_w)), mode="reflect")
    return padded, (pad_h, pad_w)


def _apply_perturbation_to_channel(
    y_channel: np.ndarray,
    deltas: np.ndarray,
) -> np.ndarray:
    """對填補後的 Y 通道逐 8×8 區塊執行 DCT 擾動並 IDCT 還原。

    每個區塊的處理流程（遵循 JPEG DCT 標準置中慣例）：
        1. 擷取 float32 block
        2. block -= 128              （置中至 [-128, 127]，穩定中頻係數範圍）
        3. dct_block = dctn(block, norm='ortho')
        4. dct_block[3:7, 3:7] += deltas[i, j]   （注入中高頻擾動）
        5. block = idctn(dct_block, norm='ortho')
        6. block += 128              （還原置中）
        7. 寫回輸出通道

    Parameters
    ----------
    y_channel:
        填補後的浮點 Y 通道，shape (H_pad, W_pad)；H_pad、W_pad 均為 8 的倍數。
    deltas:
        預先生成的擾動陣列，shape (n_blocks_h, n_blocks_w, 4, 4)，
        範圍 [-1, 1]（已由呼叫端乘上 strength × MAX_DELTA）。

    Returns
    -------
    np.ndarray
        擾動後的浮點 Y 通道，shape 與 y_channel 相同。
    """
    h_pad, w_pad = y_channel.shape
    output = y_channel.copy()

    n_blocks_h = h_pad // 8
    n_blocks_w = w_pad // 8

    for i in range(n_blocks_h):
        for j in range(n_blocks_w):
            r0, r1 = i * 8, i * 8 + 8
            c0, c1 = j * 8, j * 8 + 8

            block = output[r0:r1, c0:c1].copy()
            block -= 128.0

            dct_block = dctn(block, norm="ortho")
            dct_block[_FREQ_SLICE] += deltas[i, j]
            block = idctn(dct_block, norm="ortho")

            block += 128.0
            output[r0:r1, c0:c1] = block

    return output


def apply_dct_perturbation(
    image: np.ndarray,
    strength: float = 0.5,
    seed: int = 42,
) -> np.ndarray:
    """M1：對影像的 Y 通道施加 DCT 頻域擾動，保護作品抵抗 AI 改圖工具。

    演算法概述
    ----------
    1. 驗證輸入（uint8 RGB，H×W×3，H≥8，W≥8）。
    2. RGB → YCrCb（浮點精度轉換，保留 Cb、Cr 通道不動）。
    3. 以 reflect padding 將 Y 通道補至 8 的倍數。
    4. 一次性生成所有區塊的擾動量：
           rng = np.random.default_rng(seed)
           raw = rng.uniform(-1, 1, (n_blocks_h, n_blocks_w, 4, 4))
           deltas = raw * strength * MAX_DELTA   (MAX_DELTA = 15.0)
    5. 逐 8×8 區塊：置中(-128) → DCT → 注入 deltas[3:7,3:7] → IDCT → 還原(+128)。
    6. 裁切填補邊距，合併 YCrCb → RGB，clip [0,255]，轉回 uint8。

    擾動量公式（Fixed-range scaling）
    -----------------------------------
        delta = rng_sample × strength × MAX_DELTA
        rng_sample ~ Uniform(-1, 1)，MAX_DELTA = 15.0

    採固定幅度而非係數比例縮放（delta ∝ |coeff|），原因：
    高能量紋理區塊的 DCT 係數可達 ±數百，比例縮放會導致難以預測
    的 PSNR 下降；固定幅度使品質包絡與影像內容解耦，在 strength=0.5
    時各類影像均能穩定達到 PSNR ≥ 38 dB（PRD §6.4 中度門檻）。

    Parameters
    ----------
    image:
        輸入影像，必須為 uint8 RGB ndarray，shape (H, W, 3)。
        僅接受 uint8；float32 / BGR / 灰階等均由設計拒絕。
    strength:
        擾動強度，範圍 [0.0, 1.0]。
        0.0 → 幾乎無變化（PSNR > 50 dB）；
        0.5 → 中度保護（PSNR ≥ 38 dB，PRD 預設）；
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

    Examples
    --------
    >>> import numpy as np
    >>> img = np.random.default_rng(0).integers(0, 256, (256, 256, 3), dtype=np.uint8)
    >>> out = apply_dct_perturbation(img, strength=0.5, seed=42)
    >>> out.shape, out.dtype
    ((256, 256, 3), dtype('uint8'))
    """
    _validate_input(image)

    h_orig, w_orig = image.shape[:2]

    # RGB uint8 → YCrCb，以 float32 操作以避免中間截斷誤差
    ycrcb = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb).astype(np.float32)
    y_channel = ycrcb[:, :, 0]

    # 填補至 8 的倍數
    y_padded, (pad_h, pad_w) = _pad_to_multiple(y_channel)

    n_blocks_h = y_padded.shape[0] // 8
    n_blocks_w = y_padded.shape[1] // 8

    # 一次性預生成所有擾動量（確定性、高效）
    rng = np.random.default_rng(seed)
    raw_deltas = rng.uniform(-1.0, 1.0, size=(n_blocks_h, n_blocks_w, 4, 4))
    deltas = (raw_deltas * strength * _MAX_DELTA).astype(np.float32)

    # 逐區塊 DCT 擾動
    y_perturbed = _apply_perturbation_to_channel(y_padded, deltas)

    # 裁切回原始尺寸
    y_final = y_perturbed[:h_orig, :w_orig]

    # 合併通道並轉回 RGB
    ycrcb[:, :, 0] = y_final
    ycrcb_clipped = np.clip(ycrcb, 0.0, 255.0).astype(np.uint8)
    result = cv2.cvtColor(ycrcb_clipped, cv2.COLOR_YCrCb2RGB)

    return result
