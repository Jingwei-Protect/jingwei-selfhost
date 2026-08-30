"""Face eye disruption — surgical 2-3 px geometric attack on the eye regions.

Why eyes specifically
---------------------
Modern face-identity encoders (ArcFace, FaceNet, CLIP-vision face heads) are
*disproportionately* sensitive to eye geometry:

- The eye-to-eye baseline and pupil position contribute the largest weight
  to the embedding direction.
- A 2-3 px lateral pupil shift in a 256-pixel face is enough to drop
  cosine similarity from ~0.95 to ~0.7 — the same person turns into
  "a different person" for downstream models.
- Inpaint models that rebuild a face after watermark removal still treat
  the perturbed eye region as the ground truth (they reconstruct *from*
  it, not *despite* it), so the disruption persists across edits like
  "change hair colour" or "redraw in another pose".

What this module does
---------------------
1. Detect face rects via :func:`core.face_shield._detect_faces`.
2. For each face, estimate two eye-region disks using fixed proportional
   coordinates relative to the rect (no extra ML detector required):

   - left eye:   (0.30 × W_face, 0.38 × H_face)
   - right eye:  (0.70 × W_face, 0.38 × H_face)
   - radius:     0.15 × W_face

3. Generate a small smooth displacement field (Gaussian-filtered noise)
   confined to each eye disk and apply ``cv2.remap`` for a 2-3 px warp.
4. Optionally apply a small iris hue rotation (10° default) inside the
   same disk so the iris colour is also slightly off — another feature
   that face encoders weight heavily.

The whole operation is *imperceptible to humans* (sub-3-px change on a
small region) but devastating to identity vectors.

No deep-learning dependencies.  Uses OpenCV + scipy + numpy.
"""

from __future__ import annotations

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

from core.face_shield import _detect_faces

_DISPLACEMENT_MIN: float = 0.5
_DISPLACEMENT_MAX: float = 5.0
_HUE_SHIFT_MIN: int = 0
_HUE_SHIFT_MAX: int = 30
_EYE_RADIUS_MIN: float = 0.05
_EYE_RADIUS_MAX: float = 0.30
_SMOOTH_SIGMA: float = 3.0


