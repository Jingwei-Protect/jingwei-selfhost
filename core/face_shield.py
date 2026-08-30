"""Face Shield -- localized face-region disruption for delivery images.

Uses OpenCV's built-in Haar Cascade classifier to detect face regions, then
applies high-frequency crosshatch grid and diagonal text overlay specifically
within detected face bounding boxes.

Haar Cascade limitation: trained on real-world photographs.  For anime /
illustrated faces the classifier will usually miss, triggering the center-1/3
fallback.  This is acceptable for MVP; a future upgrade could use a different
cascade or accept user-drawn ROIs.

No deep-learning dependencies.  Uses OpenCV (traditional CV), Pillow, numpy.
"""

from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from core.text_fonts import get_text_font as _get_font

# Cascades are loaded lazily so importing this module never requires
# ``cv2.CascadeClassifier`` (product face-emboss boxes use ``center_roi`` and
# must keep working even if OpenCV's Haar API is missing/broken on a host).
_CASCADE: Any | None = None
_PROFILE_CASCADE: Any | None = None
_ALT_CASCADE: Any | None = None
_UPPERBODY_CASCADE: Any | None = None
_CASCADES_READY: bool = False
_CASCADE_API_AVAILABLE: bool = False


def _load_cascade(filename: str) -> Any | None:
    """Load one Haar XML; return None if API/file unavailable."""
    classifier_cls = getattr(cv2, "CascadeClassifier", None)
    data = getattr(cv2, "data", None)
    if classifier_cls is None or data is None:
        return None
    haarcascades = getattr(data, "haarcascades", None)
    if not haarcascades:
        return None
    cascade = classifier_cls(haarcascades + filename)
    if cascade is None or cascade.empty():
        return None
    return cascade


def _ensure_cascades() -> bool:
    """Lazily initialize Haar cascades. Returns True if at least one loaded."""
    global _CASCADE, _PROFILE_CASCADE, _ALT_CASCADE, _UPPERBODY_CASCADE
    global _CASCADES_READY, _CASCADE_API_AVAILABLE
    if _CASCADES_READY:
        return _CASCADE_API_AVAILABLE
    _CASCADES_READY = True
    try:
        _CASCADE = _load_cascade("haarcascade_frontalface_default.xml")
        _ALT_CASCADE = _load_cascade("haarcascade_frontalface_alt2.xml")
        _PROFILE_CASCADE = _load_cascade("haarcascade_profileface.xml")
        _UPPERBODY_CASCADE = _load_cascade("haarcascade_upperbody.xml")
    except Exception:
        _CASCADE = _ALT_CASCADE = _PROFILE_CASCADE = _UPPERBODY_CASCADE = None
    _CASCADE_API_AVAILABLE = any(
        c is not None for c in (_CASCADE, _ALT_CASCADE, _PROFILE_CASCADE, _UPPERBODY_CASCADE)
    )
    return _CASCADE_API_AVAILABLE


