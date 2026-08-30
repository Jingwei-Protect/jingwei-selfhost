"""Displacement Watermark — text-shaped pixel shift for irremovable protection.

Modes
-----
- ``scatter``: Each character placed independently at high-gradient regions.
  Lower visual impact on the overall image.
- ``band``: Full word placed along 3 high-gradient horizontal bands.
  More readable and stronger protection.
- ``tile``: Text repeated densely across the image.

Only requires numpy, Pillow, scipy, opencv-python.
"""

from __future__ import annotations

import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, maximum_filter, minimum_filter

from core.text_fonts import get_text_font as _get_font

_SHIFT_MIN = 2
_SHIFT_MAX = 20
_FEATHER_SIGMA = 1.2
_FONT_RATIO_MIN = 0.07
_FONT_RATIO_MAX = 0.25
_SHADOW_OFFSET = (2, 2)
_SHADOW_STRENGTH_DEFAULT = 0.35
_SHADOW_BLUR = 1.2


def _validate_inputs(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 64 or image.shape[1] < 64:
        raise ValueError(
            f"Image must be at least 64x64, got {image.shape[:2]}."
        )


def _gradient_magnitude(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    return np.sqrt(gx ** 2 + gy ** 2)


def _find_best_band(
    grad_map: np.ndarray,
    band_h: int,
    n_bands: int,
    min_dist: int,
    exclude: list[int] | None = None,
) -> list[int]:
    h, w = grad_map.shape
    if exclude is None:
        exclude = []

    band_scores: list[tuple[float, int]] = []
    for y in range(0, h - band_h, 4):
        score = float(grad_map[y:y + band_h, :].sum())
        band_scores.append((score, y))

    band_scores.sort(key=lambda t: t[0], reverse=True)

    selected: list[int] = []
    for _score, y in band_scores:
        if len(selected) >= n_bands:
            break
        too_close = any(abs(y - sy) < min_dist for sy in selected + exclude)
        if not too_close:
            selected.append(y)

    return selected


def _find_best_patches(
    grad_map: np.ndarray,
    patch_w: int,
    patch_h: int,
    n_patches: int,
    min_dist: int,
    rng: np.random.Generator,
) -> list[tuple[int, int]]:
    h, w = grad_map.shape
    integral = cv2.integral(grad_map.astype(np.float64))

    step = max(4, min(patch_w, patch_h) // 4)
    candidates: list[tuple[float, int, int]] = []

    for y in range(0, h - patch_h, step):
        for x in range(0, w - patch_w, step):
            s = (
                integral[y + patch_h, x + patch_w]
                - integral[y, x + patch_w]
                - integral[y + patch_h, x]
                + integral[y, x]
            )
            avg = s / (patch_w * patch_h)
            candidates.append((avg, x, y))

    candidates.sort(key=lambda t: t[0], reverse=True)

    selected: list[tuple[int, int]] = []
    for _score, cx, cy in candidates:
        if len(selected) >= n_patches:
            break
        too_close = False
        for sx, sy in selected:
            if abs(cx - sx) < min_dist and abs(cy - sy) < min_dist:
                too_close = True
                break
        if not too_close:
            jx = int(rng.integers(-step, step + 1))
            jy = int(rng.integers(-step, step + 1))
            fx = max(0, min(cx + jx, w - patch_w))
            fy = max(0, min(cy + jy, h - patch_h))
            selected.append((fx, fy))

    return selected


def _render_char_mask(char: str, font_size: int, rotation: float = 0.0) -> np.ndarray:
    font = _get_font(font_size, char)
    dummy = Image.new("L", (1, 1))
    bbox = ImageDraw.Draw(dummy).textbbox((0, 0), char, font=font)
    cw = bbox[2] - bbox[0] + font_size // 3
    ch = bbox[3] - bbox[1] + font_size // 3

    canvas = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(canvas).text(
        (font_size // 6, font_size // 6), char, font=font, fill=255,
    )

    if abs(rotation) > 0.5:
        canvas = canvas.rotate(rotation, expand=True, resample=Image.BICUBIC)

    return np.array(canvas, dtype=np.float32) / 255.0


def _render_word_mask(text: str, font_size: int, rotation: float = 0.0) -> np.ndarray:
    font = _get_font(font_size, text)
    dummy = Image.new("L", (1, 1))
    bbox = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0] + font_size // 2
    th = bbox[3] - bbox[1] + font_size // 3

    canvas = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(canvas).text(
        (font_size // 4, font_size // 6), text, font=font, fill=255,
    )

    if abs(rotation) > 0.5:
        canvas = canvas.rotate(rotation, expand=True, resample=Image.BICUBIC)

    return np.array(canvas, dtype=np.float32) / 255.0


def _build_shadow_map(
    mask: np.ndarray,
    *,
    offset: tuple[int, int] = _SHADOW_OFFSET,
    blur: float = _SHADOW_BLUR,
) -> np.ndarray:
    """Build a drop-shadow alpha map from a float mask in [0, 1]."""
    m = gaussian_filter(mask.astype(np.float32), sigma=blur) if blur > 0 else mask.astype(np.float32)
    edge = np.clip(maximum_filter(m, size=3) - minimum_filter(m, size=3), 0.0, 1.0)
    gy, gx = np.gradient(m)
    grad_edge = np.sqrt(gx * gx + gy * gy)
    grad_edge /= float(grad_edge.max()) + 1e-6
    edge = np.clip(edge * 0.65 + grad_edge * 0.35, 0.0, 1.0)

    ox, oy = offset
    shadow = np.roll(edge, shift=(oy, ox), axis=(0, 1))
    if oy > 0:
        shadow[:oy, :] = 0.0
    elif oy < 0:
        shadow[oy:, :] = 0.0
    if ox > 0:
        shadow[:, :ox] = 0.0
    elif ox < 0:
        shadow[:, ox:] = 0.0
    return shadow


def _apply_edge_shadow_patch(
    patch: np.ndarray,
    mask: np.ndarray,
    *,
    strength: float = _SHADOW_STRENGTH_DEFAULT,
) -> np.ndarray:
    """Darken patch pixels along mask edges (local region)."""
    if strength <= 0 or mask.max() < 0.01:
        return patch
    shadow = _build_shadow_map(mask)
    shadow3 = shadow[:, :, np.newaxis] * strength
    darkened = patch.astype(np.float32) * (1.0 - shadow3)
    return np.clip(darkened, 0, 255).astype(np.uint8)


def _apply_edge_shadow_full(
    image: np.ndarray,
    mask: np.ndarray,
    *,
    strength: float = _SHADOW_STRENGTH_DEFAULT,
) -> np.ndarray:
    """Darken full-image pixels along mask edges (tile mode)."""
    if strength <= 0 or mask.max() < 0.01:
        return image
    shadow = _build_shadow_map(mask)
    shadow3 = shadow[:, :, np.newaxis] * strength
    darkened = image.astype(np.float32) * (1.0 - shadow3)
    return np.clip(darkened, 0, 255).astype(np.uint8)


def _apply_mask_displacement(
    image: np.ndarray,
    mask: np.ndarray,
    x: int,
    y: int,
    dx: int,
    dy: int,
    feather: float,
    *,
    shadow_enabled: bool = False,
    shadow_strength: float = _SHADOW_STRENGTH_DEFAULT,
) -> np.ndarray:
    h, w = image.shape[:2]
    mh, mw = mask.shape

    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(w, x + mw)
    y1 = min(h, y + mh)

    if x1 - x0 < 4 or y1 - y0 < 4:
        return image

    mx0 = x0 - x
    my0 = y0 - y
    mx1 = mx0 + (x1 - x0)
    my1 = my0 + (y1 - y0)
    local_mask = mask[my0:my1, mx0:mx1].copy()

    if feather > 0:
        local_mask = gaussian_filter(local_mask, sigma=feather)

    rh = y1 - y0
    rw = x1 - x0

    out = image.copy()
    original = image[y0:y1, x0:x1].astype(np.float32)
    shifted_patch = np.zeros_like(original)

    src_y0 = max(0, y0 - dy)
    src_y1 = min(h, y1 - dy)
    src_x0 = max(0, x0 - dx)
    src_x1 = min(w, x1 - dx)

    dst_oy = max(0, dy) if dy > 0 else 0
    dst_ox = max(0, dx) if dx > 0 else 0
    src_oy = max(0, -dy) if dy < 0 else 0
    src_ox = max(0, -dx) if dx < 0 else 0

    actual_h = min(rh - dst_oy, src_y1 - src_y0 - src_oy)
    actual_w = min(rw - dst_ox, src_x1 - src_x0 - src_ox)

    if actual_h > 0 and actual_w > 0:
        shifted_patch[dst_oy:dst_oy + actual_h, dst_ox:dst_ox + actual_w] = (
            image[src_y0 + src_oy:src_y0 + src_oy + actual_h,
                  src_x0 + src_ox:src_x0 + src_ox + actual_w].astype(np.float32)
        )
        fill_mask = np.zeros((rh, rw), dtype=np.float32)
        fill_mask[dst_oy:dst_oy + actual_h, dst_ox:dst_ox + actual_w] = 1.0
        for c in range(3):
            shifted_patch[:, :, c] = (
                shifted_patch[:, :, c] * fill_mask
                + original[:, :, c] * (1.0 - fill_mask)
            )
    else:
        shifted_patch = original.copy()

    m3 = local_mask[:, :, np.newaxis]
    blended = original * (1.0 - m3) + shifted_patch * m3
    patch_out = np.clip(blended, 0, 255).astype(np.uint8)
    if shadow_enabled:
        patch_out = _apply_edge_shadow_patch(patch_out, local_mask, strength=shadow_strength)
    out[y0:y1, x0:x1] = patch_out
    return out


def _random_shift(shift_px: int, rng: np.random.Generator) -> tuple[int, int]:
    angle = float(rng.uniform(25, 65))
    sign_x = 1 if rng.random() > 0.5 else -1
    sign_y = 1 if rng.random() > 0.5 else -1
    dx = int(round(shift_px * math.cos(math.radians(angle)))) * sign_x
    dy = int(round(shift_px * math.sin(math.radians(angle)))) * sign_y
    if dx == 0 and dy == 0:
        dx = shift_px
    return dx, dy


def _anchor_enabled(anchor_x: float, anchor_y: float) -> bool:
    return 0.0 <= anchor_x <= 1.0 and 0.0 <= anchor_y <= 1.0


def _apply_scatter(
    image: np.ndarray,
    text: str,
    shift_px: int,
    font_size: int,
    feather: float,
    seed: int,
    density: str = "normal",
    *,
    shadow_enabled: bool = False,
    shadow_strength: float = _SHADOW_STRENGTH_DEFAULT,
    anchor_x: float = -1.0,
    anchor_y: float = -1.0,
) -> np.ndarray:
    h, w = image.shape[:2]
    rng = np.random.default_rng(seed)
    grad_map = _gradient_magnitude(image)

    chars = list(text)
    char_masks = []
    for ch in chars:
        rot = float(rng.uniform(-15, 15))
        char_masks.append(_render_char_mask(ch, font_size, rotation=rot))

    max_ch = max(m.shape[0] for m in char_masks)
    max_cw = max(m.shape[1] for m in char_masks)
    patch_h = max_ch + 4
    patch_w = max_cw + 4

    # Scale placement count by image area (per megapixel)
    megapixels = (h * w) / 1_000_000
    if density == "dense":
        base_per_mp = 25
    elif density == "sparse":
        base_per_mp = 8
    else:
        base_per_mp = 15
    n_patches = max(6, int(megapixels * base_per_mp))

    total_masks = []
    for i in range(n_patches):
        total_masks.append(char_masks[i % len(char_masks)])

    min_dist = max(patch_w, patch_h) + 6
    positions = _find_best_patches(
        grad_map, patch_w, patch_h, n_patches, min_dist, rng,
    )

    # Fallback: if gradient-based placement found too few positions,
    # fill remaining with random positions across the image
    if len(positions) < n_patches:
        remaining = n_patches - len(positions)
        for _ in range(remaining):
            rx = int(rng.integers(0, max(1, w - patch_w)))
            ry = int(rng.integers(0, max(1, h - patch_h)))
            positions.append((rx, ry))

    if _anchor_enabled(anchor_x, anchor_y) and positions:
        ax = int(anchor_x * w - patch_w / 2)
        ay = int(anchor_y * h - patch_h / 2)
        ax = max(0, min(ax, w - patch_w))
        ay = max(0, min(ay, h - patch_h))
        positions[0] = (ax, ay)

    out = image.copy()
    for i, (px, py) in enumerate(positions):
        idx = i % len(char_masks)
        cmask = char_masks[idx]
        mh, mw = cmask.shape
        cx = px + (patch_w - mw) // 2
        cy = py + (patch_h - mh) // 2
        dx, dy = _random_shift(shift_px, rng)
        out = _apply_mask_displacement(
            out, cmask, cx, cy, dx, dy, feather,
            shadow_enabled=shadow_enabled,
            shadow_strength=shadow_strength,
        )

    return out


def _apply_band(
    image: np.ndarray,
    text: str,
    shift_px: int,
    font_size: int,
    feather: float,
    seed: int,
    *,
    shadow_enabled: bool = False,
    shadow_strength: float = _SHADOW_STRENGTH_DEFAULT,
    anchor_x: float = -1.0,
    anchor_y: float = -1.0,
) -> np.ndarray:
    h, w = image.shape[:2]
    rng = np.random.default_rng(seed)
    grad_map = _gradient_magnitude(image)

    word_mask = _render_word_mask(text, font_size, rotation=0.0)
    mh, mw = word_mask.shape

    n_placements = 3
    band_ys = _find_best_band(
        grad_map, band_h=mh, n_bands=n_placements, min_dist=int(mh * 2.5),
    )
    if not band_ys:
        band_ys = [h // 4, h // 2, h * 3 // 4]

    if _anchor_enabled(anchor_x, anchor_y):
        ay = int(anchor_y * h - mh // 2)
        ay = max(0, min(ay, h - mh))
        band_ys[0] = ay

    out = image.copy()
    for by in band_ys:
        best_x = 0
        best_score = -1.0
        step = max(4, mw // 8)
        for x in range(0, w - mw, step):
            region_grad = grad_map[by:min(h, by + mh), x:x + mw]
            score = float(region_grad.sum())
            if score > best_score:
                best_score = score
                best_x = x

        jx = int(rng.integers(-mw // 6, mw // 6 + 1))
        jy = int(rng.integers(-mh // 4, mh // 4 + 1))
        px = max(0, min(best_x + jx, w - mw))
        py = max(0, min(by + jy, h - mh))
        dx, dy = _random_shift(shift_px, rng)
        out = _apply_mask_displacement(
            out, word_mask, px, py, dx, dy, feather,
            shadow_enabled=shadow_enabled,
            shadow_strength=shadow_strength,
        )

    return out


def apply_displacement_single_at(
    image: np.ndarray,
    *,
    text: str = "Jingwei",
    shift_px: int = 10,
    font_size_ratio: float = 0.15,
    feather: float = _FEATHER_SIGMA,
    seed: int = 42,
    shadow_enabled: bool = False,
    shadow_strength: float = _SHADOW_STRENGTH_DEFAULT,
    anchor_x: float = 0.5,
    anchor_y: float = 0.5,
) -> np.ndarray:
    """Render the full word EXACTLY ONCE, centered on (anchor_x, anchor_y).

    Unlike ``_apply_band`` (which auto-picks 3 high-gradient rows), this honors
    the user-placed box: the word's center is the click point, so the on-screen
    dashed box maps 1:1 to where the displaced text actually lands. Callers
    place multiple words by invoking this once per box.
    """
    _validate_inputs(image)
    if not text.strip():
        return image.copy()

    text = text.strip()
    shift_px = int(np.clip(shift_px, _SHIFT_MIN, _SHIFT_MAX))
    h, w = image.shape[:2]
    short_side = min(h, w)
    ratio = float(np.clip(font_size_ratio, _FONT_RATIO_MIN, _FONT_RATIO_MAX))
    font_size = max(12, int(round(short_side * ratio)))

    rng = np.random.default_rng(seed)
    word_mask = _render_word_mask(text, font_size, rotation=0.0)
    mh, mw = word_mask.shape

    # Align the INK bounding-box center (not the canvas center) to the anchor.
    # The rendered glyph padding is asymmetric (ascender gap > descender), so the
    # text sits well below the canvas center; centering the canvas would drop the
    # word ~14% of its height below the on-screen box. Compensate with ink bbox.
    ys, xs = np.nonzero(word_mask > 0.3)
    if xs.size and ys.size:
        ink_cx = (int(xs.min()) + int(xs.max())) / 2.0
        ink_cy = (int(ys.min()) + int(ys.max())) / 2.0
    else:
        ink_cx, ink_cy = mw / 2.0, mh / 2.0

    cx = float(np.clip(anchor_x, 0.0, 1.0))
    cy = float(np.clip(anchor_y, 0.0, 1.0))
    px = int(round(cx * w - ink_cx))
    py = int(round(cy * h - ink_cy))
    px = max(0, min(px, max(0, w - mw)))
    py = max(0, min(py, max(0, h - mh)))

    dx, dy = _random_shift(shift_px, rng)
    return _apply_mask_displacement(
        image.copy(), word_mask, px, py, dx, dy, feather,
        shadow_enabled=shadow_enabled,
        shadow_strength=shadow_strength,
    )


def _build_tile_mask(
    w: int,
    h: int,
    text: str,
    font_size: int,
    density: str,
    rotation: float,
    seed: int,
    *,
    anchor_x: float = -1.0,
    anchor_y: float = -1.0,
) -> np.ndarray:
    font = _get_font(font_size, text)
    dummy = Image.new("L", (1, 1))
    bbox = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0] + font_size // 2
    th = bbox[3] - bbox[1] + font_size // 4

    tile = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(tile).text(
        (font_size // 4, font_size // 8), text, font=font, fill=255,
    )
    rotated = tile.rotate(rotation, expand=True, resample=Image.BICUBIC)
    rtw, rth = rotated.size

    if density == "dense":
        gap_x = int(rtw * 1.1)
        gap_y = int(rth * 1.0)
    elif density == "sparse":
        gap_x = int(rtw * 2.0)
        gap_y = int(rth * 1.8)
    else:
        gap_x = int(rtw * 1.4)
        gap_y = int(rth * 1.3)

    rng = np.random.default_rng(seed)
    if _anchor_enabled(anchor_x, anchor_y):
        x_offset = int(anchor_x * max(1, gap_x))
        y_offset = int(anchor_y * max(1, gap_y))
    else:
        x_offset = int(rng.integers(0, max(1, gap_x // 3)))
        y_offset = int(rng.integers(0, max(1, gap_y // 3)))

    canvas = Image.new("L", (w, h), 0)
    for ty in range(-rth + y_offset, h + rth, gap_y):
        for tx in range(-rtw + x_offset, w + rtw, gap_x):
            canvas.paste(rotated, (tx, ty), rotated)

    return np.array(canvas, dtype=np.float32) / 255.0


def _apply_tile_shift(
    image: np.ndarray,
    mask: np.ndarray,
    dx: int,
    dy: int,
    feather: float,
    *,
    shadow_enabled: bool = False,
    shadow_strength: float = _SHADOW_STRENGTH_DEFAULT,
) -> np.ndarray:
    h, w = image.shape[:2]

    if feather > 0:
        mask = gaussian_filter(mask, sigma=feather)

    shifted = image.copy()
    if dy != 0 or dx != 0:
        src_y0 = max(0, -dy)
        src_y1 = min(h, h - dy)
        src_x0 = max(0, -dx)
        src_x1 = min(w, w - dx)
        dst_y0 = max(0, dy)
        dst_x0 = max(0, dx)
        region_h = src_y1 - src_y0
        region_w = src_x1 - src_x0

        if region_h > 0 and region_w > 0:
            shifted_new = image.copy()
            shifted_new[dst_y0:dst_y0 + region_h, dst_x0:dst_x0 + region_w] = (
                image[src_y0:src_y0 + region_h, src_x0:src_x0 + region_w]
            )
            shifted = shifted_new

    m3 = mask[:, :, np.newaxis]
    blended = image.astype(np.float32) * (1.0 - m3) + shifted.astype(np.float32) * m3
    out = np.clip(blended, 0, 255).astype(np.uint8)
    if shadow_enabled:
        out = _apply_edge_shadow_full(out, mask, strength=shadow_strength)
    return out


def apply_displacement_watermark(
    image: np.ndarray,
    *,
    text: str = "Jingwei",
    shift_px: int = 10,
    font_size_ratio: float = 0.15,
    density: str = "normal",
    rotation: float = 15.0,
    mode: str = "scatter",
    feather: float = _FEATHER_SIGMA,
    seed: int = 42,
    shadow_enabled: bool = False,
    shadow_strength: float = _SHADOW_STRENGTH_DEFAULT,
    anchor_x: float = -1.0,
    anchor_y: float = -1.0,
) -> np.ndarray:
    """Apply displacement watermark.

    Parameters
    ----------
    mode : str
        ``scatter`` — characters at separate high-gradient locations.
        ``band`` — full word along high-gradient bands (3 placements).
        ``tile`` — dense repeated text.
        ``single`` — alias for ``band`` (backward compatibility).
    font_size_ratio : float
        Font height as fraction of image short side (0.07–0.25).
    shadow_enabled : bool
        If True, add a subtle dark drop-shadow along displacement edges.
    shadow_strength : float
        Shadow opacity in ``[0.0, 1.0]``; default 0.35.
    anchor_x : float
        Normalized X in ``[0, 1]`` for user-placed anchor; ``-1`` = auto.
    anchor_y : float
        Normalized Y in ``[0, 1]`` for user-placed anchor; ``-1`` = auto.
    seed : int
        RNG seed; change to get different random layouts.
    """
    _validate_inputs(image)
    if not text.strip():
        return image.copy()

    text = text.strip()
    shift_px = int(np.clip(shift_px, _SHIFT_MIN, _SHIFT_MAX))

    h, w = image.shape[:2]
    short_side = min(h, w)
    ratio = float(np.clip(font_size_ratio, _FONT_RATIO_MIN, _FONT_RATIO_MAX))
    font_size = max(12, int(round(short_side * ratio)))

    # Normalize mode aliases
    if mode == "single":
        mode = "band"

    rng = np.random.default_rng(seed)

    if mode == "tile":
        mask = _build_tile_mask(
            w, h, text, font_size, density, rotation, seed,
            anchor_x=anchor_x, anchor_y=anchor_y,
        )
        angle = float(rng.uniform(30, 60))
        dx = int(round(shift_px * math.cos(math.radians(angle))))
        dy = int(round(shift_px * math.sin(math.radians(angle))))
        if dx == 0 and dy == 0:
            dx = shift_px
        return _apply_tile_shift(
            image, mask, dx, dy, feather,
            shadow_enabled=shadow_enabled,
            shadow_strength=shadow_strength,
        )

    if mode == "band":
        return _apply_band(
            image, text, shift_px, font_size, feather, seed,
            shadow_enabled=shadow_enabled,
            shadow_strength=shadow_strength,
            anchor_x=anchor_x,
            anchor_y=anchor_y,
        )

    # Default: scatter
    return _apply_scatter(
        image, text, shift_px, font_size, feather, seed, density,
        shadow_enabled=shadow_enabled,
        shadow_strength=shadow_strength,
        anchor_x=anchor_x,
        anchor_y=anchor_y,
    )


def _border_median_luma(luma: np.ndarray) -> float:
    """Median luma of the 1-pixel frame — used to detect a light card."""
    if luma.ndim != 2 or luma.size == 0:
        return 0.0
    h, w = luma.shape
    if h < 3 or w < 3:
        return float(np.median(luma))
    frame = np.concatenate(
        [luma[0, :], luma[-1, :], luma[1:-1, 0], luma[1:-1, -1]]
    )
    return float(np.median(frame))


def _logo_shape_mask(logo_rgba: np.ndarray) -> np.ndarray:
    """HxW float mask in ``[0, 1]`` from logo alpha, or ink-on-ground if opaque.

    Transparent files use the alpha channel. Fully opaque files:
    - light / white card: knock out high-luma, low-chroma ground so dark or
      coloured marks remain; if almost the whole card is “ink”, treat it as
      a photograph and use the full rectangle;
    - otherwise recover dark ink from luma; if that signal is too weak
      (pale mark on pale ground), fall back to the full rectangle.
    """
    if logo_rgba.dtype != np.uint8 or logo_rgba.ndim != 3 or logo_rgba.shape[2] != 4:
        raise ValueError(
            f"logo must be HxWx4 uint8 RGBA, got {logo_rgba.shape} {logo_rgba.dtype}"
        )
    alpha = logo_rgba[:, :, 3].astype(np.float32) / 255.0
    if float(alpha.min()) <= 0.99:
        return alpha

    rgb = logo_rgba[:, :, :3].astype(np.float32)
    luma = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2])
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    if _border_median_luma(luma) >= 200.0:
        # Soft knockout: bright AND unsaturated → ground; keep saturated colour.
        luma_ground = np.clip((luma - 185.0) / 40.0, 0.0, 1.0)
        chroma_ground = np.clip((36.0 - chroma) / 36.0, 0.0, 1.0)
        mask = np.clip(1.0 - luma_ground * chroma_ground, 0.0, 1.0)
        if float(mask.max()) < 0.15:
            return np.ones_like(luma, dtype=np.float32)
        # A photo filling a white-margined card is not a logo silhouette.
        if float((mask > 0.30).mean()) > 0.65:
            return np.ones_like(luma, dtype=np.float32)
        return mask

    mask = np.clip((220.0 - luma) / 220.0, 0.0, 1.0)
    if float(mask.max()) < 0.15:
        return np.ones_like(luma, dtype=np.float32)
    return mask


def apply_displacement_logo(
    image: np.ndarray,
    logo_rgba: np.ndarray,
    *,
    scale: float = 0.18,
    position: str = "bottom_right",
    anchor_x: float = -1.0,
    anchor_y: float = -1.0,
    shift_px: int = 10,
    feather: float = _FEATHER_SIGMA,
    seed: int = 42,
    shadow_enabled: bool = True,
    shadow_strength: float = _SHADOW_STRENGTH_DEFAULT,
) -> np.ndarray:
    """Push host pixels in the logo silhouette — same mechanism as dog-style text.

    The logo is a mask, not a pasted stamp. Colour in the upload is ignored
    except to recover a shape from an opaque file. ``scale`` is the logo's
    longest side as a fraction of the host short side. ``anchor_x`` / ``anchor_y``
    in ``[0, 1]`` override ``position`` and centre the ink on that point.
    """
    from core.logo_watermark import _paste_box

    _validate_inputs(image)
    mask = _logo_shape_mask(logo_rgba)
    if float(mask.max()) <= 0.0:
        return image.copy()

    h, w = image.shape[:2]
    scale = float(np.clip(scale, 0.04, 0.55))
    shift_px = int(np.clip(shift_px, _SHIFT_MIN, _SHIFT_MAX))
    short = min(h, w)
    target = max(8, int(round(short * scale)))
    mh, mw = mask.shape
    longest = max(mh, mw)
    ratio = target / longest
    new_w = max(8, min(w, int(round(mw * ratio))))
    new_h = max(8, min(h, int(round(mh * ratio))))
    resized = np.asarray(
        Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8)).resize(
            (new_w, new_h), Image.Resampling.LANCZOS,
        ),
        dtype=np.float32,
    ) / 255.0

    if _anchor_enabled(anchor_x, anchor_y):
        ys, xs = np.nonzero(resized > 0.3)
        if xs.size and ys.size:
            ink_cx = (int(xs.min()) + int(xs.max())) / 2.0
            ink_cy = (int(ys.min()) + int(ys.max())) / 2.0
        else:
            ink_cx, ink_cy = new_w / 2.0, new_h / 2.0
        px = int(round(float(np.clip(anchor_x, 0.0, 1.0)) * w - ink_cx))
        py = int(round(float(np.clip(anchor_y, 0.0, 1.0)) * h - ink_cy))
        px = max(0, min(px, max(0, w - new_w)))
        py = max(0, min(py, max(0, h - new_h)))
    else:
        px, py = _paste_box(h, w, new_h, new_w, position)  # type: ignore[arg-type]

    rng = np.random.default_rng(seed)
    dx, dy = _random_shift(shift_px, rng)
    return _apply_mask_displacement(
        image.copy(),
        resized,
        px,
        py,
        dx,
        dy,
        feather,
        shadow_enabled=shadow_enabled,
        shadow_strength=float(np.clip(shadow_strength, 0.0, 1.0)),
    )
