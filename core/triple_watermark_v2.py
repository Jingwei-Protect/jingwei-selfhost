"""Triple watermark v2 — adaptive subject-colour camouflage + RGB-split rendering.

Why v1 (``core.triple_watermark``) is easy for modern inpainters to remove
-------------------------------------------------------------------------
v1 uses pure (255, 80, 80) / (80, 255, 80) / (80, 80, 255).  These three
saturation-maxed primaries are colour-orthogonal to almost every natural
image, so an inpainting model can identify the watermark region trivially
by colour-channel statistics and erase it.

What v2 does differently
------------------------
1. **Sample the image's own palette.**  K-means clusters every 4th pixel of
   the input image into 5 dominant RGB centroids; near-white (>240) and
   near-black (<15) extremes are excluded since they usually belong to
   paper/outline rather than subject content.  Centroids are **sorted by
   saturation** so we prefer colourful subject hues over muddy greys.

2. **Use those centroids as watermark colours.**  Each of the three layers
   takes one centroid, then shifts along the **same hue direction** in RGB
   (additive step parallel to the colour vector) so the result stays
   recognisably “on-palette” and does not collapse toward neutral grey.

3. **RGB-split rendering per layer.**  The R channel of each rendered text
   tile is rolled right by ``rgb_split_offset`` px, the B channel rolled
   left by the same amount, leaving G untouched.

4. **Crisscross geometry.**  Each layer tiles text along a **spine line**
   through the image centre: TL–BR diagonal, LA–R horizontal through the
   middle, and BL–TR diagonal.  Together with rotations 30°/50°/70° the bands
   cover left, centre, and right instead of stacking on one side.

Only numpy / scipy / Pillow are used.  No deep-learning dependencies.
"""

from __future__ import annotations

import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.cluster.vq import kmeans2

from core.text_fonts import get_text_font as _get_font

DEFAULT_V2_TEXTS: list[str] = [
    "COPYRIGHT PROTECTED",
    "PREVIEW ONLY - DO NOT EDIT",
    "\u7248\u6b0a\u6240\u6709 \u7981\u6b62AI\u6539\u5716",
]

_FALLBACK_COLORS: list[tuple[int, int, int]] = [
    (128, 128, 128),
    (160, 140, 130),
    (110, 120, 140),
]

_OPACITY_MIN: float = 0.20
_OPACITY_MAX: float = 0.60
_RGB_SPLIT_MIN: int = 2
_RGB_SPLIT_MAX: int = 10
_BRIGHTNESS_MIN: int = 10
_BRIGHTNESS_MAX: int = 50

_LAYER_ROTATIONS_DEG: tuple[int, int, int] = (30, 50, 70)


def _validate_inputs(
    image: np.ndarray,
    texts: list[str],
) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 8 or image.shape[1] < 8:
        raise ValueError(
            f"Image dimensions must be at least 8x8, got {image.shape[:2]}."
        )
    if not isinstance(texts, list) or len(texts) != 3:
        raise ValueError(
            f"texts must be a list of exactly 3 strings, got {texts!r}."
        )
    if not all(isinstance(t, str) and t for t in texts):
        raise ValueError("each text entry must be a non-empty string.")


def _centroid_saturation(rgb: tuple[int, int, int]) -> float:
    """Saturation proxy: (max - min) / max, same as common UI 'saturation' on RGB cube."""
    r, g, b = rgb
    mx = max(r, g, b)
    mn = min(r, g, b)
    if mx <= 0:
        return 0.0
    return float(mx - mn) / float(mx)


