"""Face blob disruption — irregular high-saturation colour blobs on face ROI.

The strategy
------------
Modern AI watermark-removal pipelines run an OCR pass *and* a periodic-pattern
detector before inpainting.  Anything text-like or repeating gets segmented
into a clean removal mask, and the remaining inpaint context is usually
sufficient to restore the face accurately.

This module deliberately does the **opposite** of a watermark:

- Shapes are **irregular** (smooth-noise threshold blobs, not rectangles
  or text).
- Multiple **colours** at high saturation (magenta / cyan / yellow-green)
  collide on the face, so segmenting "the watermark colour" is undefined.
- Blob centres target **facial landmarks** (eyes / nose / mouth) so the
  AI is forced to inpaint exactly the pixels its face encoder needs most.
- Edges are **feathered**, removing the hard boundary that watermark
  removers use to estimate mask geometry.

A human viewer immediately sees that the image has been *deliberately
tampered with* — which is the social signal we want for a "preview only"
deliverable.  An AI editor that tries to "clean it up" will be forced into
inpaint, where the irregular masks + identity-critical pixels cause
substantial face drift.

This module is **content-agnostic**: it works on any input.  It does not
embed text, logos or signatures.  Traceable identity should be added by
``core.lsb_watermark`` and ``core.compliance_metadata``.

No deep-learning dependencies.  Uses OpenCV + numpy.
"""

from __future__ import annotations

import cv2
import numpy as np

from core.face_shield import _detect_faces

_BLOB_COUNT_MIN: int = 1
_BLOB_COUNT_MAX: int = 6
_BLOB_SIZE_MIN: float = 0.10
_BLOB_SIZE_MAX: float = 0.50
_HUE_SHIFT_MIN: int = 10
_HUE_SHIFT_MAX: int = 89   # OpenCV H ∈ [0, 179]
_SAT_BOOST_MIN: float = 0.8
_SAT_BOOST_MAX: float = 2.5
_ROUGHNESS_MIN: int = 4
_ROUGHNESS_MAX: int = 24
_FEATHER_MIN: int = 1
_FEATHER_MAX: int = 30


