"""Face Stroke Injection — plant dark brush-strokes on bright facial areas.

For grayscale artwork, colour-based watermarks are trivially removed by AI
denoisers because they appear as "out-of-distribution" coloured noise on a
monochrome canvas.  This module instead injects **dark line segments** that
mimic the original artist's brush-strokes:

1. Detect face region (reuses face_shield._detect_faces).
2. Within the face ROI, find bright zones (luminance > threshold).
3. Sample the dominant stroke direction from the original artwork edges.
4. Generate short dark strokes (3-15px long) at random positions in the
   bright zones, oriented along the dominant direction ± random jitter.
5. Each stroke tapers at its ends (anti-aliased) so it blends smoothly.

Because the strokes look indistinguishable from the artist's own lines,
AI cannot selectively remove them without destroying legitimate artwork.

Only requires numpy, opencv-python, Pillow.
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image, ImageDraw


def _detect_faces_for_strokes(image: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Lightweight face detection — import from face_shield to avoid duplication."""
    try:
        from core.face_shield import _detect_faces
        return _detect_faces(image)
    except Exception:
        h, w = image.shape[:2]
        fx = w // 4
        fy = max(1, h // 12)
        fw = w // 2
        fh = h // 3
        return [(fx, fy, min(fw, w - fx), min(fh, h - fy))]


def _dominant_stroke_angle(gray_roi: np.ndarray) -> float:
    """Estimate dominant edge direction in a grayscale ROI using Sobel."""
    sx = cv2.Sobel(gray_roi, cv2.CV_64F, 1, 0, ksize=3)
    sy = cv2.Sobel(gray_roi, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.sqrt(sx ** 2 + sy ** 2)
    threshold = np.percentile(mag, 75)
    mask = mag > threshold
    if mask.sum() < 10:
        return 0.0
    angles = np.arctan2(sy[mask], sx[mask])
    hist, bin_edges = np.histogram(angles, bins=36, range=(-np.pi, np.pi))
    peak_idx = int(np.argmax(hist))
    return float((bin_edges[peak_idx] + bin_edges[peak_idx + 1]) / 2.0)


def apply_face_stroke_injection(
    image: np.ndarray,
    *,
    n_strokes: int = 40,
    stroke_length_range: tuple[int, int] = (4, 18),
    stroke_width_range: tuple[int, int] = (1, 3),
    brightness_threshold: int = 140,
    darkness: int = 45,
    angle_jitter: float = 0.5,
    seed: int = 42,
) -> np.ndarray:
    """Inject dark brush-stroke fragments onto bright facial regions.

    Parameters
    ----------
    image : np.ndarray
        uint8 RGB, shape ``(H, W, 3)``.
    n_strokes : int
        Number of strokes to inject per face region.
    stroke_length_range : tuple
        (min, max) pixel length of each stroke.
    stroke_width_range : tuple
        (min, max) pixel width of each stroke.
    brightness_threshold : int
        Only inject strokes on pixels brighter than this (0-255).
    darkness : int
        How much to darken the stroke vs local brightness. Higher = darker.
    angle_jitter : float
        Random angular deviation from dominant direction (radians).
    seed : int
        RNG seed for reproducibility.

    Returns
    -------
    np.ndarray
        uint8 RGB with strokes injected.
    """
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 32 or image.shape[1] < 32:
        raise ValueError(f"Image must be at least 32x32, got {image.shape[:2]}.")

    rng = np.random.default_rng(seed)
    h, w = image.shape[:2]
    darkness = int(np.clip(darkness, 10, 80))

    faces = _detect_faces_for_strokes(image)
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    pil_img = Image.fromarray(image)
    draw = ImageDraw.Draw(pil_img)

    for (fx, fy, fw, fh) in faces:
        fx = max(0, fx)
        fy = max(0, fy)
        fw = min(fw, w - fx)
        fh = min(fh, h - fy)
        if fw < 8 or fh < 8:
            continue

        roi_gray = gray[fy:fy + fh, fx:fx + fw]
        dominant_angle = _dominant_stroke_angle(roi_gray)

        bright_mask = roi_gray > brightness_threshold
        bright_coords = np.argwhere(bright_mask)
        if len(bright_coords) < 5:
            bright_mask = roi_gray > (brightness_threshold - 40)
            bright_coords = np.argwhere(bright_mask)
        if len(bright_coords) < 5:
            continue

        actual_strokes = min(n_strokes, len(bright_coords))
        chosen_indices = rng.choice(len(bright_coords), size=actual_strokes, replace=False)

        for idx in chosen_indices:
            ly, lx = bright_coords[idx]
            gy, gx = fy + ly, fx + lx

            length = int(rng.integers(stroke_length_range[0], stroke_length_range[1] + 1))
            width = int(rng.integers(stroke_width_range[0], stroke_width_range[1] + 1))
            angle = dominant_angle + float(rng.uniform(-angle_jitter, angle_jitter))

            dx = int(round(length * np.cos(angle) / 2))
            dy = int(round(length * np.sin(angle) / 2))

            x0 = max(0, min(w - 1, gx - dx))
            y0 = max(0, min(h - 1, gy - dy))
            x1 = max(0, min(w - 1, gx + dx))
            y1 = max(0, min(h - 1, gy + dy))

            local_bright = int(gray[gy, gx])
            stroke_val = max(0, local_bright - darkness - int(rng.integers(0, 15)))
            color = (stroke_val, stroke_val, stroke_val)

            draw.line([(x0, y0), (x1, y1)], fill=color, width=width)

    return np.array(pil_img, dtype=np.uint8)