def _extract_dominant_colors(
    image: np.ndarray,
    n_colors: int = 5,
    seed: int = 42,
) -> list[tuple[int, int, int]]:
    """Extract up to ``n_colors`` dominant RGB centroids via K-means.

    Centroids are sorted by **saturation descending** so the top picks are
    visually colourful subject hues, not near-neutral mud from K-means.
    """
    h, w = image.shape[:2]
    pixels = image.reshape(-1, 3).astype(np.float64)

    if h * w > 250_000:
        pixels = pixels[::4]

    mx = pixels.max(axis=1)
    mn = pixels.min(axis=1)
    keep = (mx <= 240) & (mn >= 15)
    filtered = pixels[keep]

    if filtered.shape[0] < n_colors * 2:
        filtered = pixels
    if filtered.shape[0] < n_colors:
        return []

    np.random.seed(seed)
    try:
        centroids, _ = kmeans2(
            filtered,
            k=n_colors,
            iter=20,
            minit="++",
            missing="warn",
        )
    except Exception:
        return []

    out: list[tuple[int, int, int]] = []
    for c in centroids:
        if not np.all(np.isfinite(c)):
            continue
        rgb = tuple(int(np.clip(round(v), 0, 255)) for v in c)
        out.append(rgb)  # type: ignore[arg-type]

    out.sort(key=_centroid_saturation, reverse=True)
    return out


def _shift_color_brightness(
    color: tuple[int, int, int], delta: int
) -> tuple[int, int, int]:
    """Additive shift along the colour vector (preserves hue in RGB).

    ``delta > 0`` pushes away from black along ``normalize(R,G,B)``;
    ``delta < 0`` pulls toward black along the same direction.  This avoids
    the multiplicative blow-up that maps rich colours toward dull grey.
    """
    r, g, b = int(color[0]), int(color[1]), int(color[2])
    v = np.array([r, g, b], dtype=np.float64)
    norm = float(np.linalg.norm(v))

    if norm < 1e-6:
        step = float(np.sign(delta)) * min(abs(int(delta)), float(_BRIGHTNESS_MAX))
        out = np.clip(v + step, 0, 255)
        return tuple(int(round(x)) for x in out)

    direction = v / norm
    sign = 1.0 if delta >= 0 else -1.0
    mag = min(abs(int(delta)), float(_BRIGHTNESS_MAX))
    out = np.clip(v + sign * mag * direction, 0, 255)
    return tuple(int(round(x)) for x in out)


def _shift_horizontal(channel: np.ndarray, dx: int) -> np.ndarray:
    if dx == 0:
        return channel
    rolled = np.roll(channel, dx, axis=1)
    if dx > 0:
        rolled[:, :dx] = 0
    else:
        rolled[:, dx:] = 0
    return rolled


def _apply_rgb_split(overlay: Image.Image, offset: int) -> Image.Image:
    arr = np.array(overlay, dtype=np.uint8)
    r = _shift_horizontal(arr[..., 0], offset)
    g = arr[..., 1]
    b = _shift_horizontal(arr[..., 2], -offset)
    a = arr[..., 3]
    out = np.stack([r, g, b, a], axis=-1)
    return Image.fromarray(out, mode="RGBA")


