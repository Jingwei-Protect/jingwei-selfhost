"""Finding the outline a subject cuts against a flat background.

Every mark tried so far sat wholly inside one kind of content, and on flat
illustration that failed: anything faint enough to be worth looking at was
unfindable, and anything legible was lifted off cleanly, because a region of
flat colour carries no information an attacker has to reproduce.

The outline is the one place on such a picture where that is not true. Removing
a mark that straddles it means putting the boundary back exactly, and a flat
background is unusually bad at hiding a boundary that comes back slightly wrong
-- there is no texture to break up the seam. The property that makes flat art
easy to refill is the same one that makes an error in it obvious.

This module locates that outline and ranks the places along it where a mark of a
given size would sit half on each side. It also reports when a picture has no
flat background at all, which is the honest answer for a photograph or a densely
painted scene and tells the caller to place the mark some other way.
"""

from __future__ import annotations

import cv2
import numpy as np

from core.host_texture import gradient_magnitude

__all__ = [
    "estimate_background",
    "smooth_field",
    "subject_outline",
    "outline_placements",
]

# Below this share of the frame, whatever was found is a patch of similar colour
# rather than a background the subject sits on.
_MIN_BACKGROUND_FRACTION = 0.05


def estimate_background(
    image: np.ndarray,
    *,
    tolerance: float = 18.0,
    min_fraction: float = _MIN_BACKGROUND_FRACTION,
) -> np.ndarray:
    """Boolean mask of the flat field the subject sits on.

    The background is taken to be the colour occupying the frame's border, kept
    only where it forms a region reaching that border. Testing connectivity
    matters: a picture may repeat the background colour inside the subject, and
    those pockets are not somewhere an outline can be found.

    Returns an all-False mask when no such region covers ``min_fraction`` of the
    frame, which is how a picture without a flat background reports itself.
    """
    h, w = image.shape[:2]
    ring = max(2, int(round(min(h, w) * 0.02)))

    border = np.concatenate(
        [
            image[:ring].reshape(-1, 3),
            image[-ring:].reshape(-1, 3),
            image[:, :ring].reshape(-1, 3),
            image[:, -ring:].reshape(-1, 3),
        ]
    )
    reference = np.median(border, axis=0)

    distance = np.linalg.norm(image.astype(np.float64) - reference, axis=2)
    similar = (distance < tolerance).astype(np.uint8)

    count, labels = cv2.connectedComponents(similar, connectivity=4)
    touching = {
        int(label)
        for label in np.concatenate(
            [labels[0], labels[-1], labels[:, 0], labels[:, -1]]
        )
        if label != 0
    }
    if not touching:
        return np.zeros((h, w), dtype=bool)

    background = np.isin(labels, list(touching)) & similar.astype(bool)
    if background.mean() < min_fraction:
        return np.zeros((h, w), dtype=bool)
    return background


def smooth_field(
    image: np.ndarray,
    *,
    window: int = 15,
    max_texture: float = 18.0,
    min_region_fraction: float = 0.01,
    min_fraction: float = _MIN_BACKGROUND_FRACTION,
) -> np.ndarray:
    """Every region carrying too little detail to hide a badly rebuilt boundary.

    Wider than :func:`estimate_background` on purpose. On the cat picture the
    subject never touches the backdrop -- a smooth white pillow sits between the
    two -- so a test that only knows about the colour at the frame's border
    traces the pillow's outline and misses the one worth marking. What the
    argument needs is a neighbour smooth enough to show a seam, and the pillow
    qualifies exactly as much as the sky does.

    Only regions covering at least ``min_region_fraction`` of the frame are
    kept, and that filter is doing real work rather than tidying. The argument
    for marking a boundary is that a neighbour with no detail cannot disguise a
    seam, and a calm patch twenty pixels across disguises one perfectly well.
    Without the filter the calm gaps between brush strokes inside fur all
    qualify, and the outline stops describing a silhouette at all.
    """
    local = cv2.boxFilter(
        gradient_magnitude(image), -1, (window, window), normalize=True
    )
    smooth = cv2.morphologyEx(
        (local < max_texture).astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)
    )

    count, labels, stats, _ = cv2.connectedComponentsWithStats(smooth, connectivity=8)
    keep = [
        label
        for label in range(1, count)
        if stats[label, cv2.CC_STAT_AREA] >= min_region_fraction * smooth.size
    ]
    if not keep:
        return np.zeros(image.shape[:2], dtype=bool)
    smooth = np.isin(labels, keep)

    if smooth.mean() < min_fraction:
        return np.zeros(image.shape[:2], dtype=bool)
    return smooth


