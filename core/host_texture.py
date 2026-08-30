"""How much texture a picture offers a mark, and how hard the mark may push there.

The second Doubao removal round measured seven marks across two pictures and
found their survival ordered perfectly by one quantity: the mark's luminance
amplitude divided by the texture already present where it sits. Rank correlation
against survival was -1.000 for that ratio against +0.964 for texture on its
own, and the ordering interleaved the two pictures rather than grouping them, so
it is the ratio doing the work and not one picture simply being easier.

That has a consequence for how a mark gets built. A single fixed strength
produced a ratio of 0.26 on dense floral texture and 0.62 on a flat
illustration, and those two sit on opposite sides of the point where Doubao
starts lifting the mark off cleanly. Strength cannot be a constant, and it
cannot be a slider the artist sets blind either, because the number that matters
is not visible in the slider. It has to be solved for against the host.

This module is the two halves of that: reading what a host offers, and searching
a renderer's strength knob until the mark lands on a chosen ratio.

The ratio is called conspicuity here. High means the mark reads as an overlay
sitting on top of the picture, which is both what makes it easy to see and what
makes it easy to lift. Low means it is bound into detail that was already there.
"""

from __future__ import annotations

from collections.abc import Callable

import cv2
import numpy as np

__all__ = [
    "gradient_magnitude",
    "texture_map",
    "best_host",
    "region_texture",
    "mark_amplitude",
    "conspicuity",
    "calibrate_strength",
]


def gradient_magnitude(image: np.ndarray) -> np.ndarray:
    """Per-pixel Sobel gradient magnitude of the luminance channel.

    Detail is measured on luminance alone because that is the channel the mark
    pushes on and the one the eye resolves finely; chroma edges of the same
    magnitude neither hide the mark as well nor read as sharply.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float64)
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    return np.hypot(gx, gy)


def texture_map(image: np.ndarray, box_h: int, box_w: int) -> np.ndarray:
    """Mean gradient magnitude over a mark-sized window centred at each pixel.

    Averaging over the mark's own footprint rather than a fixed small kernel
    matters: what masks a word is the detail across the whole word, so a thin
    high-contrast line crossing an otherwise empty area should not read as a
    good host.
    """
    return cv2.boxFilter(gradient_magnitude(image), -1, (box_w, box_h), normalize=True)


def region_texture(image: np.ndarray, region: np.ndarray) -> float:
    """Mean gradient magnitude of the pixels a boolean mask selects."""
    if not region.any():
        return 0.0
    return float(gradient_magnitude(image)[region].mean())


def best_host(
    image: np.ndarray,
    mark_h: int,
    mark_w: int,
    *,
    centrality: float | None = 0.30,
) -> tuple[int, int, float]:
    """Find the mark-sized box with the most detail to hide in.

    ``centrality`` is the standard deviation, as a fraction of each side, of a
    Gaussian that biases the search toward the middle of the frame. Detail alone
    is the wrong target on a picture with a busy background, where the densest
    texture is often foliage or pattern that an inpainter refills happily; the
    bias pulls the choice toward the subject, whose exact appearance is the part
    carrying the value. Pass ``None`` for the unweighted maximum.

    Returns the top-left corner and the *unweighted* texture there, since it is
    the true texture, not the biased score, that sets the amplitude budget.
    """
    h, w = image.shape[:2]
    if mark_h >= h or mark_w >= w:
        raise ValueError(f"mark {mark_w}x{mark_h} does not fit in {w}x{h}")

    local = texture_map(image, mark_h, mark_w)
    score = local.copy()

    if centrality is not None:
        ys, xs = np.mgrid[0:h, 0:w]
        score = score * np.exp(
            -(
                ((xs - w / 2.0) ** 2) / (2 * (w * centrality) ** 2)
                + ((ys - h / 2.0) ** 2) / (2 * (h * centrality) ** 2)
            )
        )

    # Only centres where the whole box stays inside the frame are eligible.
    eligible = np.zeros(score.shape, dtype=bool)
    eligible[mark_h // 2 : h - (mark_h - mark_h // 2), mark_w // 2 : w - (mark_w - mark_w // 2)] = True
    score = np.where(eligible, score, -np.inf)

    cy, cx = np.unravel_index(int(np.argmax(score)), score.shape)
    return int(cx - mark_w // 2), int(cy - mark_h // 2), float(local[cy, cx])


def mark_amplitude(clean: np.ndarray, marked: np.ndarray, region: np.ndarray) -> float:
    """Mean absolute luminance shift the mark causes inside a region."""
    if not region.any():
        return 0.0
    a = cv2.cvtColor(clean, cv2.COLOR_RGB2GRAY).astype(np.float64)
    b = cv2.cvtColor(marked, cv2.COLOR_RGB2GRAY).astype(np.float64)
    return float(np.abs(b - a)[region].mean())


def conspicuity(clean: np.ndarray, marked: np.ndarray, region: np.ndarray) -> float:
    """Mark amplitude relative to the detail already in its host region.

    Returns infinity on a perfectly flat host, which is the honest answer: there
    is no detail to hide in, so any mark at all reads as an overlay.
    """
    texture = region_texture(clean, region)
    amp = mark_amplitude(clean, marked, region)
    if texture <= 0.0:
        return float("inf") if amp > 0.0 else 0.0
    return amp / texture


def calibrate_strength(
    render: Callable[[float], np.ndarray],
    clean: np.ndarray,
    region: np.ndarray,
    target_amplitude: float,
    *,
    bounds: tuple[float, float] = (0.0, 1.0),
    iterations: int = 16,
) -> tuple[float, np.ndarray, float]:
    """Bisect a renderer's strength knob until the mark hits a target amplitude.

    Amplitude is monotone in strength for the displacement renderer, since the
    knob scales a shadow that only ever darkens, so bisection converges without
    needing the relationship to be linear -- which it is not, because the shadow
    is applied multiplicatively and clips.

    The floor of ``bounds`` is worth attention. At strength zero the mark is
    displacement only, and that still moves luminance wherever the host has
    detail. On a busy host the floor can therefore sit above the target, and no
    setting of this knob will reach it. The achieved amplitude is returned so the
    caller can notice; the fix in that case is a smaller shift, not a fainter
    shadow.

    Returns the chosen strength, the image it produced, and the amplitude
    reached.
    """
    lo, hi = bounds

    at_floor = render(lo)
    if mark_amplitude(clean, at_floor, region) >= target_amplitude:
        return lo, at_floor, mark_amplitude(clean, at_floor, region)

    best = render(hi)
    best_strength = hi
    for _ in range(iterations):
        mid = (lo + hi) / 2.0
        candidate = render(mid)
        amp = mark_amplitude(clean, candidate, region)
        best, best_strength = candidate, mid
        if amp < target_amplitude:
            lo = mid
        else:
            hi = mid

    return best_strength, best, mark_amplitude(clean, best, region)
