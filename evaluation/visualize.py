# TODO: future refactor - extract font search to core/fontutil.py
"""保護前後對比圖輸出（PNG）：原圖 | 保護後 | 差異放大。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from evaluation.psnr_ssim import evaluate_protection

_ANNOTATION_FONT_PATHS = [
    # Windows
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/arial.ttf",
    # macOS
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    # Linux
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
]

_SEP_WIDTH = 1
_ANNOTATION_STRIP_MIN_H = 28
_FONT_SIZE = 14
# Screen-only strip. The downloaded protect image stays full resolution.
COMPARISON_DISPLAY_MAX_SIDE = 960


def _get_annotation_font(size: int = _FONT_SIZE) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _ANNOTATION_FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _to_rgb_on_white(arr: np.ndarray) -> np.ndarray:
    """Ensure uint8 HxWx3 RGB. RGBA is composited onto white."""
    if arr.ndim == 3 and arr.shape[2] == 4 and arr.dtype == np.uint8:
        alpha = arr[:, :, 3:4].astype(np.float32) / 255.0
        rgb = arr[:, :, :3].astype(np.float32)
        composited = rgb * alpha + 255.0 * (1.0 - alpha)
        return np.clip(composited, 0, 255).astype(np.uint8)
    return arr


def _validate_rgb_pair(original: np.ndarray, protected: np.ndarray) -> None:
    if original.dtype != np.uint8 or protected.dtype != np.uint8:
        raise ValueError("Images must be uint8 RGB arrays.")
    if (
        original.ndim != 3
        or protected.ndim != 3
        or original.shape[2] != 3
        or protected.shape[2] != 3
    ):
        raise ValueError(
            f"Expected HxWx3 RGB, got shapes {original.shape}, {protected.shape}."
        )
    if original.shape != protected.shape:
        raise ValueError(
            f"Shape mismatch: {original.shape} vs {protected.shape}."
        )
    h, w = original.shape[:2]
    if h < 8 or w < 8:
        raise ValueError(f"Image dimensions must be at least 8×8, got {h}×{w}.")


def _resize_rgb(arr: np.ndarray, width: int, height: int) -> np.ndarray:
    """Lanczos resize for comparison panels only."""
    return np.asarray(
        Image.fromarray(arr).resize((width, height), Image.Resampling.LANCZOS),
        dtype=np.uint8,
    )


def generate_comparison(
    original: np.ndarray,
    protected: np.ndarray,
    output_path: str,
    diff_amplification: int = 10,
    max_side: int | None = None,
) -> None:
    """輸出橫向三欄對比 PNG：[Original | Protected | Difference×k]，頂部標註指標。

    Parameters
    ----------
    original, protected:
        uint8 RGB，同 shape；**須至少 11×11** 以供 ``evaluate_protection`` 計算 SSIM。
    output_path:
        儲存路徑；**僅支援 .png**。
    diff_amplification:
        差異視覺放大倍數（預設 10）。
    max_side:
        顯示面板長邊上限。指標仍用原圖計算；``None`` 表示不縮小。
    """
    original = _to_rgb_on_white(original)
    protected = _to_rgb_on_white(protected)
    _validate_rgb_pair(original, protected)
    h, w = original.shape[:2]
    if h < 11 or w < 11:
        raise ValueError(
            "generate_comparison requires at least 11×11 for metric annotations (SSIM)."
        )

    out_p = Path(output_path)
    if out_p.suffix.lower() != ".png":
        raise ValueError(
            f"output_path must be a .png file, got suffix {out_p.suffix!r}."
        )

    metrics = evaluate_protection(original, protected)
    psnr_v = metrics["psnr"]
    psnr_s = "inf" if psnr_v == float("inf") else f"{psnr_v:.2f}"
    text = (
        f"PSNR: {psnr_s} dB | SSIM: {metrics['ssim']:.4f} | "
        f"Max diff: {metrics['max_diff']} | Mean diff: {metrics['mean_diff']:.2f}"
    )

    diff = np.abs(original.astype(np.int32) - protected.astype(np.int32))
    diff_grey = np.max(diff, axis=2)
    diff_scaled = np.clip(diff_grey * diff_amplification, 0, 255).astype(np.uint8)

    lut = np.zeros((256, 3), dtype=np.uint8)
    for i in range(256):
        t = i / 255.0
        if t < 0.25:
            s = t / 0.25
            lut[i] = [0, int(s * 80), int(s * 140)]
        elif t < 0.5:
            s = (t - 0.25) / 0.25
            lut[i] = [int(s * 60), 80 + int(s * 100), 140 + int(s * 115)]
        elif t < 0.75:
            s = (t - 0.5) / 0.25
            lut[i] = [60 + int(s * 195), 180 + int(s * 75), 255 - int(s * 55)]
        else:
            s = (t - 0.75) / 0.25
            lut[i] = [255, 255 - int(s * 55), 200 - int(s * 200)]

    diff_vis = lut[diff_scaled]

    if max_side is not None and max_side > 0:
        long_edge = max(h, w)
        if long_edge > max_side:
            scale = max_side / long_edge
            new_w = max(1, int(round(w * scale)))
            new_h = max(1, int(round(h * scale)))
            original = _resize_rgb(original, new_w, new_h)
            protected = _resize_rgb(protected, new_w, new_h)
            diff_vis = _resize_rgb(diff_vis, new_w, new_h)
            h, w = new_h, new_w

    font = _get_annotation_font()
    temp_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    strip_h = max(_ANNOTATION_STRIP_MIN_H, bbox[3] - bbox[1] + 8)

    total_w = 3 * w + 2 * _SEP_WIDTH
    total_h = strip_h + h
    canvas = Image.new("RGB", (total_w, total_h), (245, 245, 245))
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (8, max(2, (strip_h - (bbox[3] - bbox[1])) // 2)),
        text,
        fill=(20, 20, 20),
        font=font,
    )

    def _paste_panel(im_arr: np.ndarray, x0: int) -> None:
        canvas.paste(Image.fromarray(im_arr), (x0, strip_h))

    _paste_panel(original, 0)
    canvas.paste(Image.new("RGB", (_SEP_WIDTH, h), (255, 255, 255)), (w, strip_h))
    _paste_panel(protected, w + _SEP_WIDTH)
    canvas.paste(
        Image.new("RGB", (_SEP_WIDTH, h), (255, 255, 255)),
        (2 * w + _SEP_WIDTH, strip_h),
    )
    _paste_panel(diff_vis, 2 * w + 2 * _SEP_WIDTH)

    out_p.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_p, format="PNG")