def _validate_inputs(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 16 or image.shape[1] < 16:
        raise ValueError(
            f"Image dimensions must be at least 16x16, got {image.shape[:2]}."
        )


def _make_irregular_blob_mask(
    h: int, w: int,
    cell_count: int,
    threshold: float,
    rng: np.random.RandomState,
) -> np.ndarray:
    """Generate an irregular binary blob mask via smooth-noise thresholding.

    Returns a float32 mask in ``[0.0, 1.0]`` of shape ``(h, w)``.  The blob
    appears wherever the smoothed noise exceeds *threshold*.  Lower
    ``cell_count`` (down to 4) gives larger, rougher blobs; higher values
    give more "speckled" patterns.
    """
    cells = np.clip(cell_count, 4, 64)
    low = rng.rand(cells, cells).astype(np.float32)
    smooth = cv2.resize(low, (w, h), interpolation=cv2.INTER_CUBIC)
    smooth = np.clip(smooth, 0.0, 1.0)
    return (smooth > threshold).astype(np.float32)


def _radial_falloff(h: int, w: int, cx: float, cy: float, radius: float) -> np.ndarray:
    """Smooth radial falloff centred at ``(cx, cy)``: 1 inside, 0 outside."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    # cosine ramp from full inside (≤ 0.7 R) to zero at R
    inner = radius * 0.7
    falloff = np.ones_like(dist, dtype=np.float32)
    in_ramp = (dist > inner) & (dist <= radius)
    falloff[in_ramp] = 0.5 * (
        1 + np.cos(np.pi * (dist[in_ramp] - inner) / max(1e-6, radius - inner))
    )
    falloff[dist > radius] = 0.0
    return falloff


def _apply_hue_saturation_shift(
    region_rgb: np.ndarray,
    mask: np.ndarray,
    hue_shift_deg: int,
    saturation_boost: float,
) -> np.ndarray:
    """Apply hue + saturation shift inside *mask* (float in [0,1]) on RGB region."""
    hsv = cv2.cvtColor(region_rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    h_orig = hsv[..., 0]
    s_orig = hsv[..., 1]

    # OpenCV H scale is 0..179; convert degree shift accordingly
    h_shift = (hue_shift_deg % 180)
    new_h = (h_orig + h_shift) % 180
    new_s = np.clip(s_orig * saturation_boost, 0, 255)

    blend = mask[..., None]
    hsv[..., 0] = h_orig * (1 - blend[..., 0]) + new_h * blend[..., 0]
    hsv[..., 1] = s_orig * (1 - blend[..., 0]) + new_s * blend[..., 0]

    hsv = np.clip(hsv, 0, 255).astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)


def apply_face_blob_disruption(
    image: np.ndarray,
    *,
    n_blobs: int = 3,
    blob_size_ratio: float = 0.28,
    hue_shift_range: tuple[int, int] = (40, 70),
    saturation_boost: float = 1.4,
    edge_roughness: int = 8,
    feather_px: int = 6,
    seed: int = 42,
) -> np.ndarray:
    """Stamp ``n_blobs`` irregular high-saturation colour blobs onto face ROIs.

    Parameters
    ----------
    image:
        uint8 RGB, shape ``(H, W, 3)``.
    n_blobs:
        Number of blobs per detected face.  Clamped to ``[1, 6]``.
    blob_size_ratio:
        Blob radius as a fraction of the face short side.  Clamped to
        ``[0.10, 0.50]``.  0.28 covers roughly one facial landmark.
    hue_shift_range:
        ``(min, max)`` hue rotation in degrees (each blob samples uniformly).
        Each value is clamped to ``[10, 89]``.
    saturation_boost:
        Multiplier applied to S channel inside each blob.  Clamped to
        ``[0.8, 2.5]``.  ≥ 1.3 makes the blob obviously "tampered".
    edge_roughness:
        Low-frequency cell count for the noise mask.  Smaller → rougher,
        bigger contiguous blobs; larger → more speckled.  Clamped to
        ``[4, 24]``.
    feather_px:
        Gaussian feathering width on blob edges.  Clamped to ``[1, 30]``.
    seed:
        Deterministic seed.

    Returns
    -------
    np.ndarray
        uint8 RGB, same shape as input.
    """
    _validate_inputs(image)
    n_blobs_c = int(np.clip(n_blobs, _BLOB_COUNT_MIN, _BLOB_COUNT_MAX))
    size_ratio = float(np.clip(blob_size_ratio, _BLOB_SIZE_MIN, _BLOB_SIZE_MAX))
    hue_lo = int(np.clip(min(hue_shift_range), _HUE_SHIFT_MIN, _HUE_SHIFT_MAX))
    hue_hi = int(np.clip(max(hue_shift_range), _HUE_SHIFT_MIN, _HUE_SHIFT_MAX))
    if hue_hi < hue_lo:
        hue_hi = hue_lo
    sat_boost = float(np.clip(saturation_boost, _SAT_BOOST_MIN, _SAT_BOOST_MAX))
    roughness = int(np.clip(edge_roughness, _ROUGHNESS_MIN, _ROUGHNESS_MAX))
    feather = int(np.clip(feather_px, _FEATHER_MIN, _FEATHER_MAX))

    rng = np.random.RandomState(seed)
    rects = _detect_faces(image)
    out = image.copy()

    for (rx, ry, rw, rh) in rects:
        if rw < 8 or rh < 8:
            continue
        short_side = min(rw, rh)
        radius = max(4.0, short_side * size_ratio * 0.5)

        for _ in range(n_blobs_c):
            # Random centre inside the face rect, biased away from very edges
            margin_x = max(1, int(rw * 0.10))
            margin_y = max(1, int(rh * 0.10))
            cx = int(rng.randint(rx + margin_x, rx + rw - margin_x))
            cy = int(rng.randint(ry + margin_y, ry + rh - margin_y))

            # Crop a local working window (square containing the blob)
            r_int = int(np.ceil(radius)) + feather + 4
            x0 = max(0, cx - r_int)
            y0 = max(0, cy - r_int)
            x1 = min(out.shape[1], cx + r_int)
            y1 = min(out.shape[0], cy + r_int)
            ww = x1 - x0
            hh = y1 - y0
            if ww < 4 or hh < 4:
                continue

            local_cx = cx - x0
            local_cy = cy - y0

            irregular = _make_irregular_blob_mask(
                hh, ww, roughness, threshold=0.55, rng=rng
            )
            radial = _radial_falloff(hh, ww, local_cx, local_cy, radius)
            mask = irregular * radial

            if feather > 0:
                k = feather * 2 + 1
                mask = cv2.GaussianBlur(mask, (k, k), sigmaX=feather, sigmaY=feather)
            mask = np.clip(mask, 0.0, 1.0)

            if float(mask.max()) < 0.05:
                continue

            hue_deg = int(rng.randint(hue_lo, hue_hi + 1))
            local_region = out[y0:y1, x0:x1]
            shifted = _apply_hue_saturation_shift(
                local_region, mask, hue_deg, sat_boost
            )
            out[y0:y1, x0:x1] = shifted

    return out
