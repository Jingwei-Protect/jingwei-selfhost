"""Background estimation and outline-straddling placement."""

from __future__ import annotations

import numpy as np
import pytest

from core.silhouette import (
    estimate_background,
    outline_placements,
    smooth_field,
    subject_outline,
)


def _subject_on_flat(h: int = 300, w: int = 400) -> np.ndarray:
    """A textured blob sitting on a flat field, the shape this module expects."""
    img = np.full((h, w, 3), (120, 170, 220), dtype=np.uint8)
    rng = np.random.default_rng(0)
    img[100:220, 140:280] = rng.integers(0, 255, (120, 140, 3), dtype=np.uint8)
    return img


def test_flat_field_is_found_around_the_subject() -> None:
    background = estimate_background(_subject_on_flat())
    assert background[10, 10]
    assert not background[160, 200]
    assert 0.5 < background.mean() < 0.95


def test_picture_without_a_flat_field_reports_none() -> None:
    rng = np.random.default_rng(1)
    noise = rng.integers(0, 255, (300, 400, 3), dtype=np.uint8)
    assert not estimate_background(noise).any()


def test_background_colour_repeated_inside_the_subject_is_excluded() -> None:
    """A pocket of background colour enclosed by the subject is not background."""
    img = _subject_on_flat()
    img[150:180, 190:230] = (120, 170, 220)

    background = estimate_background(img)
    assert background[10, 10]
    assert not background[165, 210], "enclosed pocket should not count as background"


def test_smooth_field_covers_the_flat_area_but_not_the_subject() -> None:
    field = smooth_field(_subject_on_flat())
    assert field[10, 10]
    assert not field[160, 210]


def test_smooth_field_finds_a_calm_area_the_backdrop_test_would_miss() -> None:
    """A smooth band that never reaches the frame border still counts.

    This is the cat picture in miniature: the subject touches a smooth pillow
    rather than the backdrop, and only the wider test sees that boundary.
    """
    img = np.full((300, 400, 3), (120, 170, 220), dtype=np.uint8)
    rng = np.random.default_rng(4)
    img[60:260, 60:340] = (245, 245, 245)
    img[110:210, 150:270] = rng.integers(0, 255, (100, 120, 3), dtype=np.uint8)

    backdrop = estimate_background(img)
    field = smooth_field(img)

    assert not backdrop[80, 200], "the pale band is not the border colour"
    assert field[80, 200], "but it is smooth, so the wider test should take it"
    assert not field[160, 210]


def test_smooth_field_reports_nothing_on_texture_everywhere() -> None:
    rng = np.random.default_rng(5)
    assert not smooth_field(rng.integers(0, 255, (300, 400, 3), dtype=np.uint8)).any()


def test_calm_specks_inside_texture_are_not_a_field() -> None:
    """Gaps between brush strokes are calm but far too small to show a seam."""
    rng = np.random.default_rng(6)
    img = rng.integers(0, 255, (300, 400, 3), dtype=np.uint8)
    img[:80, :] = (120, 170, 220)
    for cy, cx in ((150, 100), (180, 260), (240, 180)):
        img[cy : cy + 12, cx : cx + 12] = (200, 200, 200)

    field = smooth_field(img)
    assert field[20, 200], "the wide calm band is a field"
    assert not field[155, 105], "a twelve pixel speck is not"


def test_outline_traces_the_boundary_only() -> None:
    background = estimate_background(_subject_on_flat())
    outline = subject_outline(background)

    assert outline.any()
    assert not outline[10, 10], "deep background is not on the boundary"
    assert not outline[160, 210], "deep inside the subject is not on the boundary"
    assert outline[100:104, 200].any(), "the subject's top edge should be traced"


def test_outline_of_nothing_is_empty() -> None:
    assert not subject_outline(np.zeros((50, 50), dtype=bool)).any()


def test_placements_straddle_the_boundary() -> None:
    placements = outline_placements(_subject_on_flat(), 20, 60)

    assert placements
    for p in placements:
        assert 0.15 < p["subject_share"] < 0.85, p


def test_placements_keep_the_box_inside_the_frame() -> None:
    for p in outline_placements(_subject_on_flat(), 20, 60):
        assert 0 <= p["x"] <= 400 - 60
        assert 0 <= p["y"] <= 300 - 20


def test_placements_are_spread_out_rather_than_clustered() -> None:
    placements = outline_placements(_subject_on_flat(), 20, 60, top_k=4)
    assert len(placements) >= 2
    for a, b in zip(placements, placements[1:]):
        assert abs(a["x"] - b["x"]) >= 60 or abs(a["y"] - b["y"]) >= 20


def test_placements_are_ranked_by_score() -> None:
    scores = [p["score"] for p in outline_placements(_subject_on_flat(), 20, 60)]
    assert scores == sorted(scores, reverse=True)


def test_subject_texture_ignores_the_flat_side() -> None:
    """Texture is reported for the subject alone, not diluted by the background."""
    placements = outline_placements(_subject_on_flat(), 20, 60)
    assert placements[0]["subject_texture"] > 30


def test_no_placements_without_a_flat_field() -> None:
    rng = np.random.default_rng(2)
    noise = rng.integers(0, 255, (300, 400, 3), dtype=np.uint8)
    assert outline_placements(noise, 20, 60) == []


def test_mark_larger_than_the_frame_yields_nothing() -> None:
    small = np.full((60, 60, 3), (120, 170, 220), dtype=np.uint8)
    rng = np.random.default_rng(3)
    small[20:45, 20:45] = rng.integers(0, 255, (25, 25, 3), dtype=np.uint8)
    assert outline_placements(small, 80, 80) == []


@pytest.mark.parametrize("width", [3, 5, 9])
def test_thicker_outline_covers_more(width: int) -> None:
    background = estimate_background(_subject_on_flat())
    assert subject_outline(background, width=width).sum() > 0


def test_outline_rejects_a_degenerate_width() -> None:
    """Morphology below 3 pixels is a no-op, so it must not pass silently."""
    background = estimate_background(_subject_on_flat())
    with pytest.raises(ValueError):
        subject_outline(background, width=1)
