"""Courtesy logo overlay — a visible mark the artist chooses, not an anti-removal layer.

A pasted logo (gray, white, or original colour) is the ordinary stock-photo
watermark. Doubao and similar editors treat that look as something to lift.
This module exists so a creator can still stamp a brand or mark of their own.
It does not claim to survive AI wash-out.

Only numpy and Pillow.
"""

from __future__ import annotations

import io
from typing import Literal

import numpy as np
from PIL import Image

LogoTint = Literal["original", "gray", "white"]
LogoPosition = Literal[
    "bottom_right", "bottom_left", "top_right", "top_left", "center"
]

_MAX_LOGO_SIDE = 2048
_MARGIN = 0.04

_POSITION_ANCHOR: dict[LogoPosition, tuple[float, float]] = {
    "top_left": (0.0, 0.0),
    "top_right": (1.0, 0.0),
    "center": (0.5, 0.5),
    "bottom_left": (0.0, 1.0),
    "bottom_right": (1.0, 1.0),
}


def decode_logo_bytes(data: bytes) -> np.ndarray:
    """Decode an uploaded logo to HxWx4 uint8 RGBA.

    Raises
    ------
    ValueError
        Empty bytes, undecodable image, or a logo with no visible pixels.
    """
    if not data:
        raise ValueError("logo file is empty")
    try:
        img = Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception as exc:
        raise ValueError(f"could not decode logo: {exc}") from exc

    w, h = img.size
    if w < 8 or h < 8:
        raise ValueError(f"logo must be at least 8x8, got {w}x{h}")
    longest = max(w, h)
    if longest > _MAX_LOGO_SIDE:
        scale = _MAX_LOGO_SIDE / longest
        img = img.resize(
            (max(8, int(round(w * scale))), max(8, int(round(h * scale)))),
            Image.Resampling.LANCZOS,
        )
    arr = np.asarray(img, dtype=np.uint8)
    if int(arr[:, :, 3].max()) == 0:
        raise ValueError("logo is fully transparent")
    return arr


def _tint_logo(logo: np.ndarray, tint: LogoTint) -> np.ndarray:
    """Recolour RGB, keep alpha. Gray / white are the usual courtesy-watermark looks."""
    if tint == "original":
        return logo
    out = logo.copy()
    if tint == "gray":
        luma = (
            0.299 * out[:, :, 0] + 0.587 * out[:, :, 1] + 0.114 * out[:, :, 2]
        )
        g = np.clip(luma, 0, 255).astype(np.uint8)
        out[:, :, 0] = g
        out[:, :, 1] = g
        out[:, :, 2] = g
        return out
    # white: keep shape, force RGB to white so it reads as a stock mark
    out[:, :, 0] = 255
    out[:, :, 1] = 255
    out[:, :, 2] = 255
    return out


def _paste_box(
    host_h: int,
    host_w: int,
    mark_h: int,
    mark_w: int,
    position: LogoPosition,
) -> tuple[int, int]:
    """Top-left of the logo so it sits in ``position`` with a small margin."""
    ax, ay = _POSITION_ANCHOR[position]
    mx = int(round(_MARGIN * host_w))
    my = int(round(_MARGIN * host_h))
    x = int(round(ax * (host_w - mark_w)))
    y = int(round(ay * (host_h - mark_h)))
    if position.endswith("left") or position == "center":
        x = max(mx if position.endswith("left") else 0, min(x, host_w - mark_w))
    if position.endswith("right"):
        x = min(host_w - mark_w - mx, max(0, x))
    if position.startswith("top") or position == "center":
        y = max(my if position.startswith("top") else 0, min(y, host_h - mark_h))
    if position.startswith("bottom"):
        y = min(host_h - mark_h - my, max(0, y))
    if position == "center":
        x = max(0, (host_w - mark_w) // 2)
        y = max(0, (host_h - mark_h) // 2)
    return x, y


def apply_logo_watermark(
    image: np.ndarray,
    logo_rgba: np.ndarray,
    *,
    opacity: float = 0.40,
    scale: float = 0.18,
    position: LogoPosition = "bottom_right",
    tint: LogoTint = "gray",
) -> np.ndarray:
    """Alpha-composite a logo onto ``image``.

    ``scale`` is the logo's longest side as a fraction of the host short side.
    ``opacity`` multiplies the logo alpha (0–1). Neither setting is calibrated
    for removal resistance — only for how loud the courtesy mark looks.
    """
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"image must be HxWx3 uint8, got {image.shape} {image.dtype}")
    if logo_rgba.dtype != np.uint8 or logo_rgba.ndim != 3 or logo_rgba.shape[2] != 4:
        raise ValueError(
            f"logo must be HxWx4 uint8 RGBA, got {logo_rgba.shape} {logo_rgba.dtype}"
        )
    if position not in _POSITION_ANCHOR:
        raise ValueError(f"unknown position: {position!r}")
    if tint not in ("original", "gray", "white"):
        raise ValueError(f"unknown tint: {tint!r}")

    opacity = float(np.clip(opacity, 0.05, 1.0))
    scale = float(np.clip(scale, 0.04, 0.55))

    host_h, host_w = image.shape[:2]
    short = min(host_h, host_w)
    target = max(8, int(round(short * scale)))
    lh, lw = logo_rgba.shape[:2]
    longest = max(lh, lw)
    ratio = target / longest
    new_w = max(8, int(round(lw * ratio)))
    new_h = max(8, int(round(lh * ratio)))
    new_w = min(new_w, host_w)
    new_h = min(new_h, host_h)

    resized = np.asarray(
        Image.fromarray(logo_rgba).resize((new_w, new_h), Image.Resampling.LANCZOS),
        dtype=np.uint8,
    )
    tinted = _tint_logo(resized, tint)
    x0, y0 = _paste_box(host_h, host_w, new_h, new_w, position)
    x1, y1 = x0 + new_w, y0 + new_h

    alpha = (tinted[:, :, 3].astype(np.float64) / 255.0) * opacity
    alpha = alpha[:, :, None]
    fg = tinted[:, :, :3].astype(np.float64)
    out = image.copy().astype(np.float64)
    region = out[y0:y1, x0:x1]
    # Crop if the box was clamped oddly (should not happen after min()).
    ah, aw = region.shape[:2]
    out[y0:y1, x0:x1] = fg[:ah, :aw] * alpha[:ah, :aw] + region * (1.0 - alpha[:ah, :aw])
    return np.clip(out, 0, 255).astype(np.uint8)
