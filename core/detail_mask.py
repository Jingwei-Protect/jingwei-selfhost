"""Detail mask — edge/texture-weighted mask for perceptual hiding.

Human vision is very sensitive to colour shifts on smooth, flat areas
(skin, sky, uniform backgrounds) but tolerant of perturbations on
edges, textures, and fine details.  AI models, on the other hand,
heavily rely on edge and texture information to reconstruct images.

This module generates a [0,1] mask where:
  - 1.0 = high-detail region (edges, textures)  → attack at full strength
  - 0.0 = flat region (skin, background)         → nearly zero attack

Usage:
    mask = compute_detail_mask(image)
    perturbed_channel = original + shift * mask

Only requires numpy and opencv-python.
"""

from __future__ import annotations

import cv2
import numpy as np


def compute_detail_mask(
    image: np.ndarray,
    *,
    blur_ksize: int = 15,
    clip_percentile: float = 95.0,
) -> np.ndarray:
    """Compute a normalised detail/edge mask from an RGB image.

    Parameters
    ----------
    image : np.ndarray
        uint8 RGB, shape ``(H, W, 3)``.
    blur_ksize : int
        Gaussian kernel size to soften the mask edges. Must be odd.
    clip_percentile : float
        Top percentile for clipping before normalisation. Prevents
        a few extreme-edge pixels from compressing the rest of the
        range.

    Returns
    -------
    np.ndarray
        float32, shape ``(H, W)``, values in ``[0.0, 1.0]``.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float64)

    sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    edge_mag = np.sqrt(sx ** 2 + sy ** 2)

    local_var = cv2.GaussianBlur(gray ** 2, (7, 7), 0) - cv2.GaussianBlur(gray, (7, 7), 0) ** 2
    local_var = np.maximum(local_var, 0)
    local_std = np.sqrt(local_var)

    combined = edge_mag * 0.6 + local_std * 0.4

    clip_val = float(np.percentile(combined, clip_percentile))
    if clip_val < 1e-6:
        return np.zeros(gray.shape, dtype=np.float32)

    mask = np.clip(combined / clip_val, 0.0, 1.0)

    ksize = blur_ksize if blur_ksize % 2 == 1 else blur_ksize + 1
    mask = cv2.GaussianBlur(mask.astype(np.float32), (ksize, ksize), 0)

    mask = np.clip(mask, 0.0, 1.0)
    return mask.astype(np.float32)
