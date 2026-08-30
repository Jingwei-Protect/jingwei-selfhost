"""Emboss texture overlay — decorative relief pattern for image protection.

Three pattern types:
  diagonal   — full-coverage diagonal lines (thicker, harder to remove)
  halftone   — content-aware halftone: dot radius proportional to local
               luminance, 45° rotated grid.  Dot sizes encode the image
               itself, creating a chicken-and-egg problem for AI removal.
  crosshatch — double-diagonal cross lines (thicker than before)

Text overlay uses THREE font sizes mixed in a repeating cycle so the
author name appears at different scales — multi-scale patterns require
AI to solve several simultaneous frequency bands rather than one kernel.

Per-channel chromatic emboss (R stronger/shifted right, B shifted left)
forces AI to solve a coupled 3-channel deconvolution.

No deep-learning dependencies.  Uses numpy, Pillow, and opencv-python.
"""

from __future__ import annotations

import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from core.text_fonts import get_text_font as _get_font

# Three relative sizes for multi-scale text tiling
_TEXT_SIZE_RATIOS = (0.018, 0.030, 0.045)


def _draw_diagonal_lines(
    draw: ImageDraw.ImageDraw,
    w: int, h: int,
    spacing: int,
    line_width: int,
    color: int,
) -> None:
    diag = int(math.hypot(w, h)) + spacing
    for offset in range(-diag, diag + spacing, spacing):
        draw.line([(offset, 0), (offset + h, h)], fill=color, width=line_width)


def _draw_crosshatch(
    draw: ImageDraw.ImageDraw,
    w: int, h: int,
    spacing: int,
    line_width: int,
    color: int,
) -> None:
    diag = int(math.hypot(w, h)) + spacing
    for offset in range(-diag, diag + spacing, spacing):
        draw.line([(offset, 0), (offset + h, h)], fill=color, width=line_width)
        draw.line([(offset, 0), (offset - h, h)], fill=color, width=line_width)


