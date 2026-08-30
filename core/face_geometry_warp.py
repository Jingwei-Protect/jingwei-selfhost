"""Face geometry warp — subtle landmark distortion to corrupt AI face identity.

Human visual tolerance for facial geometry changes is remarkably high: we
recognise a face as "the same person" even after 2-4 px shifts in eye spacing
or nose position.  AI face encoders (ArcFace, CLIP vision, etc.) are the
opposite — they compute a dense 68/128-landmark coordinate vector and are
**extremely** sensitive to sub-pixel positional changes.

This module exploits that asymmetry:

1. Detect face regions via Haar Cascade (reuses ``face_shield._detect_faces``).
2. For each face, generate a smooth random displacement field (Gaussian-
   filtered white noise) with peak amplitude of 2-5 pixels.
3. Remap the face region using the displacement field (``cv2.remap``).

The result: a human sees the same character; an AI face encoder extracts a
**different** facial identity vector → regenerated poses or edits cannot
maintain face consistency with the original.

Note
----
Earlier versions of this module also applied an asymmetric hue shift to the
left vs right half of the face.  That has been removed because the
rectangular hue boundary produced a visible green/magenta square on faces,
and the same disruption is now done more organically by
:mod:`core.face_blob_disruption` (irregular Perlin blobs).  This module is
now purely a *geometric* attack.

No deep-learning dependencies.  Uses OpenCV, scipy, numpy.
"""

from __future__ import annotations

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

from core.face_shield import _detect_faces

_WARP_AMPLITUDE_MIN: float = 1.0
_WARP_AMPLITUDE_MAX: float = 6.0
_WARP_SMOOTH_SIGMA: float = 7.0
_MARGIN_RATIO: float = 0.15


def _validate_inputs(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 8 or image.shape[1] < 8:
        raise ValueError(
            f"Image dimensions must be at least 8x8, got {image.shape[:2]}."
        )


def _generate_displacement_field(
    h: int, w: int, amplitude: float, sigma: float, rng: np.random.RandomState
) -> tuple[np.ndarray, np.ndarray]:
    """Smooth random displacement field: (dx, dy) arrays, peak ±amplitude px."""
    raw_x = rng.randn(h, w).astype(np.float32)
    raw_y = rng.randn(h, w).astype(np.float32)
    smooth_x = gaussian_filter(raw_x, sigma=sigma)
    smooth_y = gaussian_filter(raw_y, sigma=sigma)
    mx = max(float(np.abs(smooth_x).max()), 1e-6)
    my = max(float(np.abs(smooth_y).max()), 1e-6)
    dx = smooth_x * (amplitude / mx)
    dy = smooth_y * (amplitude / my)
    return dx, dy


def _apply_warp_to_region(
    image: np.ndarray,
    x: int, y: int, w: int, h: int,
    amplitude: float,
    sigma: float,
    rng: np.random.RandomState,
) -> np.ndarray:
    """Warp a rectangular region in-place using a smooth displacement field."""
    img_h, img_w = image.shape[:2]
    margin_h = int(h * _MARGIN_RATIO)
    margin_w = int(w * _MARGIN_RATIO)
    rx0 = max(0, x - margin_w)
    ry0 = max(0, y - margin_h)
    rx1 = min(img_w, x + w + margin_w)
    ry1 = min(img_h, y + h + margin_h)
    rh = ry1 - ry0
    rw = rx1 - rx0
    if rh < 4 or rw < 4:
        return image

    region = image[ry0:ry1, rx0:rx1].copy()

    dx, dy = _generate_displacement_field(rh, rw, amplitude, sigma, rng)

    feather_y = max(1, rh // 6)
    feather_x = max(1, rw // 6)
    fade_y = np.ones(rh, dtype=np.float32)
    fade_y[:feather_y] = np.linspace(0, 1, feather_y)
    fade_y[-feather_y:] = np.linspace(1, 0, feather_y)
    fade_x = np.ones(rw, dtype=np.float32)
    fade_x[:feather_x] = np.linspace(0, 1, feather_x)
    fade_x[-feather_x:] = np.linspace(1, 0, feather_x)
    fade = fade_y[:, None] * fade_x[None, :]
    dx *= fade
    dy *= fade

    gy, gx = np.meshgrid(np.arange(rh, dtype=np.float32),
                          np.arange(rw, dtype=np.float32), indexing="ij")
    map_x = (gx + dx).astype(np.float32)
    map_y = (gy + dy).astype(np.float32)

    warped = cv2.remap(region, map_x, map_y, cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REFLECT_101)

    out = image.copy()
    out[ry0:ry1, rx0:rx1] = warped
    return out


def apply_face_geometry_warp(
    image: np.ndarray,
    *,
    warp_amplitude: float = 3.0,
    seed: int = 42,
    allow_fallback: bool = False,
) -> np.ndarray:
    """Subtly warp face geometry to corrupt AI face identity encoders.

    Parameters
    ----------
    image:
        uint8 RGB, shape ``(H, W, 3)``.
    warp_amplitude:
        Peak displacement in pixels, clamped to ``[1.0, 6.0]``.
        2-3 px is imperceptible to humans but shifts AI face landmarks.
        4-5 px is still mostly imperceptible on illustration faces.
    seed:
        Deterministic seed for displacement field generation.

    Returns
    -------
    np.ndarray
        uint8 RGB, same shape as input.
    """
    _validate_inputs(image)
    amplitude = float(np.clip(warp_amplitude, _WARP_AMPLITUDE_MIN, _WARP_AMPLITUDE_MAX))

    rng = np.random.RandomState(seed)
    rects = _detect_faces(image, allow_fallback=allow_fallback)

    out = image.copy()
    for (rx, ry, rw, rh) in rects:
        out = _apply_warp_to_region(out, rx, ry, rw, rh, amplitude, _WARP_SMOOTH_SIGMA, rng)

    return out
