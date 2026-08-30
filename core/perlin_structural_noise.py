"""Perlin Structural Noise — edge-aware low-frequency noise for stealth protection.

Why this is better than Gaussian white noise
---------------------------------------------
Gaussian noise occupies all frequencies uniformly, making it trivially
separable by any frequency-domain filter or AI denoiser.  It is also
destroyed by JPEG compression (which quantises high-frequency DCT
coefficients).

This module generates **multi-octave Perlin-like noise** that:

1. Has most energy in low/mid frequencies → survives JPEG compression
   at quality 70-85 (the typical range for social media platforms).
2. Is weighted by the image's edge map (Sobel magnitude) so noise is
   concentrated along edges and textures.  A denoiser cannot remove the
   noise without also degrading real edges — creating a Catch-22.
3. Has smooth spatial coherence — looks like natural luminance variation
   rather than digital artifact, so human eyes don't notice it.

Algorithm
---------
1. Generate multi-octave noise: sum 3 octaves of upsampled random grids
   at 1/16, 1/8, 1/4 of the image resolution.  Weights: 0.5, 0.3, 0.2
   (lower frequencies dominate).
2. Compute Sobel edge magnitude on the input image's luminance channel.
3. Build an edge weight mask: ``w = clip(edge / percentile_90, 0, 1)``.
   Apply a floor of 0.15 so even flat areas get a tiny amount of noise
   (preventing AI from using flat areas as clean reference).
4. Multiply noise by edge weight, scale by strength, add to image.

Only requires numpy, opencv-python.  No deep-learning dependencies.
"""

from __future__ import annotations

import cv2
import numpy as np


_OCTAVE_SCALES = (16, 8, 4)
_OCTAVE_WEIGHTS = (0.50, 0.30, 0.20)
_EDGE_FLOOR: float = 0.15
_EDGE_PERCENTILE: float = 90.0
_MAX_STRENGTH: float = 8.0


def _validate_inputs(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 32 or image.shape[1] < 32:
        raise ValueError(
            f"Image must be at least 32x32, got {image.shape[:2]}."
        )


def _generate_octave_noise(
    h: int,
    w: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate multi-octave Perlin-like noise, shape (H, W, 3), ~N(0, 1)."""
    accumulated = np.zeros((h, w, 3), dtype=np.float32)

    for scale, weight in zip(_OCTAVE_SCALES, _OCTAVE_WEIGHTS):
        lh = max(2, h // scale)
        lw = max(2, w // scale)
        low_res = rng.standard_normal((lh, lw, 3)).astype(np.float32)

        upsampled = np.empty((h, w, 3), dtype=np.float32)
        for c in range(3):
            up = cv2.resize(
                low_res[:, :, c],
                (w, h),
                interpolation=cv2.INTER_CUBIC,
            )
            std = float(up.std())
            if std > 1e-8:
                up = (up - up.mean()) / std
            upsampled[:, :, c] = up

        accumulated += upsampled * weight

    for c in range(3):
        std = float(accumulated[:, :, c].std())
        if std > 1e-8:
            accumulated[:, :, c] /= std

    return accumulated


def _compute_edge_weight(image: np.ndarray) -> np.ndarray:
    """Compute Sobel-based edge weight mask, shape (H, W), values [floor, 1]."""
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float64)
    sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.sqrt(sx ** 2 + sy ** 2)

    clip_val = float(np.percentile(mag, _EDGE_PERCENTILE))
    if clip_val < 1e-6:
        return np.full(gray.shape, _EDGE_FLOOR, dtype=np.float32)

    weight = np.clip(mag / clip_val, 0.0, 1.0)
    weight = cv2.GaussianBlur(weight.astype(np.float32), (9, 9), 0)
    weight = np.clip(weight * (1.0 - _EDGE_FLOOR) + _EDGE_FLOOR, _EDGE_FLOOR, 1.0)
    return weight.astype(np.float32)


def apply_perlin_structural_noise(
    image: np.ndarray,
    *,
    strength: float = 0.4,
    seed: int = 42,
) -> np.ndarray:
    """Apply edge-aware Perlin structural noise for stealth protection.

    Parameters
    ----------
    image : np.ndarray
        uint8 RGB, shape ``(H, W, 3)``.
    strength : float
        Noise intensity in [0.1, 1.0].  Scaled by ``_MAX_STRENGTH`` (8.0)
        to produce pixel-level perturbation.
        0.3 → peak ~2.4 grey levels on edges (very subtle).
        0.5 → peak ~4.0 grey levels on edges (moderate).
        1.0 → peak ~8.0 grey levels on edges.
    seed : int
        RNG seed for deterministic output.

    Returns
    -------
    np.ndarray
        uint8 RGB, same shape as input.
    """
    _validate_inputs(image)
    strength = float(np.clip(strength, 0.1, 1.0))

    h, w = image.shape[:2]
    rng = np.random.default_rng(seed)

    noise = _generate_octave_noise(h, w, rng)
    edge_weight = _compute_edge_weight(image)

    perturbation = noise * edge_weight[:, :, np.newaxis] * strength * _MAX_STRENGTH

    out = image.astype(np.float32) + perturbation
    return np.clip(out, 0, 255).astype(np.uint8)
