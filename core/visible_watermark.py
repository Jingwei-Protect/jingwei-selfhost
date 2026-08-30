"""M5：可見水印模組。

以半透明文字水印鋪設於影像上，保護畫師版權並作為視覺聲明。
文字以 30 度旋轉、固定間距重複鋪滿全圖，不可被軸對齊裁切移除。

設計決策：
- 白色文字（固定）：搭配低透明度（預設 opacity=0.1）在大多數影像
  上均可辨識；自適應顏色增加複雜度，超出 MVP 範疇。
- 30 度旋轉：對角水印無法被橫向/縱向裁切完全移除；30° 視覺平衡，
  符合業界常見版權水印慣例。
- 字型搜尋順序：跨平台嘗試系統 CJK 字型，fallback 至 PIL 預設字型。
  注意：PIL 預設字型僅支援 ASCII，非 ASCII 文字需系統安裝 CJK-capable
  TTF 字型（如 Windows msyh.ttc、Linux NotoSansCJK 等），否則顯示為方框。

本模組不依賴任何深度學習框架，僅使用 numpy、Pillow。
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from core.text_fonts import get_text_font as _get_font

_DENSITY_MULTIPLIERS = {"sparse": 8, "normal": 5, "dense": 3}
_WATERMARK_ROTATION_DEG = 30
_WATERMARK_COLOR = (255, 255, 255, 255)  # RGBA white


def _validate_input(image: np.ndarray, text: str) -> None:
    """驗證輸入影像與文字，不符合時 raise ValueError。

    Raises
    ------
    ValueError
        影像非 uint8 HxWx3、H/W < 8，或 text 為空字串。
    """
    if image.dtype != np.uint8:
        raise ValueError(
            f"Input dtype must be uint8, got {image.dtype}."
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
    if not text:
        raise ValueError("text must not be empty.")


def apply_visible_watermark(
    image: np.ndarray,
    text: str,
    opacity: float = 0.1,
    density: Literal["sparse", "normal", "dense"] = "normal",
) -> np.ndarray:
    """M5：在影像上鋪設半透明旋轉文字水印。

    演算法概述
    ----------
    1. 驗證輸入。
    2. opacity <= 0.0 時提前返回 image.copy()（fast-path，無任何 PIL 運算）。
    3. 計算 font_size = max(12, min(H, W) // 40)。
    4. 搜尋系統字型（跨平台），fallback PIL default。
    5. 計算間距：spacing = font_size × density_multiplier
       （sparse: ×8, normal: ×5, dense: ×3）。
    6. 建構旋轉 30° 的文字 tile（RGBA 透明背景，白色文字）。
    7. 以雙重迴圈將 tile 鋪滿透明 overlay，以 opacity 縮放 alpha。
    8. PIL alpha_composite 合成，轉回 uint8 RGB。

    Parameters
    ----------
    image:
        輸入影像，uint8 RGB，shape (H, W, 3)。
    text:
        水印文字；非空字串。
        非 ASCII 文字（中文/Emoji）需系統安裝 CJK-capable TTF 字型，
        否則以 PIL 預設字型顯示為方框。
    opacity:
        水印透明度，範圍 [0.0, 1.0]。
        0.0 → 完全透明（fast-path 返回原圖）；
        0.1 → 預設，輕微可見；
        1.0 → 不透明白色文字。
    density:
        水印密度，控制文字間距。
        'sparse'：間距 = font_size × 8；
        'normal'：間距 = font_size × 5（預設）；
        'dense'：間距 = font_size × 3。

    Returns
    -------
    np.ndarray
        加上水印的影像，uint8 RGB，shape 與輸入相同。

    Raises
    ------
    ValueError
        輸入格式不符或 text 為空。
    """
    _validate_input(image, text)

    # Fast-path：opacity=0 直接回傳副本，零 PIL 運算
    if opacity <= 0.0:
        return image.copy()

    h, w = image.shape[:2]
    font_size = max(12, min(h, w) // 40)
    font = _get_font(font_size, text)
    spacing = font_size * _DENSITY_MULTIPLIERS[density]

    # 建立文字 tile（RGBA 透明背景）
    # 先估算文字邊界框大小
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0] + font_size
    text_h = bbox[3] - bbox[1] + font_size

    tile = Image.new("RGBA", (text_w, text_h), (0, 0, 0, 0))
    tile_draw = ImageDraw.Draw(tile)
    tile_draw.text(
        (font_size // 2, font_size // 2),
        text,
        font=font,
        fill=_WATERMARK_COLOR,
    )
    rotated_tile = tile.rotate(_WATERMARK_ROTATION_DEG, expand=True)
    tw, th = rotated_tile.size

    # 建立透明 overlay 並鋪滿旋轉 tile
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y in range(-th, h + th, spacing):
        for x in range(-tw, w + tw, spacing):
            overlay.paste(rotated_tile, (x, y), rotated_tile)

    # 縮放 overlay 的 alpha 通道以實現 opacity 控制
    overlay_arr = np.array(overlay, dtype=np.float32)
    overlay_arr[:, :, 3] = (overlay_arr[:, :, 3] * opacity).clip(0, 255)
    overlay_scaled = Image.fromarray(overlay_arr.astype(np.uint8))

    # 合成
    base_rgba = Image.fromarray(image).convert("RGBA")
    composited = Image.alpha_composite(base_rgba, overlay_scaled)
    return np.array(composited.convert("RGB"), dtype=np.uint8)
