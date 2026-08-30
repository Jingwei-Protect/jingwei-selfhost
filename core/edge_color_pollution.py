"""Edge-bound colour pollution — high-saturation bands welded to content edges.

Why this works when text watermarks do not
------------------------------------------
A text watermark is spatially independent of the image content: it floats on
top of the image as a regular, easy-to-mask pattern.  Modern inpainters
(including Yuanbao) easily separate it from the content and erase it.

Edge-bound colour pollution takes the opposite approach: the perturbation
exists **only where real subject edges are**.  High-saturation magenta / cyan /
yellow paint is applied in thick bands that follow every Sobel-detected edge,
offset by varying amounts.  The resulting "neon outline" effect is
**structurally inseparable** from the subject:

- If the inpainter removes the colour band, it must also destroy the real
  edge underneath, deforming the subject.
- If the inpainter preserves the edge, the colour pollution survives.
- Multi-colour overlapping bands make it impossible to notch-filter in HSV
  because the original pixel hue is buried under 3-4 independent colour
  layers at each edge location.

The palette is fixed to high-saturation colours that are maximally distant
from any natural image palette: magenta ``(255, 0, 180)``, cyan ``(0, 220, 255)``,
and warm yellow ``(255, 200, 0)``.  Opacity and band width are configurable.

Only numpy and scipy are required; no deep-learning dependencies.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import sobel, gaussian_filter

_POLLUTION_COLORS: list[tuple[int, int, int]] = [
    (255, 0, 180),    # magenta / hot pink
    (0, 220, 255),    # cyan
    (255, 200, 0),    # warm yellow
    (180, 0, 255),    # purple
]

_EDGE_PERCENTILE_DEFAULT = 75


def _validate_inputs(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 8 or image.shape[1] < 8:
        raise ValueError(
            f"Image dimensions must be at least 8x8, got {image.shape[:2]}."
        )


def _edge_magnitude(image: np.ndarray) -> np.ndarray:
    """Compute Sobel edge magnitude on the luminance channel."""
    gray = (
        0.299 * image[..., 0].astype(np.float32)
        + 0.587 * image[..., 1].astype(np.float32)
        + 0.114 * image[..., 2].astype(np.float32)
    )
    sx = sobel(gray, axis=1)
    sy = sobel(gray, axis=0)
    return np.sqrt(sx * sx + sy * sy)


def _shift_mask(
    mask: np.ndarray, dx: int, dy: int
) -> np.ndarray:
    """Shift a 2-D boolean mask by (dx, dy), zeroing the wrap."""
    h, w = mask.shape
    shifted = np.zeros_like(mask)
    src_y0 = max(0, -dy)
    src_y1 = min(h, h - dy)
    src_x0 = max(0, -dx)
    src_x1 = min(w, w - dx)
    dst_y0 = max(0, dy)
    dst_y1 = min(h, h + dy)
    dst_x0 = max(0, dx)
    dst_x1 = min(w, w + dx)
    rh = min(src_y1 - src_y0, dst_y1 - dst_y0)
    rw = min(src_x1 - src_x0, dst_x1 - dst_x0)
    if rh > 0 and rw > 0:
        shifted[dst_y0:dst_y0 + rh, dst_x0:dst_x0 + rw] = (
            mask[src_y0:src_y0 + rh, src_x0:src_x0 + rw]
        )
    return shifted


def apply_edge_color_pollution(
    image: np.ndarray,
    *,
    opacity: float = 0.55,
    band_width: int = 3,
    n_passes: int = 4,
    edge_percentile: float = _EDGE_PERCENTILE_DEFAULT,
    seed: int = 42,
) -> np.ndarray:
    """Paint high-saturation colour bands along detected content edges.

    Parameters
    ----------
    image:
        uint8 RGB, shape ``(H, W, 3)``.
    opacity:
        Global blend alpha for each colour pass, in ``[0.1, 0.8]``.
    band_width:
        Max pixel offset per pass.  Each pass shifts the edge mask by up to
        this many pixels in a random direction, creating a "thick band" along
        every edge.  Clamped to ``[1, 8]``.
    n_passes:
        Number of colour layers to stack.  Each uses the next colour in
        ``_POLLUTION_COLORS`` (wrapping).  Clamped to ``[1, 8]``.
    edge_percentile:
        Sobel magnitude percentile threshold.  Lower values include more
        (weaker) edges.  Clamped to ``[50, 95]``.
    seed:
        Controls random offset directions; deterministic outputs.

    Returns
    -------
    np.ndarray
        uint8 RGB, same shape as input.
    """
    _validate_inputs(image)
    opacity = float(np.clip(opacity, 0.1, 0.8))
    band_width = int(np.clip(band_width, 1, 8))
    n_passes = int(np.clip(n_passes, 1, 8))
    edge_percentile = float(np.clip(edge_percentile, 50.0, 95.0))

    rng = np.random.RandomState(seed)
    h, w = image.shape[:2]

    edge_mag = _edge_magnitude(image)
    threshold = np.percentile(edge_mag, edge_percentile)
    base_mask = edge_mag > threshold

    dilated = gaussian_filter(base_mask.astype(np.float32), sigma=0.5) > 0.3

    out = image.astype(np.float32)

    offsets_pool = [
        (1, 0), (-1, 0), (0, 1), (0, -1),
        (1, 1), (-1, -1), (1, -1), (-1, 1),
    ]

    for i in range(n_passes):
        color = _POLLUTION_COLORS[i % len(_POLLUTION_COLORS)]
        color_layer = np.full((h, w, 3), color, dtype=np.float32)

        # Each pass uses 2-3 sub-offsets to build a thick band
        n_sub = rng.randint(2, 4)
        pass_mask = np.zeros((h, w), dtype=np.float32)

        for _ in range(n_sub):
            dx, dy = offsets_pool[rng.randint(0, len(offsets_pool))]
            scale = rng.randint(1, band_width + 1)
            shifted = _shift_mask(dilated, dx * scale, dy * scale)
            pass_mask = np.maximum(pass_mask, shifted.astype(np.float32))

        alpha_map = opacity * pass_mask[..., None]
        out = out * (1.0 - alpha_map) + color_layer * alpha_map

    return np.clip(out, 0, 255).astype(np.uint8)
