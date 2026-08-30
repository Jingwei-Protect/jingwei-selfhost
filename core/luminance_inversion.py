"""Luminance inversion — local brightness-flip attack for grayscale images.

On grayscale artwork, colour-based attacks (hue shift, saturation boost,
RGB offset) are ineffective because R=G=B.  This module exploits the
**luminance** channel instead:

1. Select random small patches (15-40px) across the image.
2. Within each patch, shift brightness towards the inverse direction:
   bright pixels get slightly darker, dark pixels get slightly lighter.
3. The shifts are small (10-20 levels on a 0-255 scale) so humans see
   only a faint "texture grain" — but AI VAE encoders encode these
   inverted gradients as structural features, producing blotchy/uneven
   results when they attempt to reconstruct the image.

Works on both colour and grayscale images but is primarily designed for
grayscale where other attacks fail.

Only numpy is required.
"""

from __future__ import annotations

import numpy as np


def _validate_inputs(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 32 or image.shape[1] < 32:
        raise ValueError(
            f"Image must be at least 32x32, got {image.shape[:2]}."
        )


def apply_luminance_inversion(
    image: np.ndarray,
    *,
    n_patches: int = 60,
    patch_size_range: tuple[int, int] = (15, 40),
    strength: int = 18,
    seed: int = 42,
) -> np.ndarray:
    """Apply local luminance inversion to random patches.

    Parameters
    ----------
    image:
        uint8 RGB, shape ``(H, W, 3)``.
    n_patches:
        Number of patches to invert.  More = more disruption.
    patch_size_range:
        (min_px, max_px) for patch side length.
    strength:
        Maximum brightness shift in grey levels.  Clamped to [5, 40].
    seed:
        RNG seed for deterministic output.

    Returns
    -------
    np.ndarray
        uint8 RGB, same shape as input.
    """
    _validate_inputs(image)
    rng = np.random.default_rng(seed)
    strength = int(np.clip(strength, 5, 40))
    h, w = image.shape[:2]
    ps_min, ps_max = patch_size_range
    ps_min = max(5, min(ps_min, min(h, w) // 2))
    ps_max = max(ps_min + 1, min(ps_max, min(h, w) // 2))

    out = image.astype(np.float32)

    gray = 0.299 * out[:, :, 0] + 0.587 * out[:, :, 1] + 0.114 * out[:, :, 2]
    midpoint = float(np.median(gray))

    for _ in range(n_patches):
        pw = int(rng.integers(ps_min, ps_max))
        ph = int(rng.integers(ps_min, ps_max))
        px = int(rng.integers(0, max(1, w - pw)))
        py = int(rng.integers(0, max(1, h - ph)))

        patch_gray = gray[py:py + ph, px:px + pw]
        direction = np.where(patch_gray > midpoint, -1.0, 1.0)

        shift_mag = float(rng.uniform(0.4, 1.0)) * strength
        shift = direction * shift_mag

        ys = np.linspace(0, 1, ph, dtype=np.float32)
        xs = np.linspace(0, 1, pw, dtype=np.float32)
        wy = np.sin(ys * np.pi) ** 2
        wx = np.sin(xs * np.pi) ** 2
        window = wy[:, np.newaxis] * wx[np.newaxis, :]

        weighted_shift = shift * window

        for c in range(3):
            out[py:py + ph, px:px + pw, c] += weighted_shift

    return np.clip(out, 0, 255).astype(np.uint8)
