"""署名·快速 displacement stamp — the Doubao dog c024 rung, auto-placed.

c024 is one faintly readable word on chest fur (7% of the subject short
side, shadow 0.1518). The live warp is 6 px — the ladder rung picked after
3 px restored too cleanly. Doubao often missed the 3 px chest stamp; 6 px
keeps the same font/shadow with a stronger geometric shift.

Extra conspicuity calibration and a luma fade made a weaker copy that
looked empty on the live padded puppy. Those steps are not applied.

Auto placement sits on a moderate-texture coat window. Maximising Sobel
parks the same faint word on petals, where it disappears.
"""

from __future__ import annotations

from typing import NamedTuple

import cv2
import numpy as np

from core.credit_mode import (
    CREDIT_DISP_FONT_RATIO,
    CREDIT_DISP_SHADOW_STRENGTH,
    CREDIT_DISP_SHIFT,
)
from core.displacement_watermark import (
    _FEATHER_SIGMA,
    _apply_mask_displacement,
    _random_shift,
    _render_word_mask,
)
from core.host_texture import (
    best_host,
    region_texture,
    texture_map,
)

CREDIT_CONSPICUITY = 0.24
# c024 chest-fur Sobel. Max-texture search prefers petals, where this depth vanishes.
CREDIT_HOST_TEXTURE = 40.0
CREDIT_HOST_TEX_MIN = 8.0
CREDIT_HOST_TEX_MAX = 70.0
CREDIT_HOST_LOG_SIGMA = 0.5
CREDIT_HOST_CENTRALITY = 0.35
CREDIT_MAX_MARK_WIDTH_RATIO = 0.85
_BORDER_DIST = 18.0
_SHIFT_PX = CREDIT_DISP_SHIFT


class CreditStampLayout(NamedTuple):
    font_size: int
    mask_h: int
    mask_w: int
    x: int
    y: int
    anchor_x: float
    anchor_y: float
    box_w: float
    box_h: float


def content_bbox(image: np.ndarray) -> tuple[int, int, int, int]:
    """Tight box of pixels that are not the border fill colour.

    Large paper / sky margins (the extra yellow above the puppy) drop out, so
    font size tracks the subject instead of the canvas.
    """
    if image.ndim != 3 or image.shape[2] < 3:
        h, w = image.shape[:2]
        return 0, 0, w, h
    h, w = image.shape[:2]
    rgb = image[:, :, :3].astype(np.float32)
    if h < 8 or w < 8:
        return 0, 0, w, h
    frame = np.concatenate(
        [
            rgb[0, :].reshape(-1, 3),
            rgb[-1, :].reshape(-1, 3),
            rgb[1:-1, 0],
            rgb[1:-1, -1],
        ],
        axis=0,
    )
    border = np.median(frame, axis=0)
    dist = np.linalg.norm(rgb - border, axis=2)
    mask = dist > _BORDER_DIST
    if float(mask.mean()) < 0.04:
        return 0, 0, w, h
    ys, xs = np.where(mask)
    pad = 2
    x0 = max(0, int(xs.min()) - pad)
    y0 = max(0, int(ys.min()) - pad)
    x1 = min(w, int(xs.max()) + 1 + pad)
    y1 = min(h, int(ys.max()) + 1 + pad)
    if (x1 - x0) < 32 or (y1 - y0) < 32:
        return 0, 0, w, h
    return x0, y0, x1, y1


_KMEANS_MAX_SIDE = 160
_KMEANS_K = 4


def subject_host_bbox(image: np.ndarray) -> tuple[int, int, int, int]:
    """Tight box of the largest interior colour mass (the body, not the bouquet).

    ``content_bbox`` still includes surrounding flowers, so its centre is often
    the bouquet. Cluster the subject colours and keep the biggest mass; that is
    the puppy's coat on the live upload, which is where c024 sat.
    """
    x0, y0, x1, y1 = content_bbox(image)
    crop = image[y0:y1, x0:x1, :3]
    ch, cw = crop.shape[:2]
    if ch < 32 or cw < 32:
        return x0, y0, x1, y1
    scale = min(1.0, _KMEANS_MAX_SIDE / float(max(ch, cw)))
    if scale < 0.999:
        sw, sh = max(16, int(round(cw * scale))), max(16, int(round(ch * scale)))
        small = cv2.resize(crop, (sw, sh), interpolation=cv2.INTER_AREA)
    else:
        small = crop
        sw, sh = cw, ch
    pixels = np.ascontiguousarray(small.reshape(-1, 3).astype(np.float32))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 12, 1.0)
    _compact, labels, centers = cv2.kmeans(
        pixels, _KMEANS_K, None, criteria, 4, cv2.KMEANS_PP_CENTERS,
    )
    labels = labels.reshape(sh, sw)
    border = np.median(
        np.concatenate(
            [
                image[0, :, :3],
                image[-1, :, :3],
                image[1:-1, 0, :3],
                image[1:-1, -1, :3],
            ],
            axis=0,
        ).astype(np.float32),
        axis=0,
    )
    drop = int(np.argmin(np.linalg.norm(centers - border, axis=1)))
    counts = [(i, int((labels == i).sum())) for i in range(_KMEANS_K) if i != drop]
    if not counts:
        return x0, y0, x1, y1
    best = max(counts, key=lambda item: item[1])[0]
    ys, xs = np.where(labels == best)
    if xs.size < 24:
        return x0, y0, x1, y1
    inv = 1.0 / scale
    pad = 4
    sx0 = x0 + max(0, int(xs.min() * inv) - pad)
    sy0 = y0 + max(0, int(ys.min() * inv) - pad)
    sx1 = x0 + min(cw, int((xs.max() + 1) * inv) + pad)
    sy1 = y0 + min(ch, int((ys.max() + 1) * inv) + pad)
    if (sx1 - sx0) < 32 or (sy1 - sy0) < 32:
        return x0, y0, x1, y1
    return sx0, sy0, sx1, sy1


