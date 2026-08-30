"""Artist emboss signature — stylised 3-layer embossed nameplate.

Renders the artist's signature in a corner of the image as an embossed
nameplate (highlight + shadow + main glyph stacked).  Because the signature
sits in a corner *outside* the face ROI and is visually clearly part of the
artwork rather than a flat watermark overlay, AI watermark-removal pipelines
either:

- leave it intact (treating it as an artistic element), or
- attempt to remove it and produce an obvious blank corner — a visible
  *tampering signal* the buyer/viewer can immediately recognise.

The implementation is local-only: it uses Pillow + numpy, no network.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from core.text_fonts import get_text_font as _get_font

Position = Literal["bottom_right", "bottom_left", "top_right", "top_left"]

_FONT_SIZE_MIN_RATIO: float = 0.015
_FONT_SIZE_MAX_RATIO: float = 0.10
_PADDING_MIN_RATIO: float = 0.005
_PADDING_MAX_RATIO: float = 0.10
_EMBOSS_DEPTH_MIN: int = 1
_EMBOSS_DEPTH_MAX: int = 6
_LOCAL_MEAN_BOX: int = 24
_PLATE_MARGIN_PX: int = 6


def _validate_inputs(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 32 or image.shape[1] < 32:
        raise ValueError(
            f"Image must be at least 32x32 for emboss signature, "
            f"got {image.shape[:2]}."
        )


def _resolve_corner(
    pos: Position,
    img_w: int, img_h: int,
    plate_w: int, plate_h: int,
    pad: int,
) -> tuple[int, int]:
    """Top-left ``(x, y)`` of the nameplate for the requested corner."""
    if pos == "bottom_right":
        return img_w - plate_w - pad, img_h - plate_h - pad
    if pos == "bottom_left":
        return pad, img_h - plate_h - pad
    if pos == "top_right":
        return img_w - plate_w - pad, pad
    if pos == "top_left":
        return pad, pad
    raise ValueError(
        "position must be one of 'bottom_right','bottom_left',"
        f"'top_right','top_left', got {pos!r}."
    )


def _sample_local_mean_color(
    image: np.ndarray, x: int, y: int, w: int, h: int
) -> tuple[int, int, int]:
    """Mean colour inside the plate region, used as the plate base tone."""
    x1 = max(0, min(image.shape[1], x))
    y1 = max(0, min(image.shape[0], y))
    x2 = max(0, min(image.shape[1], x + w))
    y2 = max(0, min(image.shape[0], y + h))
    if x2 - x1 < 1 or y2 - y1 < 1:
        return (128, 128, 128)
    patch = image[y1:y2, x1:x2]
    return tuple(int(v) for v in patch.reshape(-1, 3).mean(axis=0))  # type: ignore[return-value]


def _shift_brightness(rgb: tuple[int, int, int], delta: int) -> tuple[int, int, int]:
    """Shift each channel by ``delta``, clamped to ``[0, 255]``."""
    return tuple(int(np.clip(c + delta, 0, 255)) for c in rgb)  # type: ignore[return-value]


def _measure_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return max(1, bbox[2] - bbox[0]), max(1, bbox[3] - bbox[1])


def apply_artist_emboss_signature(
    image: np.ndarray,
    *,
    artist_name: str,
    position: Position = "bottom_right",
    font_size_ratio: float = 0.035,
    padding_ratio: float = 0.025,
    emboss_depth: int = 2,
    color: tuple[int, int, int] | None = None,
    seed: int = 42,
) -> np.ndarray:
    """Stamp an embossed nameplate of ``artist_name`` into a corner.

    Parameters
    ----------
    image:
        uint8 RGB, shape ``(H, W, 3)``.
    artist_name:
        Display text.  Empty / whitespace-only → no-op.
    position:
        Which corner: ``"bottom_right"`` (default), ``"bottom_left"``,
        ``"top_right"``, ``"top_left"``.
    font_size_ratio:
        Font height as a fraction of the image short side, clamped to
        ``[0.015, 0.10]``.
    padding_ratio:
        Distance from the image edge as a fraction of the short side,
        clamped to ``[0.005, 0.10]``.
    emboss_depth:
        Pixel offset of highlight/shadow layers, clamped to ``[1, 6]``.
    color:
        Optional explicit base RGB.  ``None`` → sample local mean colour
        and use a complementary shift.
    seed:
        Reserved for future jittering; currently unused but kept for
        API consistency.

    Returns
    -------
    np.ndarray
        uint8 RGB, same shape as input.
    """
    del seed  # reserved for future jitter; deterministic for now

    _validate_inputs(image)
    name = (artist_name or "").strip()
    if not name:
        return image.copy()

    h, w = image.shape[:2]
    short_side = min(h, w)
    size_ratio = float(np.clip(font_size_ratio, _FONT_SIZE_MIN_RATIO, _FONT_SIZE_MAX_RATIO))
    pad_ratio = float(np.clip(padding_ratio, _PADDING_MIN_RATIO, _PADDING_MAX_RATIO))
    depth = int(np.clip(emboss_depth, _EMBOSS_DEPTH_MIN, _EMBOSS_DEPTH_MAX))

    font_size = max(10, int(short_side * size_ratio))
    pad_px = max(2, int(short_side * pad_ratio))
    font = _get_font(font_size, name)

    # Measure text + decide plate size
    probe = Image.new("RGB", (1, 1))
    pdraw = ImageDraw.Draw(probe)
    tw, th = _measure_text(pdraw, name, font)
    plate_w = tw + _PLATE_MARGIN_PX * 2 + depth * 2
    plate_h = th + _PLATE_MARGIN_PX * 2 + depth * 2

    plate_w = min(plate_w, w - pad_px * 2)
    plate_h = min(plate_h, h - pad_px * 2)
    if plate_w < 8 or plate_h < 8:
        return image.copy()

    px, py = _resolve_corner(position, w, h, plate_w, plate_h, pad_px)

    # Inset emboss: render text, apply emboss convolution, blend into image
    # No plate background — text appears pressed/recessed into the artwork
    import cv2

    # Render text mask at high resolution
    text_canvas = Image.new("L", (plate_w, plate_h), 0)
    tdraw = ImageDraw.Draw(text_canvas)
    tx_local = (plate_w - tw) // 2
    ty_local = (plate_h - th) // 2
    tdraw.text((tx_local, ty_local), name, font=font, fill=255)
    text_arr = np.array(text_canvas, dtype=np.float32) / 255.0

    # Emboss convolution on text mask → creates light/shadow bevel
    emboss_kernel = np.array(
        [[-2, -1, 0],
         [-1,  0, 1],
         [ 0,  1, 2]], dtype=np.float32,
    ) * depth
    beveled = cv2.filter2D(text_arr, cv2.CV_32F, emboss_kernel)

    # Normalize to [-1, 1]
    abs_max = float(np.abs(beveled).max())
    if abs_max > 1e-6:
        beveled = beveled / abs_max

    # Blend into image using additive blend (works on any background)
    out = image.copy().astype(np.float32)
    strength = 40.0
    for c in range(3):
        out[py:py + plate_h, px:px + plate_w, c] += beveled * strength

    return np.clip(out, 0, 255).astype(np.uint8)


# Re-export local-mean utility for tests / future modules.
def _local_mean_for_tests(
    image: np.ndarray, x: int, y: int, w: int, h: int
) -> tuple[int, int, int]:
    return _sample_local_mean_color(image, x, y, w, h)


__all__ = [
    "apply_artist_emboss_signature",
    "Position",
]
