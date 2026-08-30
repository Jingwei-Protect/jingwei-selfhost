"""Edge corruption — false-edge injection to confuse AI subject segmentation.

AI img2img pipelines rely on edge detection to identify subject boundaries.
By adding "ghost edges" — faint parallel copies of real edges offset by 1-3
pixels with a slight hue shift — we corrupt the edge map that the model uses
for subject localisation:

- If the model preserves ALL edges (real + ghost), the output has visible
  colour-shifted artifacts along every boundary.
- If the model tries to denoise/remove the extra edges, it risks destroying
  actual subject boundaries, producing deformation.

The Sobel operator (via scipy.ndimage) detects edges in the luminance channel.
Ghost edges are drawn in the original pixel colour but with the hue rotated
by approximately ±15 degrees (HSV space), creating a subtle chromatic fringe
that is hard to filter without affecting real edges.

Only numpy and scipy are required; no deep-learning dependencies.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import sobel


def _validate_inputs(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 8 or image.shape[1] < 8:
        raise ValueError(
            f"Image dimensions must be at least 8x8, got {image.shape[:2]}."
        )


def _rgb_to_hsv(rgb: np.ndarray) -> np.ndarray:
    """Convert uint8 RGB to float32 HSV (H in [0,360), S/V in [0,1])."""
    f = rgb.astype(np.float32) / 255.0
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin

    h = np.zeros_like(delta)
    mask_r = (cmax == r) & (delta > 0)
    mask_g = (cmax == g) & (delta > 0)
    mask_b = (cmax == b) & (delta > 0)
    h[mask_r] = 60.0 * (((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6.0)
    h[mask_g] = 60.0 * ((b[mask_g] - r[mask_g]) / delta[mask_g] + 2.0)
    h[mask_b] = 60.0 * ((r[mask_b] - g[mask_b]) / delta[mask_b] + 4.0)

    s = np.where(cmax > 0, delta / cmax, 0.0)
    return np.stack([h, s, cmax], axis=-1).astype(np.float32)


def _hsv_to_rgb(hsv: np.ndarray) -> np.ndarray:
    """Convert float32 HSV to uint8 RGB."""
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    h = h % 360.0
    c = v * s
    x = c * (1.0 - np.abs((h / 60.0) % 2.0 - 1.0))
    m = v - c

    hi = (h / 60.0).astype(np.int32) % 6
    r = np.zeros_like(h)
    g = np.zeros_like(h)
    b = np.zeros_like(h)

    for idx, (rv, gv, bv) in enumerate([
        (c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x),
    ]):
        mask = hi == idx
        r[mask] = (rv if isinstance(rv, (int, float)) else rv[mask])
        g[mask] = (gv if isinstance(gv, (int, float)) else gv[mask])
        b[mask] = (bv if isinstance(bv, (int, float)) else bv[mask])

    rgb = np.stack([r + m, g + m, b + m], axis=-1)
    return np.clip(rgb * 255.0, 0, 255).astype(np.uint8)


def apply_edge_corruption(
    image: np.ndarray,
    *,
    intensity: float = 0.4,
    grayscale_mode: bool = False,
    luma_shift: int = 25,
    seed: int = 42,
) -> np.ndarray:
    """Add ghost edges parallel to real edges.

    For colour images (default): ghost edges are hue-shifted ±15°.
    For grayscale images (``grayscale_mode=True``): ghost edges are
    brightness-shifted by ``±luma_shift`` levels, creating visible
    "double line" artifacts that AI cannot separate from real edges.

    Parameters
    ----------
    image : np.ndarray
        RGB uint8, shape ``(H, W, 3)``.
    intensity : float
        Blend alpha for ghost edges in ``[0.0, 1.0]``.
    grayscale_mode : bool
        If True, use luminance shift instead of hue shift.
    luma_shift : int
        Brightness offset for grayscale ghost edges (default 25).
    seed : int
        Controls random offset direction for ghost edges.

    Returns
    -------
    np.ndarray
        RGB uint8, same shape as input.
    """
    _validate_inputs(image)
    intensity = float(np.clip(intensity, 0.0, 1.0))
    if intensity <= 0.0:
        return image.copy()

    rng = np.random.RandomState(seed)
    h, w = image.shape[:2]

    gray = (
        0.299 * image[..., 0].astype(np.float32)
        + 0.587 * image[..., 1].astype(np.float32)
        + 0.114 * image[..., 2].astype(np.float32)
    )
    sx = sobel(gray, axis=1)
    sy = sobel(gray, axis=0)
    edge_mag = np.sqrt(sx * sx + sy * sy)

    threshold = np.percentile(edge_mag, 85)
    edge_mask = edge_mag > threshold

    if not grayscale_mode:
        hsv = _rgb_to_hsv(image)

    out = image.astype(np.float32)

    offsets = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)]
    n_ghosts = rng.randint(2, 4)

    for gi in range(n_ghosts):
        dx, dy = offsets[rng.randint(0, len(offsets))]
        scale = rng.randint(1, 4)
        dx *= scale
        dy *= scale

        if grayscale_mode:
            sign = rng.choice([-1, 1])
            ghost_rgb = np.clip(
                image.astype(np.float32) + sign * luma_shift, 0, 255
            )
        else:
            hue_shift = rng.choice([-15.0, 15.0])
            shifted_hsv = hsv.copy()
            shifted_hsv[..., 0] = (shifted_hsv[..., 0] + hue_shift) % 360.0
            ghost_rgb = _hsv_to_rgb(shifted_hsv).astype(np.float32)

        shifted_mask = np.zeros((h, w), dtype=bool)
        src_y0 = max(0, -dy)
        src_y1 = min(h, h - dy)
        src_x0 = max(0, -dx)
        src_x1 = min(w, w - dx)
        dst_y0 = max(0, dy)
        dst_y1 = min(h, h + dy)
        dst_x0 = max(0, dx)
        dst_x1 = min(w, w + dx)

        region_h = min(src_y1 - src_y0, dst_y1 - dst_y0)
        region_w = min(src_x1 - src_x0, dst_x1 - dst_x0)
        if region_h <= 0 or region_w <= 0:
            continue

        shifted_mask[dst_y0:dst_y0 + region_h, dst_x0:dst_x0 + region_w] = (
            edge_mask[src_y0:src_y0 + region_h, src_x0:src_x0 + region_w]
        )

        alpha = intensity * shifted_mask[..., None].astype(np.float32)
        ghost_src = np.zeros_like(out)
        ghost_src[dst_y0:dst_y0 + region_h, dst_x0:dst_x0 + region_w] = (
            ghost_rgb[src_y0:src_y0 + region_h, src_x0:src_x0 + region_w]
        )

        out = out * (1.0 - alpha) + ghost_src * alpha

    return np.clip(out, 0, 255).astype(np.uint8)