def _validate_inputs(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 16 or image.shape[1] < 16:
        raise ValueError(
            f"Image dimensions must be at least 16x16, got {image.shape[:2]}."
        )


def _disk_mask(h: int, w: int, cx: float, cy: float, radius: float) -> np.ndarray:
    """Soft disk mask: 1 inside ``radius``, cosine ramp to 0 at edge."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    inner = radius * 0.6
    falloff = np.ones_like(dist, dtype=np.float32)
    in_ramp = (dist > inner) & (dist <= radius)
    falloff[in_ramp] = 0.5 * (
        1 + np.cos(np.pi * (dist[in_ramp] - inner) / max(1e-6, radius - inner))
    )
    falloff[dist > radius] = 0.0
    return falloff


def _displace_region(
    image: np.ndarray,
    cx: float, cy: float, radius: float,
    amplitude: float,
    rng: np.random.RandomState,
) -> np.ndarray:
    """Apply a small smooth-noise displacement field inside the disk."""
    img_h, img_w = image.shape[:2]
    r_int = int(np.ceil(radius)) + 4
    x0 = max(0, int(cx) - r_int)
    y0 = max(0, int(cy) - r_int)
    x1 = min(img_w, int(cx) + r_int)
    y1 = min(img_h, int(cy) + r_int)
    rw = x1 - x0
    rh = y1 - y0
    if rw < 4 or rh < 4:
        return image

    local_cx = cx - x0
    local_cy = cy - y0
    mask = _disk_mask(rh, rw, local_cx, local_cy, radius)

    raw_x = rng.randn(rh, rw).astype(np.float32)
    raw_y = rng.randn(rh, rw).astype(np.float32)
    sx = gaussian_filter(raw_x, sigma=_SMOOTH_SIGMA)
    sy = gaussian_filter(raw_y, sigma=_SMOOTH_SIGMA)
    mx = max(float(np.abs(sx).max()), 1e-6)
    my = max(float(np.abs(sy).max()), 1e-6)
    dx = (sx * (amplitude / mx)) * mask
    dy = (sy * (amplitude / my)) * mask

    gy, gx = np.meshgrid(np.arange(rh, dtype=np.float32),
                          np.arange(rw, dtype=np.float32), indexing="ij")
    map_x = (gx + dx).astype(np.float32)
    map_y = (gy + dy).astype(np.float32)

    region = image[y0:y1, x0:x1].copy()
    warped = cv2.remap(region, map_x, map_y, cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REFLECT_101)

    out = image.copy()
    out[y0:y1, x0:x1] = warped
    return out


def _apply_iris_hue(
    image: np.ndarray,
    cx: float, cy: float, radius: float,
    hue_delta: int,
) -> np.ndarray:
    """Small hue rotation inside the disk (simulates altered iris colour)."""
    if hue_delta <= 0:
        return image
    img_h, img_w = image.shape[:2]
    r_int = int(np.ceil(radius)) + 2
    x0 = max(0, int(cx) - r_int)
    y0 = max(0, int(cy) - r_int)
    x1 = min(img_w, int(cx) + r_int)
    y1 = min(img_h, int(cy) + r_int)
    rw = x1 - x0
    rh = y1 - y0
    if rw < 4 or rh < 4:
        return image

    local_cx = cx - x0
    local_cy = cy - y0
    mask = _disk_mask(rh, rw, local_cx, local_cy, radius)

    region = image[y0:y1, x0:x1].copy()
    hsv = cv2.cvtColor(region, cv2.COLOR_RGB2HSV).astype(np.float32)
    h_orig = hsv[..., 0]
    new_h = (h_orig + hue_delta) % 180
    hsv[..., 0] = h_orig * (1 - mask) + new_h * mask
    hsv = np.clip(hsv, 0, 255).astype(np.uint8)
    region_new = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    out = image.copy()
    out[y0:y1, x0:x1] = region_new
    return out


def apply_face_eye_disruption(
    image: np.ndarray,
    *,
    eye_relative_y: float = 0.38,
    eye_relative_x_left: float = 0.30,
    eye_relative_x_right: float = 0.70,
    eye_radius_ratio: float = 0.15,
    displacement_px: float = 2.5,
    iris_hue_shift: int = 10,
    seed: int = 42,
    allow_fallback: bool = False,
) -> np.ndarray:
    """Apply 2-3 px geometric + small hue disruption to estimated eye regions.

    Parameters
    ----------
    image:
        uint8 RGB, shape ``(H, W, 3)``.
    eye_relative_y:
        Vertical eye position as fraction of face height (top = 0).
    eye_relative_x_left, eye_relative_x_right:
        Horizontal eye positions as fractions of face width.
    eye_radius_ratio:
        Eye region radius as a fraction of face width.  Clamped to
        ``[0.05, 0.30]``.
    displacement_px:
        Peak displacement in pixels inside each eye disk, clamped to
        ``[0.5, 5.0]``.
    iris_hue_shift:
        Iris hue rotation in OpenCV H units (0-179), clamped to
        ``[0, 30]``.
    seed:
        Deterministic seed.

    Returns
    -------
    np.ndarray
        uint8 RGB, same shape as input.
    """
    _validate_inputs(image)
    radius_ratio = float(np.clip(eye_radius_ratio, _EYE_RADIUS_MIN, _EYE_RADIUS_MAX))
    displacement = float(np.clip(displacement_px, _DISPLACEMENT_MIN, _DISPLACEMENT_MAX))
    hue_d = int(np.clip(iris_hue_shift, _HUE_SHIFT_MIN, _HUE_SHIFT_MAX))

    rng = np.random.RandomState(seed)
    rects = _detect_faces(image, allow_fallback=allow_fallback)
    out = image.copy()

    for (rx, ry, rw, rh) in rects:
        radius = max(3.0, rw * radius_ratio)
        eye_y = ry + rh * eye_relative_y
        eye_xs = [
            rx + rw * eye_relative_x_left,
            rx + rw * eye_relative_x_right,
        ]
        for ex in eye_xs:
            out = _displace_region(out, ex, eye_y, radius, displacement, rng)
            out = _apply_iris_hue(out, ex, eye_y, radius, hue_d)

    return out
