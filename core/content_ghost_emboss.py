"""Content Ghost Emboss — self-referencing face emboss for stealth protection.

Why this is harder to remove than conventional watermarks
---------------------------------------------------------
Traditional watermarks are colour-orthogonal to the image content: they
have a fixed pattern (text, grid, logo) whose frequency spectrum is
independent of the underlying artwork.  An AI inpainter can learn to
separate the two because they occupy different statistical subspaces.

This module **uses the image's own face region as the emboss template**.
The resulting "ghost face" has exactly the same frequency fingerprint as
the real content.  Any AI attempt to remove or denoise it will also
degrade the genuine facial features — a chicken-and-egg problem.

Algorithm
---------
1. Detect face region via Haar Cascade (reuses ``face_shield._detect_faces``).
2. Extract the face ROI, scale it to ~60 % of original size, and flip
   horizontally (mirror) so the ghost is not a pixel-exact duplicate.
3. Apply a Sobel-based emboss convolution to produce a relief map.
4. Blend the relief onto the full image at low opacity (3-8 %), with
   per-channel sub-pixel shifts (R +1 px, B -1 px) to create subtle
   chromatic aberration that further confuses VAE colour decoding.

Only requires numpy, opencv-python, scipy.  No deep-learning dependencies.
"""

from __future__ import annotations

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

from core.face_shield import _detect_faces


_GHOST_SCALE: float = 0.6
_EMBOSS_KERNEL = np.array(
    [[-2, -1, 0],
     [-1,  1, 1],
     [ 0,  1, 2]], dtype=np.float32,
)
_OPACITY_MIN: float = 0.03
_OPACITY_MAX: float = 0.08
_SMOOTH_SIGMA: float = 1.5


def _validate_inputs(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 32 or image.shape[1] < 32:
        raise ValueError(
            f"Image must be at least 32x32, got {image.shape[:2]}."
        )


def _largest_face_rect(
    image: np.ndarray,
    faces: list[tuple[int, int, int, int]],
) -> tuple[int, int, int, int, np.ndarray]:
    """Return clamped (fx, fy, fw, fh) and the face RGB crop."""
    h, w = image.shape[:2]
    best = max(faces, key=lambda r: r[2] * r[3])
    fx, fy, fw, fh = best
    fx = max(0, fx)
    fy = max(0, fy)
    fw = min(fw, w - fx)
    fh = min(fh, h - fy)
    fw = max(1, fw)
    fh = max(1, fh)
    return fx, fy, fw, fh, image[fy:fy + fh, fx:fx + fw].copy()


def _build_ghost_layer(
    face_patch: np.ndarray,
    target_h: int,
    target_w: int,
    seed: int,
) -> np.ndarray:
    """Build a face-sized ghost emboss layer (target_h × target_w).

    Returns float32 array of shape (target_h, target_w, 3) with values
    roughly in [-1, 1], zero-mean so blending does not shift brightness.
    """
    rng = np.random.default_rng(seed)

    mirrored = face_patch[:, ::-1, :]

    gh = max(8, int(target_h * _GHOST_SCALE))
    gw = max(8, int(target_w * _GHOST_SCALE))
    resized = cv2.resize(mirrored, (gw, gh), interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(resized, cv2.COLOR_RGB2GRAY).astype(np.float32)
    embossed = cv2.filter2D(gray, cv2.CV_32F, _EMBOSS_KERNEL)

    embossed = gaussian_filter(embossed, sigma=_SMOOTH_SIGMA)

    max_abs = float(np.abs(embossed).max())
    if max_abs > 1e-6:
        embossed = embossed / max_abs

    angle = float(rng.uniform(5.0, 15.0))
    center = (gw / 2, gh / 2)
    rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
    embossed = cv2.warpAffine(
        embossed, rot_mat, (gw, gh),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT,
    )

    pad_top = (target_h - gh) // 2
    pad_left = (target_w - gw) // 2

    full = np.zeros((target_h, target_w), dtype=np.float32)
    y_start = max(0, pad_top)
    x_start = max(0, pad_left)
    y_end = min(target_h, pad_top + gh)
    x_end = min(target_w, pad_left + gw)

    src_y_start = max(0, -pad_top)
    src_x_start = max(0, -pad_left)
    src_y_end = src_y_start + (y_end - y_start)
    src_x_end = src_x_start + (x_end - x_start)

    full[y_start:y_end, x_start:x_end] = embossed[
        src_y_start:src_y_end, src_x_start:src_x_end
    ]

    fade_h = max(1, (y_end - y_start) // 8)
    fade_w = max(1, (x_end - x_start) // 8)
    mask = np.zeros_like(full)
    mask[y_start:y_end, x_start:x_end] = 1.0

    for i in range(fade_h):
        factor = i / fade_h
        if y_start + i < target_h:
            mask[y_start + i, x_start:x_end] *= factor
        row = y_end - 1 - i
        if 0 <= row < target_h:
            mask[row, x_start:x_end] *= factor
    for j in range(fade_w):
        factor = j / fade_w
        if x_start + j < target_w:
            mask[y_start:y_end, x_start + j] *= factor
        col = x_end - 1 - j
        if 0 <= col < target_w:
            mask[y_start:y_end, col] *= factor

    full *= mask
    active = mask > 1e-6
    if np.any(active):
        full[active] -= float(full[active].mean())

    ghost_rgb = np.stack([full, full, full], axis=-1)
    return ghost_rgb


def apply_content_ghost_emboss(
    image: np.ndarray,
    *,
    opacity: float = 0.05,
    chromatic_shift: int = 1,
    seed: int = 42,
) -> np.ndarray:
    """Apply self-referencing ghost emboss derived from the image's own face.

    Parameters
    ----------
    image : np.ndarray
        uint8 RGB, shape ``(H, W, 3)``.
    opacity : float
        Blend strength in [0.03, 0.08].  Higher = more visible ghost.
    chromatic_shift : int
        Per-channel horizontal pixel shift.  R shifts right, B shifts left.
        Creates subtle chromatic aberration in the ghost layer.
    seed : int
        RNG seed for deterministic rotation angle.

    Returns
    -------
    np.ndarray
        uint8 RGB, same shape as input.
    """
    _validate_inputs(image)
    opacity = float(np.clip(opacity, _OPACITY_MIN, _OPACITY_MAX))
    chromatic_shift = max(0, min(chromatic_shift, 3))

    h, w = image.shape[:2]
    faces = _detect_faces(image)
    if not faces:
        return image.copy()

    fx, fy, fw, fh, _face_patch = _largest_face_rect(image, faces)
    face_patch = image[fy:fy + fh, fx:fx + fw].copy()
    ghost_local = _build_ghost_layer(face_patch, fh, fw, seed)

    if chromatic_shift > 0:
        ghost_local[:, :, 0] = np.roll(ghost_local[:, :, 0], chromatic_shift, axis=1)
        ghost_local[:, :, 0][:, :chromatic_shift] = 0.0
        ghost_local[:, :, 2] = np.roll(ghost_local[:, :, 2], -chromatic_shift, axis=1)
        ghost_local[:, :, 2][:, -chromatic_shift:] = 0.0

    ghost_full = np.zeros((h, w, 3), dtype=np.float32)
    ghost_full[fy:fy + fh, fx:fx + fw] = ghost_local

    out = image.astype(np.float32) + ghost_full * opacity * 255.0
    return np.clip(out, 0, 255).astype(np.uint8)
