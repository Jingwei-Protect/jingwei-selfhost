"""Blur bar v2 — irreversible Gaussian blur strip with hue pollution bleed.

Pure Gaussian blur can be "filled in" by modern AI inpainters — they simply
hallucinate plausible content from surrounding context.  Three countermeasures
make AI reconstruction produce visibly wrong results:

1. **Hue pollution bleed** — shift the hue of the blur bar *and* bleed the
   shifted colors 10-30 px into the surrounding clean region.  When the AI
   samples context pixels for inpainting, it reads polluted colors and
   generates a color-inaccurate result.

2. **Irregular edges** — the bar boundary is a sine-wave wobble instead of
   a crisp rectangle.  AI mask detection struggles with non-rectangular
   regions, leaving visible artifacts at the boundary.

3. **Noise texture overlay** — after blurring, a faint noise texture is
   composited so the blurred strip doesn't look like a "clean inpaint
   invitation" — it looks like deliberate artistic content.

Uses OpenCV + Pillow + numpy.  No deep-learning dependencies.
"""

from __future__ import annotations

from typing import Literal

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from core.text_fonts import get_text_font as _get_font

Position = Literal[
    "below_face", "waist", "bottom", "custom",
]

_SIGMA_MIN: int = 3
_SIGMA_MAX: int = 40
_WIDTH_RATIO_MIN: float = 0.20
_WIDTH_RATIO_MAX: float = 1.00
_HEIGHT_RATIO_MIN: float = 0.02
_HEIGHT_RATIO_MAX: float = 0.30
_HUE_BLEED_PX_MIN: int = 6
_HUE_BLEED_PX_MAX: int = 40
_HUE_SHIFT_MIN: int = 15
_HUE_SHIFT_MAX: int = 60
_WOBBLE_AMPLITUDE_RATIO: float = 0.25
_WOBBLE_PERIODS: float = 5.0