def _make_text_tile(
    text: str,
    color: tuple[int, int, int],
    opacity: float,
    font_size: int,
    rotation_deg: float,
    rgb_split_offset: int,
) -> Image.Image:
    """One repeated-text segment, rotated and RGB-split."""
    font = _get_font(font_size, text)
    dummy = Image.new("RGBA", (1, 1))
    bbox = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
    tw = max(1, bbox[2] - bbox[0])
    th = max(1, bbox[3] - bbox[1])
    spacing = int(font_size * 3)
    tile_w = tw + spacing
    tile_h = th + font_size + 4

    alpha = int(max(0, min(255, round(opacity * 255))))
    fill = (int(color[0]), int(color[1]), int(color[2]), alpha)

    tile = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((0, font_size // 4), text, font=font, fill=fill)

    rotated = tile.rotate(rotation_deg, expand=True, resample=Image.BICUBIC)
    return _apply_rgb_split(rotated, rgb_split_offset)


def _spine_unit_vector(layer_index: int, w: int, h: int) -> tuple[float, float]:
    """Unit direction along which we tile text (through image centre).

    0: top-left → bottom-right diagonal.
    1: left → right through vertical middle (horizontal band).
    2: bottom-left → top-right diagonal.
    """
    if layer_index == 0:
        L = math.hypot(w, h)
        return (w / L, h / L)
    if layer_index == 1:
        return (1.0, 0.0)
    L = math.hypot(w, h)
    return (w / L, -h / L)


def _half_extent_along_spine(w: int, h: int, ux: float, uy: float) -> float:
    """Max distance from centre to image border along ±spine direction."""
    cx = 0.5 * w
    cy = 0.5 * h
    corners = ((0.0, 0.0), (w - 1.0, 0.0), (0.0, h - 1.0), (w - 1.0, h - 1.0))
    m = 0.0
    for px, py in corners:
        t = (px - cx) * ux + (py - cy) * uy
        m = max(m, abs(t))
    return m + max(w, h) * 0.08


def _build_layer(
    w: int,
    h: int,
    text: str,
    color: tuple[int, int, int],
    rotation_deg: float,
    layer_index: int,
    opacity: float,
    rgb_split_offset: int,
) -> Image.Image:
    """Full-size RGBA overlay; text tiled along spine through centre."""
    font_size = max(12, max(h, w) // 18)
    tile = _make_text_tile(
        text, color, opacity, font_size, rotation_deg, rgb_split_offset
    )
    tw, th = tile.size

    ux, uy = _spine_unit_vector(layer_index, w, h)
    half = _half_extent_along_spine(w, h, ux, uy)
    step = max(int(font_size * 3), 12)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cx = 0.5 * w
    cy = 0.5 * h

    t = -half
    while t <= half + 1e-3:
        px = cx + t * ux
        py = cy + t * uy
        left = int(round(px - tw / 2.0))
        top = int(round(py - th / 2.0))
        overlay.paste(tile, (left, top), tile)
        t += step

    return overlay


_FIXED_HIGH_SAT_COLORS: list[tuple[int, int, int]] = [
    (255, 0, 180),    # magenta — matches edge_corruption hue-shift artifacts
    (0, 220, 255),    # cyan — complementary to magenta
    (255, 200, 0),    # warm yellow — third axis
]


def _content_aware_recolor(
    layer: Image.Image,
    base_rgb: np.ndarray,
    brightness_delta: int,
    box_size: int = 16,
) -> Image.Image:
    """Replace the RGB channels of *layer* with brightness-shifted samples of
    the local mean colour of *base_rgb* at each pixel.

    The alpha channel of *layer* is preserved unchanged: only the colour of
    the text strokes is rewritten so the watermark becomes "content-aware"
    — every stroke pixel shares the dominant colour of the area it covers,
    making the watermark statistically indistinguishable from the underlying
    artwork.

    Parameters
    ----------
    layer:
        RGBA :class:`PIL.Image.Image`, same size as ``base_rgb``.
    base_rgb:
        ``(H, W, 3)`` uint8 array — the current state of the composed image
        below this layer (so each subsequent layer samples the *already
        watermarked* image, which adds extra colour drift).
    brightness_delta:
        Signed RGB-axis shift in ``[-50, 50]``.  Positive lightens, negative
        darkens.  Stroke pixels lose all visibility if this is zero, so use
        |delta| ≥ 12 in practice.
    box_size:
        Edge length of the spatial averaging box.  16 is a good compromise
        between "follow content" (small box) and "stable colour" (large box).
    """
    arr = np.array(layer, dtype=np.uint8)
    alpha = arr[..., 3]

    mean_rgb = cv2.blur(base_rgb, (box_size, box_size))

    delta = int(np.clip(brightness_delta, -_BRIGHTNESS_MAX, _BRIGHTNESS_MAX))
    shifted = mean_rgb.astype(np.int16) + delta
    shifted = np.clip(shifted, 0, 255).astype(np.uint8)

    out = np.empty_like(arr)
    out[..., :3] = shifted
    out[..., 3] = alpha
    return Image.fromarray(out, mode="RGBA")


def apply_triple_watermark_v2(
    image: np.ndarray,
    *,
    texts: list[str] | None = None,
    colors: list[tuple[int, int, int]] | None = None,
    opacity: float = 0.45,
    rgb_split_offset: int = 5,
    brightness_delta: int = 25,
    use_adaptive_colors: bool = False,
    content_aware: bool = False,
    seed: int = 42,
) -> np.ndarray:
    """Stack three RGB-split diagonal watermarks.

    Parameters
    ----------
    image:
        uint8 RGB, shape (H, W, 3).
    texts:
        Three watermark strings.  ``None`` uses :data:`DEFAULT_V2_TEXTS`.
    colors:
        Explicit list of 3 RGB tuples.  Takes priority over both adaptive
        and fixed-palette colours when provided.
    opacity:
        Per-layer alpha in [0.20, 0.60].
    rgb_split_offset:
        Horizontal split between R and B channels, pixels; clamped [2, 10].
    brightness_delta:
        Magnitude of additive shift along colour vector; clamped [10, 50].
    use_adaptive_colors:
        If ``True`` **and** *colors* is ``None``, extract dominant colours
        from the image via K-means (original v2 behaviour).  If ``False``
        (default), use ``_FIXED_HIGH_SAT_COLORS`` — magenta / cyan / yellow
        that match the ``edge_corruption`` artifact palette and are hard for
        AI inpainters to separate from the ghost-edge layer.
    seed:
        Controls K-means initialisation; deterministic outputs.

    Returns
    -------
    np.ndarray
        uint8 RGB, same shape as input.
    """
    resolved_texts = list(texts) if texts is not None else list(DEFAULT_V2_TEXTS)
    _validate_inputs(image, resolved_texts)

    opacity_c = float(np.clip(opacity, _OPACITY_MIN, _OPACITY_MAX))
    split_c = int(np.clip(rgb_split_offset, _RGB_SPLIT_MIN, _RGB_SPLIT_MAX))
    brightness_c = int(np.clip(brightness_delta, _BRIGHTNESS_MIN, _BRIGHTNESS_MAX))

    if colors is not None:
        selected = list(colors)
        if len(selected) != 3:
            raise ValueError(
                f"colors must be a list of exactly 3 (r,g,b) tuples, "
                f"got {len(selected)}."
            )
    elif use_adaptive_colors:
        dominant = _extract_dominant_colors(image, n_colors=5, seed=seed)
        if len(dominant) >= 3:
            selected = dominant[:3]
        else:
            needed = 3 - len(dominant)
            selected = dominant + _FALLBACK_COLORS[:needed]
    else:
        selected = list(_FIXED_HIGH_SAT_COLORS)

    h, w = image.shape[:2]
    composed = Image.fromarray(image).convert("RGBA")

    # When content_aware is on we suppress RGB-split (the chromatic fringe
    # would re-introduce a colour signature, breaking the camouflage).
    effective_split = 0 if content_aware else split_c

    for i in range(3):
        base = selected[i]
        delta = brightness_c if (i % 2 == 0) else -brightness_c
        shifted = _shift_color_brightness(base, delta)
        layer = _build_layer(
            w,
            h,
            resolved_texts[i],
            shifted,
            float(_LAYER_ROTATIONS_DEG[i]),
            i,
            opacity_c,
            effective_split,
        )

        if content_aware:
            # Sample current composed state so each layer drifts toward the
            # post-watermark colour distribution.
            base_rgb = np.array(composed.convert("RGB"), dtype=np.uint8)
            layer = _content_aware_recolor(layer, base_rgb, delta)

        composed = Image.alpha_composite(composed, layer)

    return np.array(composed.convert("RGB"), dtype=np.uint8)
