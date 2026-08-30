"""Screenshot recovery preprocessor for JW / DWT watermark extractors.

Why
---
Screenshots break watermarks via two stacked transforms that the embed-time
algorithms do not assume:

  (a) **Re-scaling** — browser zoom + Windows DPI scaling resample the image
      to an unknown new resolution. DWT/DCT quantisation lattices drift off
      their original δ multiples.
  (b) **Crop offset** — the captured area rarely starts on a multiple-of-8
      boundary, which de-aligns the 8×8 DCT block grid that JW Layer-3 relies
      on.

What this module does
---------------------
For each candidate `(scale, offset)`:
  1. Resample the uploaded image (probably a screenshot) to that scale.
  2. Optionally shift the crop by `dy, dx` pixels.
  3. Run the regular extractor; keep the highest-confidence result that
     decodes a valid payload.

We probe a small, hand-tuned grid (≤ 9 scales × 1 offset by default) so the
recovery pass stays under ~15 seconds on a 1024×1024 image.

Scales chosen to cover the common cases:
  100% DPI screenshot of same-size image            → 1.00
  125% DPI screenshot (Windows default)             → 0.80
  150% DPI                                          → 0.67
  Browser fit-to-card (~85% / ~70% / ~55%)          → 0.85, 0.70, 0.55
  Upscaled screenshot (user zoomed in)              → 1.25, 1.43
  Big phone screenshot pasted as small thumbnail    → 1.82, 2.50
"""

from __future__ import annotations

from typing import Any, Callable

import cv2
import numpy as np

# Order matters: highest a-priori likelihood first, so we can early-exit.
_SCALES: tuple[float, ...] = (
    1.00,
    0.85, 1.17,
    0.70, 1.43,
    0.55, 1.82,
    0.40, 2.50,
)

# 8×8 DCT block-alignment shifts (only used for the deeper-recovery pass).
_OFFSETS: tuple[tuple[int, int], ...] = (
    (0, 0), (4, 4), (2, 2), (6, 6),
    (1, 1), (3, 3), (5, 5), (7, 7),
)

_MIN_SIDE = 128
_EARLY_EXIT_CONF = 0.85


def _resize(image: np.ndarray, scale: float) -> np.ndarray:
    if abs(scale - 1.0) < 1e-3:
        return image
    h, w = image.shape[:2]
    nh = max(_MIN_SIDE, int(round(h * scale)))
    nw = max(_MIN_SIDE, int(round(w * scale)))
    interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
    return cv2.resize(image, (nw, nh), interpolation=interp)


def _shift(image: np.ndarray, dy: int, dx: int) -> np.ndarray:
    if dy == 0 and dx == 0:
        return image
    h, w = image.shape[:2]
    if dy >= h or dx >= w:
        return image
    return image[dy:, dx:]


def _is_better(new_conf: float, new_found: bool,
               best_conf: float, best_found: bool) -> bool:
    """Prefer 'found' results; among equally-found, take higher confidence."""
    if new_found and not best_found:
        return True
    if best_found and not new_found:
        return False
    return new_conf > best_conf


def _try_grid(
    image: np.ndarray,
    extractor: Callable[[np.ndarray], dict],
    is_found: Callable[[dict], bool],
    get_conf: Callable[[dict], float],
    *,
    use_offsets: bool,
    max_attempts: int,
    initial_result: dict | None = None,
) -> tuple[dict, dict | None]:
    """Sweep scales (and optionally offsets); return (best_result, recovery_meta)."""
    best = initial_result if initial_result is not None else extractor(image)
    best_conf = get_conf(best)
    best_found = is_found(best)
    recovery_meta: dict | None = None

    if best_found and best_conf >= _EARLY_EXIT_CONF:
        return best, recovery_meta

    offsets = _OFFSETS if use_offsets else ((0, 0),)
    tried = 0
    for scale in _SCALES:
        for dy, dx in offsets:
            if tried >= max_attempts:
                break
            if abs(scale - 1.0) < 1e-3 and (dy, dx) == (0, 0):
                continue  # already tried as the base extract
            tried += 1
            try:
                candidate = _shift(_resize(image, scale), dy, dx)
                if min(candidate.shape[:2]) < _MIN_SIDE:
                    continue
                r = extractor(candidate)
            except Exception:
                continue
            r_conf = get_conf(r)
            r_found = is_found(r)
            if _is_better(r_conf, r_found, best_conf, best_found):
                best = r
                best_conf = r_conf
                best_found = r_found
                recovery_meta = {
                    "scale": round(scale, 3),
                    "offset": [dy, dx] if (dy or dx) else None,
                    "attempts_used": tried,
                }
                if best_found and best_conf >= _EARLY_EXIT_CONF:
                    return best, recovery_meta
        if best_found and best_conf >= _EARLY_EXIT_CONF:
            break

    return best, recovery_meta


def extract_jw_with_recovery(
    image: np.ndarray,
    *,
    max_attempts: int = 24,
    initial_result: dict | None = None,
) -> dict:
    """Extract JW protocol payload with screenshot-resilient scale+offset sweep.

    Returns the standard ``extract_jw_watermark`` dict with two extra keys
    when recovery succeeded:
      - ``recovered``: True
      - ``recovery``: ``{"scale": ..., "offset": ..., "attempts_used": ...}``

    Pass ``initial_result`` when the caller already ran ``extract_jw_watermark``
    on ``image`` to avoid a duplicate full extract.
    """
    from core.jingwei_protocol import extract_jw_watermark

    best, meta = _try_grid(
        image,
        extractor=extract_jw_watermark,
        is_found=lambda r: bool(r.get("found")),
        get_conf=lambda r: float(r.get("confidence", 0.0)),
        use_offsets=True,
        max_attempts=max_attempts,
        initial_result=initial_result,
    )
    out: dict[str, Any] = dict(best)
    out["recovered"] = bool(meta and best.get("found"))
    if out["recovered"]:
        out["recovery"] = meta
    return out


def extract_dwt_with_recovery(
    image: np.ndarray,
    *,
    max_attempts: int = 9,
    initial_result: dict | None = None,
) -> dict:
    """Extract DWT payload with screenshot-resilient scale sweep.

    Same return shape as ``extract_dwt_watermark``, with optional
    ``recovered`` / ``recovery`` keys when a non-native scale won.
    """
    from core.dwt_watermark import extract_dwt_watermark

    def _found(r: dict) -> bool:
        return bool(r.get("payload_text")) and float(r.get("confidence", 0.0)) >= 0.60

    best, meta = _try_grid(
        image,
        extractor=extract_dwt_watermark,
        is_found=_found,
        get_conf=lambda r: float(r.get("confidence", 0.0)),
        use_offsets=False,
        max_attempts=max_attempts,
        initial_result=initial_result,
    )
    out: dict[str, Any] = dict(best)
    out["recovered"] = bool(meta and _found(best))
    if out["recovered"]:
        out["recovery"] = meta
    return out