def _draw_halftone(
    image_gray: np.ndarray,
    w: int, h: int,
    spacing: int,
) -> np.ndarray:
    """Content-aware halftone: dot radius ∝ local luminance (inverted).

    Grid is rotated 45° for the classic halftone look.
    Returns a uint8 (H, W) pattern array (255 = dot, 0 = background).
    """
    pat = np.zeros((h, w), dtype=np.uint8)
    pil_pat = Image.fromarray(pat)
    draw = ImageDraw.Draw(pil_pat)

    # Rotate grid 45° by using a rotated step basis
    step = spacing
    cos45 = math.cos(math.radians(45))
    sin45 = math.sin(math.radians(45))

    # Sample on a rotated lattice covering the full image
    diag = int(math.hypot(w, h))
    for i in range(-diag // step - 1, diag // step + 2):
        for j in range(-diag // step - 1, diag // step + 2):
            cx = int(i * step * cos45 - j * step * sin45 + w / 2)
            cy = int(i * step * sin45 + j * step * cos45 + h / 2)
            if cx < -step or cx > w + step or cy < -step or cy > h + step:
                continue
            # Sample luminance (clamp to image bounds)
            sx = max(0, min(w - 1, cx))
            sy = max(0, min(h - 1, cy))
            lum = float(image_gray[sy, sx]) / 255.0
            # Darker areas → larger dots (like inkprint halftone)
            max_r = max(3, spacing // 2 - 1)
            min_r = 1
            radius = int(min_r + (1.0 - lum) * (max_r - min_r))
            radius = max(1, radius)
            draw.ellipse(
                [cx - radius, cy - radius, cx + radius, cy + radius],
                fill=255,
            )

    return np.array(pil_pat, dtype=np.uint8)


def _soft_light_blend(base: np.ndarray, overlay: np.ndarray) -> np.ndarray:
    """Soft-light blending: overlay float [-1,1] onto base uint8."""
    b = base.astype(np.float32) / 255.0
    bright = overlay > 0
    result = np.where(
        bright,
        b + overlay * b * (1.0 - b),
        b + overlay * b,
    )
    return np.clip(result * 255.0, 0, 255).astype(np.uint8)


def _additive_blend(base: np.ndarray, overlay: np.ndarray, strength: float) -> np.ndarray:
    """Additive blending: directly adds brightness offset regardless of base.

    Unlike soft-light (which multiplies by base and vanishes on dark pixels),
    this produces visible emboss on black backgrounds too — like a real
    debossed watermark on dark paper.
    """
    result = base.astype(np.float32) + overlay * strength * 255.0
    return np.clip(result, 0, 255).astype(np.uint8)


def _adaptive_blend(base: np.ndarray, overlay: np.ndarray, strength: float) -> np.ndarray:
    """Per-pixel adaptive blend: soft-light in midtones, additive in extremes.

    Soft-light vanishes when base is near 0 or 255 because the formula
    multiplies by b*(1-b).  This adaptive version smoothly transitions to
    additive blending in those extreme regions, guaranteeing visibility
    across all brightness levels.
    """
    b = base.astype(np.float32) / 255.0

    # Soft-light component
    bright = overlay > 0
    sl = np.where(
        bright,
        b + overlay * b * (1.0 - b),
        b + overlay * b,
    )
    sl_result = sl * 255.0

    # Additive component (always visible)
    add_result = base.astype(np.float32) + overlay * strength * 255.0

    # Per-pixel weight: how "extreme" (close to 0 or 255) is this pixel?
    # extremity = 0 at midtone (b=0.5), = 1 at pure black/white
    extremity = np.abs(2.0 * b - 1.0)
    # Use sqrt to make additive kick in sooner (broader effective range)
    additive_weight = np.sqrt(extremity)
    # Ensure minimum additive contribution so emboss is never fully invisible
    additive_weight = np.clip(additive_weight, 0.35, 1.0)
    softlight_weight = 1.0 - additive_weight

    result = sl_result * softlight_weight + add_result * additive_weight
    return np.clip(result, 0, 255).astype(np.uint8)


def _compute_detail_weight(image: np.ndarray) -> np.ndarray:
    """Detail map: 1.0 on textured/figure areas, 0.6 floor on flat."""
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float64)
    sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    edge_mag = np.sqrt(sx ** 2 + sy ** 2)
    clip_val = float(np.percentile(edge_mag, 90)) + 1e-6
    mask = np.clip(edge_mag / clip_val, 0.0, 1.0)
    mask = cv2.GaussianBlur(mask.astype(np.float32), (31, 31), 0)
    mask = np.clip(mask * 0.4 + 0.6, 0.6, 1.0)
    return mask.astype(np.float32)


def _build_text_layer(
    w: int, h: int,
    text: str,
    text_density: str,
    seed: int,
    fill_val: int = 255,
) -> np.ndarray:
    """Tile the author name at three mixed font sizes for multi-scale pattern."""
    rng = np.random.default_rng(seed)
    angle = float(rng.uniform(20, 40))

    combined = np.zeros((h, w), dtype=np.uint8)

    sizes = [max(10, int(h * r)) for r in _TEXT_SIZE_RATIOS]

    for idx, font_size in enumerate(sizes):
        font = _get_font(font_size, text)

        dummy = Image.new("L", (1, 1))
        bbox = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0] + font_size
        th = bbox[3] - bbox[1] + font_size

        tile = Image.new("L", (tw, th), 0)
        ImageDraw.Draw(tile).text(
            (font_size // 2, font_size // 2), text, font=font, fill=fill_val,
        )
        rotated = tile.rotate(angle + idx * 2, expand=True)
        rtw, rth = rotated.size

        if text_density == "dense":
            sx_gap = max(rtw + 2, int(rtw * 0.55))
            sy_gap = max(rth + 2, int(rth * 0.45))
        elif text_density == "sparse":
            sx_gap = rtw + font_size * 3
            sy_gap = rth + font_size * 2
        else:
            sx_gap = rtw + font_size
            sy_gap = rth + font_size // 2

        # Offset each size so they don't all start at the same origin
        x_off = (idx * rtw // 3) % max(1, sx_gap)
        y_off = (idx * rth // 3) % max(1, sy_gap)

        layer = Image.new("L", (w, h), 0)
        for ty in range(-rth + y_off - sy_gap, h + rth, sy_gap):
            for tx in range(-rtw + x_off - sx_gap, w + rtw, sx_gap):
                layer.paste(rotated, (tx, ty), rotated)

        combined = np.maximum(combined, np.array(layer, dtype=np.uint8))

    return combined


_STRENGTH_PRESETS: dict[str, dict[str, float]] = {
    "light": {"intensity": 0.18, "additive_strength": 0.45},
    "medium": {"intensity": 0.30, "additive_strength": 0.60},
    "strong": {"intensity": 0.48, "additive_strength": 0.85},
}


def apply_emboss_texture(
    image: np.ndarray,
    *,
    pattern: str = "diagonal",
    intensity: float = 0.28,
    spacing: int = 20,
    text: str = "",
    text_density: str = "normal",
    seed: int = 42,
    emboss_strength: str | None = None,
) -> np.ndarray:
    """Apply an embossed decorative texture overlay.

    Parameters
    ----------
    image : np.ndarray
        uint8 RGB, shape ``(H, W, 3)``.
    pattern : str
        ``"diagonal"`` (default), ``"halftone"``, or ``"crosshatch"``.
    intensity : float
        Strength of the emboss effect (0.05 – 0.55).
        Ignored when ``emboss_strength`` is provided.
    spacing : int
        Distance between pattern elements in pixels.
    text : str
        Optional repeating text woven into the pattern.
        Rendered at three sizes for multi-scale protection.
    text_density : str
        ``"sparse"``, ``"normal"``, or ``"dense"`` (default).
    seed : int
        RNG seed (controls text rotation angle).
    emboss_strength : str | None
        ``"light"`` / ``"medium"`` / ``"strong"`` — controls both emboss
        intensity and additive blend strength to guarantee visibility on
        all brightness levels.  Overrides ``intensity`` when set.
        ``None`` means use the raw ``intensity`` value (backward compat).
    """
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 32 or image.shape[1] < 32:
        raise ValueError(f"Image must be at least 32x32, got {image.shape[:2]}.")

    # Resolve strength preset → overrides raw intensity
    if emboss_strength and emboss_strength in _STRENGTH_PRESETS:
        preset = _STRENGTH_PRESETS[emboss_strength]
        intensity = preset["intensity"]
        additive_strength = preset["additive_strength"]
    else:
        additive_strength = 0.60

    intensity = float(np.clip(intensity, 0.05, 0.55))
    spacing = max(8, min(spacing, 80))
    h, w = image.shape[:2]

    # Thicker lines for diagonal/crosshatch (spacing//3 instead of spacing//5)
    line_width = max(2, spacing // 3)
    fill_val = 255

    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    if pattern == "halftone":
        pat_np = _draw_halftone(gray, w, h, spacing)
    elif pattern == "crosshatch":
        pil_pat = Image.new("L", (w, h), 0)
        _draw_crosshatch(ImageDraw.Draw(pil_pat), w, h, spacing, line_width, fill_val)
        pat_np = np.array(pil_pat, dtype=np.uint8)
    else:  # diagonal
        pil_pat = Image.new("L", (w, h), 0)
        _draw_diagonal_lines(ImageDraw.Draw(pil_pat), w, h, spacing, line_width, fill_val)
        pat_np = np.array(pil_pat, dtype=np.uint8)

    # --- Text layer (multi-scale) ---
    if text.strip():
        txt_np = _build_text_layer(w, h, text.strip(), text_density, seed, fill_val)
        _txt_arr: np.ndarray | None = txt_np.astype(np.float32)
    else:
        _txt_arr = None

    # --- Emboss via convolution kernel ---
    emboss_kernel = np.array(
        [[-2, -1, 0],
         [-1,  1, 1],
         [ 0,  1, 2]], dtype=np.float32
    )

    embossed_pat = cv2.filter2D(pat_np.astype(np.float32), cv2.CV_32F, emboss_kernel)
    max_abs_pat = float(np.abs(embossed_pat).max()) + 1e-6
    embossed_pat_norm = embossed_pat / max_abs_pat

    if _txt_arr is not None:
        embossed_txt = cv2.filter2D(_txt_arr, cv2.CV_32F, emboss_kernel)
        max_abs_txt = float(np.abs(embossed_txt).max()) + 1e-6
        embossed_txt_norm = embossed_txt / max_abs_txt
        text_intensity = min(intensity * 2.0, 0.55)
    else:
        embossed_txt_norm = None
        text_intensity = intensity

    detail_w = _compute_detail_weight(image)

    # Per-channel chromatic emboss: R stronger/right, G baseline, B stronger/left
    ch_multipliers = (1.15, 1.0, 1.08)
    ch_x_shifts = (1, 0, -1)

    out = image.copy()
    for c, (mult, xshift) in enumerate(zip(ch_multipliers, ch_x_shifts)):
        ch_pat = embossed_pat_norm * (intensity * mult) * detail_w
        if xshift != 0:
            ch_pat = np.roll(ch_pat, xshift, axis=1)
            if xshift > 0:
                ch_pat[:, :xshift] = 0.0
            else:
                ch_pat[:, xshift:] = 0.0

        if embossed_txt_norm is not None:
            ch_txt = embossed_txt_norm * (text_intensity * mult) * detail_w
            if xshift != 0:
                ch_txt = np.roll(ch_txt, xshift, axis=1)
                if xshift > 0:
                    ch_txt[:, :xshift] = 0.0
                else:
                    ch_txt[:, xshift:] = 0.0
            txt_mask = (_txt_arr > 0).astype(np.float32)
            ch_combined = ch_pat * (1.0 - txt_mask) + ch_txt * txt_mask
        else:
            ch_combined = ch_pat

        out[:, :, c] = _adaptive_blend(
            image[:, :, c], ch_combined, additive_strength
        )

    return out
