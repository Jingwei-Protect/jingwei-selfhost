"""Triple watermark - colour-offset diagonal-band visible overlay.

Renders three independent diagonal text bands in three different colours and
rotations.  Each band crosses the central 80% of the image, so the watermark
text crosses the main subject area (face, body, hands) like a cancellation
stamp.

Why this targets inpainting performance:
- Each layer is an independent, non-axis-aligned text band in its own
  colour signature, and each band crosses where the AI editor most wants to
  preserve detail.
- Inpainting models typically excel at removing a single repetitive overlay
  but degrade quickly with multiple overlapping non-coincident patterns.
- A human reader can still parse the underlying subject through the three
  translucent bands.

Uses only numpy and Pillow.  No deep-learning dependencies.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from core.text_fonts import get_text_font as _get_font

DEFAULT_TRIPLE_TEXTS: list[str] = [
    "COPYRIGHT PROTECTED",
    "PREVIEW ONLY - DO NOT EDIT",
    "\u7248\u6b0a\u6240\u6709 \u7981\u6b62AI\u6539\u5716",
]

DEFAULT_TRIPLE_COLORS: list[tuple[int, int, int]] = [
    (255, 80, 80),
    (80, 255, 80),
    (80, 80, 255),
]

_LAYER_ROTATIONS_DEG: tuple[int, int, int] = (30, 50, 70)


def _validate_inputs(
    image: np.ndarray,
    texts: list[str],
    colors: list[tuple[int, int, int]],
    opacity: float,
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
        raise ValueError(f"texts must be a list of exactly 3 strings, got {texts!r}.")
    if not all(isinstance(t, str) and t for t in texts):
        raise ValueError("each text entry must be a non-empty string.")
    if not isinstance(colors, list) or len(colors) != 3:
        raise ValueError(
            f"colors must be a list of exactly 3 (r, g, b) tuples, got {colors!r}."
        )
    for c in colors:
        if (
            not isinstance(c, tuple)
            or len(c) != 3
            or not all(isinstance(v, (int, np.integer)) for v in c)
        ):
            raise ValueError(f"each color must be a (r, g, b) int tuple, got {c!r}.")
    if not (0.0 <= opacity <= 1.0):
        raise ValueError(f"opacity must be in [0.0, 1.0], got {opacity}.")


def _build_layer(
    h: int,
    w: int,
    text: str,
    color: tuple[int, int, int],
    rotation_deg: int,
    layer_index: int,
    opacity: float,
) -> Image.Image:
    """Build an RGBA layer of diagonal text bands crossing the central 80%.

    layer_index controls vertical band placement so the three layers crisscross.
    """
    font_size = max(12, max(h, w) // 18)
    font = _get_font(font_size, text)

    dummy = Image.new("RGBA", (1, 1))
    bbox = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
    tw = max(1, bbox[2] - bbox[0])
    th = max(1, bbox[3] - bbox[1])

    alpha = int(max(0, min(255, round(opacity * 255))))
    fill = (int(color[0]), int(color[1]), int(color[2]), alpha)

    spacing = font_size * 4
    diag = int((h * h + w * w) ** 0.5) + spacing
    strip_h = th + font_size

    strip = Image.new("RGBA", (diag, strip_h), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(strip)
    x = 0
    while x < diag:
        sdraw.text((x, font_size // 4), text, font=font, fill=fill)
        x += tw + spacing

    rotated = strip.rotate(rotation_deg, expand=True, resample=Image.BICUBIC)
    rw, rh = rotated.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    margin_y = int(h * 0.10)
    usable_h = h - 2 * margin_y
    band_spacing = max(strip_h + font_size, max(usable_h // 5, 1))
    start_offset = layer_index * (band_spacing // 3)

    cx = w // 2 - rw // 2
    y = margin_y + start_offset - rh // 2
    while y < h - margin_y + rh:
        overlay.paste(rotated, (cx, y), rotated)
        y += band_spacing

    return overlay


def apply_triple_watermark(
    image: np.ndarray,
    *,
    texts: list[str] | None = None,
    colors: list[tuple[int, int, int]] | None = None,
    opacity: float = 0.18,
    seed: int = 42,
) -> np.ndarray:
    """Stack three colour-offset diagonal-band watermark layers onto ``image``.

    Parameters
    ----------
    image:
        uint8 RGB, shape (H, W, 3).
    texts:
        Three watermark strings.  ``None`` selects :data:`DEFAULT_TRIPLE_TEXTS`.
    colors:
        Three (r, g, b) tuples.  ``None`` selects :data:`DEFAULT_TRIPLE_COLORS`.
    opacity:
        Per-layer alpha in ``[0.0, 1.0]``.  Default 0.18.
    seed:
        Accepted for API symmetry; the transform is deterministic.

    Returns
    -------
    np.ndarray
        uint8 RGB, same shape as input.
    """
    del seed
    resolved_texts: list[str] = (
        list(texts) if texts is not None else list(DEFAULT_TRIPLE_TEXTS)
    )
    resolved_colors: list[tuple[int, int, int]] = (
        list(colors) if colors is not None else list(DEFAULT_TRIPLE_COLORS)
    )
    _validate_inputs(image, resolved_texts, resolved_colors, opacity)

    h, w = image.shape[:2]
    base = Image.fromarray(image).convert("RGBA")

    composed = base
    for i in range(3):
        layer = _build_layer(
            h,
            w,
            resolved_texts[i],
            resolved_colors[i],
            _LAYER_ROTATIONS_DEG[i],
            i,
            opacity,
        )
        composed = Image.alpha_composite(composed, layer)

    return np.array(composed.convert("RGB"), dtype=np.uint8)
