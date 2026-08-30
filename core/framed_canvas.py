"""Framed canvas — wrap the original image in a poisoned border.

Instead of perturbing pixels of the artwork itself, this mode places the
original image at the centre of a larger canvas and fills the border with
diagonal stripes and rotated copyright text.  The image area is preserved
exactly; only the surrounding border is new.

Why this can disrupt AI editing:
- Many edit pipelines crop / resize the *whole* image; the border text and
  stripe pattern enters the model's input space and can confuse subject
  localisation.
- Inpainting models that try to extend the canvas are forced to reckon
  with the high-contrast diagonal stripes and copyright text.

Uses only Pillow and numpy.  No deep-learning dependencies.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from core.text_fonts import get_text_font as _get_font

DEFAULT_FRAMED_CANVAS_TEXT = (
    "COPYRIGHT PROTECTED \u2014 Preview Only "
    "\u2014 Unauthorized AI Editing Prohibited"
)

_BORDER_BG = (40, 40, 40)
_STRIPE_COLOR = (70, 70, 70)
_TEXT_COLOR = (180, 180, 180)
_STRIPE_SPACING = 8
_STRIPE_WIDTH = 2

_BORDER_RATIO_MIN = 0.08
_BORDER_RATIO_MAX = 0.20


def _validate_inputs(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 8 or image.shape[1] < 8:
        raise ValueError(
            f"Image dimensions must be at least 8x8, got {image.shape[:2]}."
        )


def apply_framed_canvas(
    image: np.ndarray,
    *,
    border_text: str = "",
    border_ratio: float = 0.125,
    seed: int = 42,
) -> np.ndarray:
    """Place *image* on a larger canvas with a poisoned diagonal-stripe border.

    Parameters
    ----------
    image : np.ndarray
        RGB uint8, shape ``(H, W, 3)``.
    border_text : str
        Text rendered along the border.  Empty falls back to
        ``DEFAULT_FRAMED_CANVAS_TEXT``.
    border_ratio : float
        Border thickness as a fraction of input dimensions, clamped to
        ``[0.08, 0.20]``.
    seed : int
        Accepted for API symmetry; the transform is deterministic.

    Returns
    -------
    np.ndarray
        RGB uint8, shape ``(H + 2*border_h, W + 2*border_w, 3)``.
    """
    del seed
    _validate_inputs(image)

    ratio = float(np.clip(border_ratio, _BORDER_RATIO_MIN, _BORDER_RATIO_MAX))
    text = border_text.strip() if border_text and border_text.strip() else DEFAULT_FRAMED_CANVAS_TEXT

    h, w = image.shape[:2]
    border_h = max(1, int(h * ratio))
    border_w = max(1, int(w * ratio))

    out_h = h + 2 * border_h
    out_w = w + 2 * border_w

    canvas = Image.new("RGB", (out_w, out_h), _BORDER_BG)
    draw = ImageDraw.Draw(canvas)

    inner_x0 = border_w
    inner_y0 = border_h
    inner_x1 = border_w + w
    inner_y1 = border_h + h

    for offset in range(-out_h, out_w + out_h, _STRIPE_SPACING):
        p1 = (offset, 0)
        p2 = (offset + out_h, out_h)
        draw.line([p1, p2], fill=_STRIPE_COLOR, width=_STRIPE_WIDTH)

    canvas.paste(Image.fromarray(image), (inner_x0, inner_y0))

    font_size = max(10, border_h // 4)
    font = _get_font(font_size, text)

    dummy = Image.new("RGBA", (1, 1))
    bbox = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    strip_w = max(out_w, out_h) + tw
    text_layer = Image.new("RGBA", (strip_w, th + font_size), (0, 0, 0, 0))
    tlayer_draw = ImageDraw.Draw(text_layer)
    x = 0
    spacing = tw + font_size * 2
    while x < strip_w:
        tlayer_draw.text((x, font_size // 4), text, font=font, fill=_TEXT_COLOR + (255,))
        x += spacing

    rotated = text_layer.rotate(45, expand=True, resample=Image.BICUBIC)
    rtw, rth = rotated.size

    overlay = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))
    overlay.paste(rotated, ((out_w - rtw) // 2, (out_h - rth) // 2), rotated)

    border_mask = Image.new("L", (out_w, out_h), 255)
    ImageDraw.Draw(border_mask).rectangle(
        [inner_x0, inner_y0, inner_x1 - 1, inner_y1 - 1], fill=0
    )

    ov_arr = np.array(overlay, dtype=np.uint8)
    mask_arr = np.array(border_mask, dtype=np.uint8)
    ov_arr[..., 3] = (ov_arr[..., 3].astype(np.uint16) * mask_arr // 255).astype(np.uint8)
    overlay = Image.fromarray(ov_arr)

    canvas_rgba = canvas.convert("RGBA")
    composed = Image.alpha_composite(canvas_rgba, overlay)
    return np.array(composed.convert("RGB"), dtype=np.uint8)