def _fallback_face_box(w: int, h: int) -> tuple[int, int, int, int]:
    """Fallback ROI when face detection misses (anime/illustration faces).

    For vertical portrait images the face sits near the **top** of the frame,
    not the centre.  We pick the central 50% of the width and the top ~1/3
    (with a small top margin so a tight headshot also lands inside).
    For square / wide images the same proportions still cover the upper-
    central area where faces typically appear.
    """
    fx = w // 4
    fy = max(1, h // 12)
    fw = w // 2
    fh = h // 3
    fw = min(fw, w - fx)
    fh = min(fh, h - fy)
    return (fx, fy, fw, fh)


def _detect_faces(
    image: np.ndarray,
    *,
    allow_fallback: bool = True,
) -> list[tuple[int, int, int, int]]:
    """Detect faces via multiple Haar Cascades with cascading fallback.

    Detection order:
    1. Frontal face (default) — best for photos
    2. Frontal face (alt2) — better with some illustrations
    3. Profile face — catches side-facing portraits
    4. Upper body — if no face found, find the torso and estimate face
       position as the top 40% of the upper-body rect
    5. Heuristic fallback — upper-central 50% width, top 1/3 height
       (only when ``allow_fallback=True``)

    Returns list of (x, y, w, h) tuples clamped to image boundaries.
    """
    h, w = image.shape[:2]
    _ensure_cascades()
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    min_face = (max(20, w // 15), max(20, h // 15))

    for cascade in (_CASCADE, _ALT_CASCADE, _PROFILE_CASCADE):
        if cascade is None:
            continue
        detections = cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=4, minSize=min_face,
        )
        if len(detections) > 0:
            rects: list[tuple[int, int, int, int]] = []
            for (rx, ry, rw, rh) in detections:
                rx = max(0, int(rx))
                ry = max(0, int(ry))
                rw = min(int(rw), w - rx)
                rh = min(int(rh), h - ry)
                if rw > 0 and rh > 0:
                    rects.append((rx, ry, rw, rh))
            if rects:
                return rects

    if _UPPERBODY_CASCADE is not None:
        body_dets = _UPPERBODY_CASCADE.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=3,
            minSize=(max(30, w // 8), max(30, h // 8)),
        )
        if len(body_dets) > 0:
            bx, by, bw, bh = body_dets[0]
            fx = max(0, int(bx + bw * 0.15))
            fy = max(0, int(by))
            fw = min(int(bw * 0.7), w - fx)
            fh = min(int(bh * 0.4), h - fy)
            if fw > 0 and fh > 0:
                return [(fx, fy, fw, fh)]

    if allow_fallback:
        return [_fallback_face_box(w, h)]
    return []


def _draw_crosshatch(
    overlay: ImageDraw.ImageDraw,
    x: int, y: int, w: int, h: int,
    spacing: int,
    color: tuple[int, int, int, int],
) -> None:
    """Draw horizontal, vertical, and diagonal lines within (x, y, x+w, y+h)."""
    x2, y2 = x + w, y + h

    for ly in range(y, y2, spacing):
        overlay.line([(x, ly), (x2, ly)], fill=color, width=1)
    for lx in range(x, x2, spacing):
        overlay.line([(lx, y), (lx, y2)], fill=color, width=1)

    for offset in range(-max(w, h), max(w, h), spacing):
        p1 = (x + offset, y)
        p2 = (x + offset + h, y2)
        overlay.line([p1, p2], fill=color, width=1)
        p3 = (x + offset, y2)
        p4 = (x + offset + h, y)
        overlay.line([p3, p4], fill=color, width=1)


def apply_face_shield(
    image: np.ndarray,
    *,
    overlay_text: str = "PREVIEW",
    grid_opacity: float = 0.30,
    text_opacity: float = 0.35,
    seed: int = 42,
) -> np.ndarray:
    """Apply localized crosshatch + text disruption over detected face regions.

    Parameters
    ----------
    image : np.ndarray
        RGB uint8, shape ``(H, W, 3)``.
    overlay_text : str
        Text rendered diagonally over each face region.
    grid_opacity : float
        Opacity for the crosshatch grid pattern.
    text_opacity : float
        Opacity for the diagonal text overlay.
    seed : int
        Controls minor grid spacing jitter for determinism.

    Returns
    -------
    np.ndarray
        RGB uint8, same shape as input.
    """
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Input must be uint8 RGB with shape (H, W, 3).")

    rng = np.random.RandomState(seed)
    h, w = image.shape[:2]
    rects = _detect_faces(image)

    base = Image.fromarray(image).convert("RGBA")

    for (rx, ry, rw, rh) in rects:
        raw_spacing = max(rw, rh) // 8
        spacing = max(4, raw_spacing + rng.randint(-1, 2))

        grid_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(grid_layer)
        _draw_crosshatch(draw, rx, ry, rw, rh, spacing, (128, 128, 128, 255))

        grid_arr = np.array(grid_layer, dtype=np.float32)
        grid_arr[:, :, 3] = (grid_arr[:, :, 3] * grid_opacity).clip(0, 255)
        grid_layer = Image.fromarray(grid_arr.astype(np.uint8))
        base = Image.alpha_composite(base, grid_layer)

        font_size = max(12, rw // 4)
        font = _get_font(font_size, overlay_text)

        text_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        txt_draw = ImageDraw.Draw(text_layer)

        bbox = txt_draw.textbbox((0, 0), overlay_text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        tile = Image.new("RGBA", (tw + font_size, th + font_size), (0, 0, 0, 0))
        ImageDraw.Draw(tile).text(
            (font_size // 2, font_size // 2),
            overlay_text,
            font=font,
            fill=(255, 255, 255, 255),
        )
        tile = tile.rotate(35, expand=True, resample=Image.BICUBIC)

        tile_w, tile_h = tile.size
        cx = rx + rw // 2 - tile_w // 2
        cy = ry + rh // 2 - tile_h // 2
        text_layer.paste(tile, (cx, cy), tile)

        txt_arr = np.array(text_layer, dtype=np.float32)
        txt_arr[:, :, 3] = (txt_arr[:, :, 3] * text_opacity).clip(0, 255)
        text_layer = Image.fromarray(txt_arr.astype(np.uint8))
        base = Image.alpha_composite(base, text_layer)

    return np.array(base.convert("RGB"), dtype=np.uint8)