def content_short_side(image: np.ndarray) -> int:
    """min(width, height) of ``content_bbox``."""
    x0, y0, x1, y1 = content_bbox(image)
    return max(32, min(x1 - x0, y1 - y0))


def _word_mask_for(image: np.ndarray, text: str) -> tuple[np.ndarray, int]:
    """Render the word; back the font off if it would overflow the subject."""
    name = (text or "").strip() or "Jingwei"
    short = content_short_side(image)
    x0, _y0, x1, _y1 = content_bbox(image)
    width_limit = max(32, int((x1 - x0) * CREDIT_MAX_MARK_WIDTH_RATIO))
    size = max(12, int(round(short * CREDIT_DISP_FONT_RATIO)))
    mask = _render_word_mask(name, size, rotation=0.0)
    if mask.shape[1] > width_limit:
        size = max(12, int(size * width_limit / mask.shape[1]))
        mask = _render_word_mask(name, size, rotation=0.0)
    return mask, size


def credit_font_size(image: np.ndarray, text: str) -> int:
    """Font px used for the credit stamp (7% of subject short side)."""
    _mask, size = _word_mask_for(image, text)
    return size


def _ink_center(mask: np.ndarray) -> tuple[float, float]:
    ys, xs = np.nonzero(mask > 0.3)
    if xs.size and ys.size:
        return (int(xs.min()) + int(xs.max())) / 2.0, (int(ys.min()) + int(ys.max())) / 2.0
    mh, mw = mask.shape
    return mw / 2.0, mh / 2.0