def subject_outline(background: np.ndarray, *, width: int = 3) -> np.ndarray:
    """Boolean mask of the boundary between background and everything else.

    ``width`` thickens the line so that placement scoring, which counts outline
    pixels falling inside a box, is not thrown off by how diagonally the
    boundary happens to run. It must be at least 3, since dilating and eroding
    by anything smaller leaves the mask unchanged and would return an empty
    boundary rather than a thin one.
    """
    if width < 3:
        raise ValueError(f"width must be at least 3, got {width}")
    if not background.any():
        return np.zeros(background.shape, dtype=bool)
    kernel = np.ones((width, width), np.uint8)
    solid = background.astype(np.uint8)
    return (cv2.dilate(solid, kernel) - cv2.erode(solid, kernel)).astype(bool)


def outline_placements(
    image: np.ndarray,
    mark_h: int,
    mark_w: int,
    *,
    top_k: int = 5,
    field: np.ndarray | None = None,
) -> list[dict[str, float | int]]:
    """Rank boxes that sit half on detailed content and half on a smooth field.

    A box is scored by how much outline runs through it, weighted by how evenly
    it is split between the two sides. Length alone would favour a box clipping
    a long stretch of boundary near its edge, which is a mark beside the outline
    rather than across it, and that has none of the property being sought.

    Each result also carries the texture on the subject side only. Amplitude has
    to be calibrated against that rather than against the box as a whole,
    because the background side contributes no detail and would drag any
    whole-box figure toward zero.

    Returns an empty list when the picture holds no smooth field. Results are
    spaced at least a mark apart so the list offers real alternatives rather
    than a cluster around one peak.
    """
    if field is None:
        field = smooth_field(image)
    if not field.any():
        return []

    h, w = image.shape[:2]
    outline = subject_outline(field).astype(np.float64)
    subject = (~field).astype(np.float64)

    box = (mark_w, mark_h)
    outline_count = cv2.boxFilter(outline, -1, box, normalize=False)
    subject_share = cv2.boxFilter(subject, -1, box, normalize=True)

    grad = gradient_magnitude(image)
    subject_grad_sum = cv2.boxFilter(grad * subject, -1, box, normalize=False)
    subject_pixels = cv2.boxFilter(subject, -1, box, normalize=False)

    # Peaks at an even split and falls to zero when the box lies wholly on one
    # side, which is exactly the placement this is meant to avoid.
    balance = 4.0 * subject_share * (1.0 - subject_share)
    score = outline_count * balance

    eligible = np.zeros(score.shape, dtype=bool)
    eligible[mark_h // 2 : h - (mark_h - mark_h // 2), mark_w // 2 : w - (mark_w - mark_w // 2)] = True
    score = np.where(eligible, score, -1.0)

    results: list[dict[str, float | int]] = []
    working = score.copy()
    for _ in range(top_k):
        cy, cx = np.unravel_index(int(np.argmax(working)), working.shape)
        if working[cy, cx] <= 0:
            break
        pixels = subject_pixels[cy, cx]
        results.append(
            {
                "x": int(cx - mark_w // 2),
                "y": int(cy - mark_h // 2),
                "outline_pixels": int(round(float(outline_count[cy, cx]))),
                "subject_share": round(float(subject_share[cy, cx]), 3),
                "subject_texture": round(
                    float(subject_grad_sum[cy, cx] / pixels) if pixels > 0 else 0.0, 2
                ),
                "score": round(float(score[cy, cx]), 1),
            }
        )
        y0, y1 = max(0, cy - mark_h), min(h, cy + mark_h)
        x0, x1 = max(0, cx - mark_w), min(w, cx + mark_w)
        working[y0:y1, x0:x1] = -1.0

    return results
