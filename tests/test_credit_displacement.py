"""Credit displacement follows the c024 stamp: content-sized, host-calibrated."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from core.credit_displacement import (
    CREDIT_CONSPICUITY,
    apply_credit_displacement,
    content_bbox,
    content_short_side,
    credit_font_size,
    credit_stamp_hint,
    plan_credit_stamp,
    subject_host_bbox,
)
from core.displacement_watermark import apply_displacement_single_at
from core.host_texture import conspicuity, region_texture
from core.visible_edit import apply_visible_edits

_ROOT = Path(__file__).resolve().parents[1]
_SHOWCASE_DOG = _ROOT / "frontend" / "public" / "showcase" / "credit" / "credit-dog-before.png"
_DOG_CLEAN = _ROOT / "exports" / "adv-exp" / "ladder_test" / "dog" / "00_clean.png"
_DOG_C024 = _ROOT / "exports" / "adv-exp" / "ladder_test" / "dog" / "c024.png"


def _yellow_padded_subject(h: int = 200, w: int = 320, top_pad: int = 400) -> np.ndarray:
    """Busy subject under a large flat yellow margin — the dog-upload layout."""
    rng = np.random.default_rng(7)
    subject = rng.integers(20, 230, (h, w, 3), dtype=np.uint8)
    canvas = np.empty((h + top_pad, w, 3), dtype=np.uint8)
    canvas[:, :] = (255, 214, 32)
    canvas[top_pad:] = subject
    return canvas


def test_content_bbox_ignores_flat_yellow_margin() -> None:
    img = _yellow_padded_subject()
    x0, y0, x1, y1 = content_bbox(img)
    assert y0 >= 350
    assert (y1 - y0) <= 220
    assert content_short_side(img) < min(img.shape[:2])


def test_credit_font_follows_subject_not_canvas() -> None:
    img = _yellow_padded_subject()
    font = credit_font_size(img, "Jingwei")
    canvas_ratio = int(round(min(img.shape[:2]) * 0.07))
    subject_ratio = int(round(content_short_side(img) * 0.07))
    assert font == max(12, subject_ratio)
    assert font < canvas_ratio


def test_default_pin_lands_on_subject_not_canvas_center() -> None:
    img = _yellow_padded_subject()
    layout = plan_credit_stamp(img, "Jingwei")
    assert layout.anchor_y > 0.55
    assert abs(layout.anchor_y - 0.5) > 0.08


def _padded_floral_over_fur() -> np.ndarray:
    """Yellow margin + busy flowers at canvas centre + smoother fur below.

    Matches the live puppy upload: auto-search on the full frame prefers the
    floral band; c024-style search is confined to the subject and should sit
    on the body, not the flowers.
    """
    h, w = 600, 400
    canvas = np.empty((h, w, 3), dtype=np.uint8)
    canvas[:] = (255, 214, 32)
    rng = np.random.default_rng(3)
    flowers = np.empty((140, w, 3), dtype=np.uint8)
    flowers[:, :] = (30, 190, 210)
    flowers = np.clip(flowers.astype(np.int16) + rng.integers(-35, 35, flowers.shape), 0, 255).astype(np.uint8)
    fur = np.empty((220, w, 3), dtype=np.uint8)
    fur[:, :] = (196, 148, 78)
    fur = np.clip(fur.astype(np.int16) + rng.integers(-12, 12, fur.shape), 0, 255).astype(np.uint8)
    canvas[200:340] = flowers
    canvas[340:560] = fur
    return canvas


def test_default_pin_sits_on_body_not_canvas_centre_flowers() -> None:
    img = _padded_floral_over_fur()
    layout = plan_credit_stamp(img, "Jingwei")
    cy = layout.y + layout.mask_h / 2.0
    assert cy > 340
    assert layout.anchor_y > 0.55


def test_dragged_pin_is_honored() -> None:
    img = _yellow_padded_subject()
    layout = plan_credit_stamp(img, "Jingwei", anchor_x=0.35, anchor_y=0.82)
    assert layout.anchor_x == pytest.approx(0.35, abs=0.04)
    assert layout.anchor_y == pytest.approx(0.82, abs=0.04)


def test_credit_stamp_is_local_not_letter_grid() -> None:
    img = _yellow_padded_subject()
    out = apply_credit_displacement(img, "Jingwei")
    delta = np.abs(out.astype(np.int16) - img.astype(np.int16)).max(axis=2)
    changed = float((delta > 2).mean())
    assert changed > 0.0
    assert changed < 0.12


def test_credit_stamp_smaller_than_canvas_ratio_single_at() -> None:
    img = _yellow_padded_subject()
    credit = apply_credit_displacement(img, "Jingwei", anchor_x=0.5, anchor_y=0.82)
    loud = apply_displacement_single_at(
        img,
        text="Jingwei",
        shift_px=3,
        font_size_ratio=0.07,
        shadow_enabled=True,
        shadow_strength=0.35,
        anchor_x=0.5,
        anchor_y=0.82,
    )
    def frac(out: np.ndarray) -> float:
        delta = np.abs(out.astype(np.int16) - img.astype(np.int16)).max(axis=2)
        return float((delta > 2).mean())

    assert frac(credit) < frac(loud)


def test_flat_host_does_not_raise_shadow_above_target() -> None:
    """A pin on yellow must not become a dark overlay; conspicuity stays bounded."""
    img = _yellow_padded_subject()
    out = apply_credit_displacement(img, "Jingwei", anchor_x=0.5, anchor_y=0.12)
    layout = plan_credit_stamp(img, "Jingwei", anchor_x=0.5, anchor_y=0.12)
    region = np.zeros(img.shape[:2], dtype=bool)
    y1 = min(img.shape[0], layout.y + layout.mask_h)
    x1 = min(img.shape[1], layout.x + layout.mask_w)
    region[layout.y:y1, layout.x:x1] = True
    host = region_texture(img, region)
    if host < 1.0:
        ratio = conspicuity(img, out, region)
        assert np.isfinite(ratio)
        assert ratio <= CREDIT_CONSPICUITY * 3.0 or ratio == 0.0


def _changed_frac(original: np.ndarray, out: np.ndarray) -> float:
    delta = np.abs(out.astype(np.int16) - original.astype(np.int16)).max(axis=2)
    return float((delta > 2).mean())


def test_visible_edit_credit_ignores_drag_pin() -> None:
    """Credit Quick locks the stamp at best_host even if a leftover box is sent."""
    img = _yellow_padded_subject()
    opts = {
        "text": "Jingwei",
        "shift": 3,
        "font_ratio": 0.07,
        "seed": 1,
        "shadow": True,
        "shadow_strength": 0.15,
        "credit": True,
    }
    auto = apply_credit_displacement(img, "Jingwei", seed=1)
    dragged = apply_visible_edits(
        img, img.copy(), img.copy(),
        add_placements=[{"layer": "displacement", "x": 0.2, "y": 0.2}],
        displacement=opts,
    )
    other = apply_visible_edits(
        img, img.copy(), img.copy(),
        add_placements=[{"layer": "displacement", "x": 0.85, "y": 0.85}],
        displacement=opts,
    )
    assert np.array_equal(dragged, auto)
    assert np.array_equal(other, auto)


def test_visible_edit_credit_flag_ignores_loud_sliders() -> None:
    img = _yellow_padded_subject()
    place = [{"layer": "displacement", "x": 0.5, "y": 0.82}]
    loud_opts = {
        "text": "Jingwei",
        "shift": 10,
        "font_ratio": 0.15,
        "seed": 1,
        "shadow": True,
        "shadow_strength": 0.35,
    }
    loud = apply_visible_edits(
        img, img.copy(), img.copy(),
        add_placements=place, displacement=loud_opts,
    )
    credit = apply_visible_edits(
        img, img.copy(), img.copy(),
        add_placements=place, displacement={**loud_opts, "credit": True},
    )
    assert _changed_frac(img, credit) < _changed_frac(img, loud)


def test_credit_stamp_hint_pins_subject() -> None:
    hint = credit_stamp_hint(_yellow_padded_subject(), "Jingwei")
    assert hint["credit_disp_y"] > 0.55
    assert hint["credit_disp_w"] > 0.0
    assert hint["credit_disp_h"] > 0.0


def _gold_fur(h: int = 240, w: int = 320) -> np.ndarray:
    """Gold chest-fur host in the c024 range (not a floral bouquet)."""
    rng = np.random.default_rng(1)
    fur = np.empty((h, w, 3), dtype=np.uint8)
    fur[:] = (196, 148, 78)
    return np.clip(fur.astype(np.int16) + rng.integers(-18, 18, fur.shape), 0, 255).astype(np.uint8)


def _busy_flowers(h: int = 240, w: int = 320) -> np.ndarray:
    """High-chroma clutter — the live bouquet case, where 0.24 * host is loud."""
    rng = np.random.default_rng(2)
    return rng.integers(0, 255, (h, w, 3), dtype=np.uint8)


def _changed_luma(clean: np.ndarray, marked: np.ndarray, *, thresh: float = 2.0) -> float:
    """Mean luma of pixels the stamp actually moved — the c024 letter depth."""
    a = cv2.cvtColor(clean, cv2.COLOR_RGB2GRAY).astype(np.float64)
    b = cv2.cvtColor(marked, cv2.COLOR_RGB2GRAY).astype(np.float64)
    delta = np.abs(b - a)
    moved = delta >= thresh
    if not moved.any():
        return 0.0
    return float(delta[moved].mean())


def test_stamp_on_dog_clean_matches_saved_c024_depth() -> None:
    """Product must be the Doubao c024 stamp, not a further-faded copy.

    Saved c024 is faintly readable on the chest (~18 luma on letter pixels).
    The extra fade cap cut that to ~7, which is why the live frame looked empty.
    """
    if not _DOG_CLEAN.is_file() or not _DOG_C024.is_file():
        pytest.skip("c024 dog fixtures missing")
    clean = np.array(Image.open(_DOG_CLEAN).convert("RGB"))
    c024 = np.array(Image.open(_DOG_C024).convert("RGB"))
    out = apply_credit_displacement(clean, "Jingwei")
    got = _changed_luma(clean, out)
    ref = _changed_luma(clean, c024)
    assert ref > 12.0
    assert got >= ref * 0.70


def test_busy_host_stamp_does_not_pump_past_c024_knob() -> None:
    """Fixed 0.1518 shadow; do not bisect toward 0.24 × floral Sobel."""
    fur = _gold_fur()
    flowers = _busy_flowers()
    fur_out = apply_credit_displacement(fur, "Jingwei")
    flower_out = apply_credit_displacement(flowers, "Jingwei")
    assert _changed_luma(fur, fur_out) > 4.0
    assert _changed_luma(flowers, flower_out) > 4.0
    # Old conspicuity search hit ~30 luma on this noise; c024 letters are ~18.
    assert _changed_luma(flowers, flower_out) < 24.0


def test_long_word_on_flowers_is_still_a_local_stamp() -> None:
    flowers = _busy_flowers()
    out = apply_credit_displacement(flowers, "jwprotect")
    assert _changed_frac(flowers, out) < 0.12
    assert _changed_luma(flowers, out) < 24.0


def test_showcase_puppy_stamp_is_on_the_coat_not_the_bouquet() -> None:
    """Live padded puppy: max-texture search parks on flowers where c024-depth vanishes.

    c024 is readable because the letters sit on the coat. The same 深浅 on the
    cyan bouquet is invisible — that is the frame the user could not see.
    """
    if not _SHOWCASE_DOG.is_file():
        pytest.skip("showcase puppy missing")
    img = np.array(Image.open(_SHOWCASE_DOG).convert("RGB"))
    layout = plan_credit_stamp(img, "Jingwei")
    assert layout.anchor_y > 0.45
    assert 0.15 < layout.anchor_x < 0.52
    out = apply_credit_displacement(img, "Jingwei")
    assert _changed_luma(img, out) > 8.0