def _c024_host(image: np.ndarray, mark_h: int, mark_w: int) -> tuple[int, int, float]:
    """Mark-sized window whose texture matches c024 chest fur, not the bouquet.

    ``best_host`` maximises Sobel energy, so petals always win. A c024-depth
    stamp is readable on moderate-texture coat and disappears in that clutter.
    Score peaks near ``CREDIT_HOST_TEXTURE``, ignore flats and floral spikes.
    """
    h, w = image.shape[:2]
    if mark_h >= h or mark_w >= w:
        raise ValueError(f"mark {mark_w}x{mark_h} does not fit in {w}x{h}")
    local = texture_map(image, mark_h, mark_w)
    log_tex = np.log1p(local)
    score = np.exp(
        -((log_tex - np.log1p(CREDIT_HOST_TEXTURE)) ** 2)
        / (2.0 * CREDIT_HOST_LOG_SIGMA ** 2)
    )
    score = np.where(
        (local < CREDIT_HOST_TEX_MIN) | (local > CREDIT_HOST_TEX_MAX),
        0.0,
        score,
    )
    ys, xs = np.mgrid[0:h, 0:w]
    score = score * np.exp(
        -(
            ((xs - w / 2.0) ** 2) / (2 * (w * CREDIT_HOST_CENTRALITY) ** 2)
            + ((ys - h / 2.0) ** 2) / (2 * (h * CREDIT_HOST_CENTRALITY) ** 2)
        )
    )
    eligible = np.zeros(score.shape, dtype=bool)
    eligible[
        mark_h // 2 : h - (mark_h - mark_h // 2),
        mark_w // 2 : w - (mark_w - mark_w // 2),
    ] = True
    score = np.where(eligible, score, -np.inf)
    if not np.isfinite(score).any() or float(np.nanmax(score)) <= 0.0:
        return best_host(image, mark_h, mark_w, centrality=CREDIT_HOST_CENTRALITY)
    cy, cx = np.unravel_index(int(np.argmax(score)), score.shape)
    return int(cx - mark_w // 2), int(cy - mark_h // 2), float(local[cy, cx])


def _place_mask(
    image: np.ndarray,
    mask: np.ndarray,
    *,
    anchor_x: float | None,
    anchor_y: float | None,
) -> tuple[int, int]:
    """Top-left of the mask: explicit pin, or a c024-style coat window.

    Search prefers a moderate-texture coat window (c024), not the busiest
    petals, so the same faintness is actually readable.
    """
    h, w = image.shape[:2]
    mh, mw = mask.shape
    if mh >= h or mw >= w:
        return 0, 0
    if anchor_x is not None and anchor_y is not None:
        ink_cx, ink_cy = _ink_center(mask)
        px = int(round(float(np.clip(anchor_x, 0.0, 1.0)) * w - ink_cx))
        py = int(round(float(np.clip(anchor_y, 0.0, 1.0)) * h - ink_cy))
        px = max(0, min(px, max(0, w - mw)))
        py = max(0, min(py, max(0, h - mh)))
        return px, py
    x0, y0, x1, y1 = subject_host_bbox(image)
    crop = image[y0:y1, x0:x1]
    ch, cw = crop.shape[:2]
    if mh < ch and mw < cw:
        x, y, _host = _c024_host(crop, mh, mw)
        return x0 + x, y0 + y
    x0, y0, x1, y1 = content_bbox(image)
    crop = image[y0:y1, x0:x1]
    ch, cw = crop.shape[:2]
    if mh < ch and mw < cw:
        x, y, _host = _c024_host(crop, mh, mw)
        return x0 + x, y0 + y
    x, y, _host = _c024_host(image, mh, mw)
    return x, y


def _glyph_region(shape: tuple[int, int], mask: np.ndarray, x: int, y: int) -> np.ndarray:
    region = np.zeros(shape, dtype=np.uint8)
    mh, mw = mask.shape
    h, w = shape
    y1 = min(h, y + mh)
    x1 = min(w, x + mw)
    if y1 <= y or x1 <= x:
        return region.astype(bool)
    patch = (mask[: y1 - y, : x1 - x] > 0.1).astype(np.uint8)
    region[y:y1, x:x1] = patch
    grown = cv2.dilate(region, np.ones((2 * _SHIFT_PX + 3, 2 * _SHIFT_PX + 3), np.uint8))
    return grown.astype(bool)


def plan_credit_stamp(
    image: np.ndarray,
    text: str,
    *,
    anchor_x: float | None = None,
    anchor_y: float | None = None,
) -> CreditStampLayout:
    """Geometry of the credit stamp without rendering it."""
    h, w = image.shape[:2]
    mask, font_size = _word_mask_for(image, text)
    mh, mw = mask.shape
    x, y = _place_mask(image, mask, anchor_x=anchor_x, anchor_y=anchor_y)
    ink_cx, ink_cy = _ink_center(mask)
    cx = (x + ink_cx) / max(1, w)
    cy = (y + ink_cy) / max(1, h)
    return CreditStampLayout(
        font_size=font_size,
        mask_h=mh,
        mask_w=mw,
        x=x,
        y=y,
        anchor_x=float(cx),
        anchor_y=float(cy),
        box_w=float(mw) / max(1, w),
        box_h=float(mh) / max(1, h),
    )


def credit_stamp_hint(image: np.ndarray, text: str = "Jingwei") -> dict[str, float]:
    """Default pin + dashed-box size for the protect-page hint."""
    layout = plan_credit_stamp(image, text)
    return {
        "credit_disp_x": round(layout.anchor_x, 4),
        "credit_disp_y": round(layout.anchor_y, 4),
        "credit_disp_w": round(layout.box_w, 4),
        "credit_disp_h": round(layout.box_h, 4),
    }


def apply_credit_displacement(
    image: np.ndarray,
    text: str,
    *,
    anchor_x: float | None = None,
    anchor_y: float | None = None,
    seed: int = 42,
) -> np.ndarray:
    """Paint the locked stamp (7% / 6 px / 0.1518). ``anchor_*`` is the pin centre."""
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"image must be HxWx3 uint8, got {image.shape} {image.dtype}")
    name = (text or "").strip()
    if not name:
        return image.copy()

    mask, _font = _word_mask_for(image, name)
    x, y = _place_mask(image, mask, anchor_x=anchor_x, anchor_y=anchor_y)
    region = _glyph_region(image.shape[:2], mask, x, y)
    if region_texture(image, region) < 1.0:
        # Uniform fill (sky / paper): nothing to hide in; do not paint a grey overlay.
        return image.copy()
    rng = np.random.default_rng(seed)
    dx, dy = _random_shift(_SHIFT_PX, rng)
    return _apply_mask_displacement(
        image.copy(),
        mask,
        x,
        y,
        dx,
        dy,
        _FEATHER_SIGMA,
        shadow_enabled=True,
        shadow_strength=CREDIT_DISP_SHADOW_STRENGTH,
    )