def _validate_inputs(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 32 or image.shape[1] < 32:
        raise ValueError(
            f"Image must be at least 32x32, got {image.shape[:2]}."
        )


def _compute_bar_rect(
    img_h: int, img_w: int,
    position: Position,
    x_ratio: float,
    y_ratio: float,
    width_ratio: float,
    height_ratio: float,
    face_rects: list[tuple[int, int, int, int]],
) -> tuple[int, int, int, int]:
    """Return (x, y, w, h) of the blur bar in pixel coordinates."""
    wr = float(np.clip(width_ratio, _WIDTH_RATIO_MIN, _WIDTH_RATIO_MAX))
    hr = float(np.clip(height_ratio, _HEIGHT_RATIO_MIN, _HEIGHT_RATIO_MAX))
    bar_w = int(img_w * wr)
    bar_h = max(8, int(img_h * hr))
    bar_x = (img_w - bar_w) // 2

    if position == "below_face":
        if face_rects:
            fx, fy, fw, fh = face_rects[0]
            bar_y = min(img_h - bar_h, fy + fh + max(4, fh // 6))
        else:
            bar_y = int(img_h * 0.38)
    elif position == "waist":
        bar_y = int(img_h * 0.52)
    elif position == "bottom":
        bar_y = int(img_h * 0.82)
    elif position == "custom":
        bar_x = int(np.clip(x_ratio, 0.0, 1.0) * (img_w - bar_w))
        bar_y = int(np.clip(y_ratio, 0.0, 1.0) * (img_h - bar_h))
    else:
        bar_y = int(img_h * 0.52)

    bar_x = max(0, min(bar_x, img_w - bar_w))
    bar_y = max(0, min(bar_y, img_h - bar_h))
    bar_w = min(bar_w, img_w - bar_x)
    bar_h = min(bar_h, img_h - bar_y)
    return bar_x, bar_y, bar_w, bar_h


def _make_wobble_mask(
    img_h: int, img_w: int,
    bx: int, by: int, bw: int, bh: int,
    bleed_px: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Create a float32 mask [0..1] with sine-wave irregular edges.

    The mask has value 1.0 inside the bar core and tapers to 0.0 over
    ``bleed_px`` pixels outside the boundary.  The boundary itself wobbles
    as a sine wave so it's not a simple rectangle.
    """
    mask = np.zeros((img_h, img_w), dtype=np.float32)
    amp = max(2, int(bh * _WOBBLE_AMPLITUDE_RATIO))
    phase = rng.uniform(0, 2 * np.pi)
    periods = _WOBBLE_PERIODS + rng.uniform(-1.0, 1.0)

    xs = np.arange(bw)
    top_wobble = (amp * np.sin(2 * np.pi * periods * xs / bw + phase)).astype(int)
    bot_wobble = (amp * np.sin(2 * np.pi * periods * xs / bw + phase + np.pi * 0.7)).astype(int)

    for col_idx in range(bw):
        x = bx + col_idx
        if x < 0 or x >= img_w:
            continue
        y_top = by + top_wobble[col_idx]
        y_bot = by + bh + bot_wobble[col_idx]
        y_top = max(0, min(y_top, img_h - 1))
        y_bot = max(0, min(y_bot, img_h - 1))
        if y_top < y_bot:
            mask[y_top:y_bot, x] = 1.0

    if bleed_px > 0:
        k = bleed_px * 2 + 1
        bleed_mask = cv2.GaussianBlur(mask, (k, k), sigmaX=bleed_px * 0.5)
        mask = np.maximum(mask, bleed_mask)
        mask = np.clip(mask, 0.0, 1.0)

    return mask


def _apply_hue_shift(
    image: np.ndarray,
    mask: np.ndarray,
    hue_shift: int,
) -> np.ndarray:
    """Shift hue in HSV space wherever mask > 0, proportional to mask value."""
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    h = hsv[:, :, 0].astype(np.int16)
    h += (mask * hue_shift).astype(np.int16)
    hsv[:, :, 0] = (h % 180).astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)


def _render_text_on_bar(
    bar_region: np.ndarray,
    text: str,
    font_size: int | None = None,
) -> np.ndarray:
    """Draw centred white text with a dark halo onto the blurred bar region."""
    h, w = bar_region.shape[:2]
    if not text.strip():
        return bar_region

    if font_size is None:
        font_size = max(10, min(h * 2 // 3, w // max(1, len(text))))
    font = _get_font(font_size, text)

    pil = Image.fromarray(bar_region)
    draw = ImageDraw.Draw(pil)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (w - tw) // 2
    ty = (h - th) // 2

    shadow_c = (0, 0, 0)
    main_c = (255, 255, 255)
    for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1), (0, 0)]:
        c = shadow_c if (dx, dy) != (0, 0) else main_c
        draw.text((tx + dx, ty + dy), text, font=font, fill=c)

    return np.array(pil, dtype=np.uint8)


def apply_blur_bar_from_mask(
    image: np.ndarray,
    mask: np.ndarray,
    *,
    text: str = "",
    blur_sigma: int = 12,
    hue_shift: int = 35,
    hue_bleed_px: int = 20,
    noise_intensity: float = 0.06,
    seed: int = 42,
) -> np.ndarray:
    """Apply blur + hue pollution on a user-painted float mask in [0, 1]."""
    _validate_inputs(image)
    rng = np.random.default_rng(seed)
    sigma = int(np.clip(blur_sigma, _SIGMA_MIN, _SIGMA_MAX))
    h_shift = int(np.clip(hue_shift, _HUE_SHIFT_MIN, _HUE_SHIFT_MAX))
    bleed = int(np.clip(hue_bleed_px, _HUE_BLEED_PX_MIN, _HUE_BLEED_PX_MAX))
    noise_str = float(np.clip(noise_intensity, 0.0, 0.20))

    img_h, img_w = image.shape[:2]
    if mask.shape[:2] != (img_h, img_w):
        mask = cv2.resize(mask.astype(np.float32), (img_w, img_h), interpolation=cv2.INTER_LINEAR)
    mask = np.clip(mask.astype(np.float32), 0.0, 1.0)
    if bleed > 0:
        k = bleed * 2 + 1
        mask = cv2.GaussianBlur(mask, (k, k), sigmaX=bleed * 0.5)
        mask = np.clip(mask, 0.0, 1.0)

    if float(mask.max()) < 0.01:
        return image.copy()

    out = image.copy()
    k = sigma * 2 + 1
    blurred_full = cv2.GaussianBlur(out, (k, k), sigmaX=sigma, sigmaY=sigma)
    core_mask = (mask >= 0.5).astype(np.float32)
    core_3ch = core_mask[:, :, np.newaxis]
    out = (out.astype(np.float32) * (1.0 - core_3ch)
           + blurred_full.astype(np.float32) * core_3ch)
    out = np.clip(out, 0, 255).astype(np.uint8)

    if noise_str > 0:
        noise = rng.standard_normal((img_h, img_w, 3)) * (noise_str * 255)
        out = np.clip(out.astype(np.float32) + noise * core_3ch, 0, 255).astype(np.uint8)

    sign = 1 if rng.integers(2) == 0 else -1
    hsv_shift = (h_shift * sign) // 2
    out = _apply_hue_shift(out, mask, hsv_shift)

    if text.strip() and np.any(core_mask > 0.5):
        ys, xs = np.where(core_mask > 0.5)
        cy, cx = int(ys.mean()), int(xs.mean())
        bh = max(8, int(np.sqrt((ys.max() - ys.min() + 1) * (xs.max() - xs.min() + 1)) * 0.35))
        bw = max(16, int((xs.max() - xs.min() + 1) * 0.9))
        bx = max(0, min(cx - bw // 2, img_w - bw))
        by = max(0, min(cy - bh // 2, img_h - bh))
        bar_slice = out[by:by + bh, bx:bx + bw].copy()
        bar_slice = _render_text_on_bar(bar_slice, text.strip())
        out[by:by + bh, bx:bx + bw] = bar_slice

    return out


def apply_blur_bar(
    image: np.ndarray,
    *,
    text: str = "",
    position: Position = "below_face",
    x_ratio: float = 0.0,
    y_ratio: float = 0.5,
    width_ratio: float = 0.80,
    height_ratio: float = 0.07,
    blur_sigma: int = 12,
    hue_shift: int = 35,
    hue_bleed_px: int = 20,
    noise_intensity: float = 0.06,
    seed: int = 42,
) -> np.ndarray:
    """Apply an irreversible blur strip with hue pollution and irregular edges.

    Parameters
    ----------
    image:
        uint8 RGB, shape ``(H, W, 3)``.
    text:
        Optional text rendered on top of the bar (e.g. artist signature).
    position:
        ``"below_face"`` / ``"waist"`` / ``"bottom"`` / ``"custom"``.
    x_ratio, y_ratio:
        Only used when ``position="custom"``.
    width_ratio:
        Bar width as fraction of image width, clamped to [0.20, 1.0].
    height_ratio:
        Bar height as fraction of image height, clamped to [0.02, 0.30].
    blur_sigma:
        Gaussian blur kernel sigma, clamped to [3, 40].
    hue_shift:
        Degrees to shift hue in the bar + bleed zone (HSV scale 0-180,
        so this value is halved internally).  Clamped to [15, 60].
    hue_bleed_px:
        How many pixels the hue pollution bleeds outside the bar boundary.
        Clamped to [6, 40].
    noise_intensity:
        Strength of the noise texture overlaid on the blurred bar.
        0.0 = no noise, 0.10 = moderate.  Clamped to [0.0, 0.20].
    seed:
        RNG seed for wobble pattern and noise.

    Returns
    -------
    np.ndarray
        uint8 RGB, same shape as input.
    """
    _validate_inputs(image)
    rng = np.random.default_rng(seed)
    sigma = int(np.clip(blur_sigma, _SIGMA_MIN, _SIGMA_MAX))
    h_shift = int(np.clip(hue_shift, _HUE_SHIFT_MIN, _HUE_SHIFT_MAX))
    bleed = int(np.clip(hue_bleed_px, _HUE_BLEED_PX_MIN, _HUE_BLEED_PX_MAX))
    noise_str = float(np.clip(noise_intensity, 0.0, 0.20))

    img_h, img_w = image.shape[:2]
    # Lazy import: auto bar placement may use Haar; painted-mask path never does.
    from core.face_shield import _detect_faces

    face_rects = _detect_faces(image)
    bx, by, bw, bh = _compute_bar_rect(
        img_h, img_w,
        position, x_ratio, y_ratio,
        width_ratio, height_ratio,
        face_rects,
    )

    if bw < 4 or bh < 4:
        return image.copy()

    out = image.copy()

    # 1) Build irregular wobble mask with bleed zone
    mask = _make_wobble_mask(img_h, img_w, bx, by, bw, bh, bleed, rng)

    # 2) Gaussian blur: only the core bar region (where mask == 1.0)
    k = sigma * 2 + 1
    blurred_full = cv2.GaussianBlur(out, (k, k), sigmaX=sigma, sigmaY=sigma)
    core_mask = (mask >= 0.95).astype(np.float32)
    core_3ch = core_mask[:, :, np.newaxis]
    out = (out.astype(np.float32) * (1.0 - core_3ch)
           + blurred_full.astype(np.float32) * core_3ch)
    out = np.clip(out, 0, 255).astype(np.uint8)

    # 3) Noise texture on the blurred core
    if noise_str > 0:
        noise = rng.standard_normal((img_h, img_w, 3)) * (noise_str * 255)
        noise_contribution = noise * core_3ch
        out = np.clip(
            out.astype(np.float32) + noise_contribution, 0, 255
        ).astype(np.uint8)

    # 4) Hue pollution: apply to the full mask (core + bleed zone)
    #    The sign alternates per seed for variety.
    sign = 1 if rng.integers(2) == 0 else -1
    hsv_shift = (h_shift * sign) // 2  # OpenCV HSV hue is 0-179
    out = _apply_hue_shift(out, mask, hsv_shift)

    # 5) Render text on the bar core
    if text.strip():
        bar_slice = out[by : by + bh, bx : bx + bw].copy()
        bar_slice = _render_text_on_bar(bar_slice, text.strip())
        out[by : by + bh, bx : bx + bw] = bar_slice

    return out
