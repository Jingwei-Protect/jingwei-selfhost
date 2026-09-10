"""Credit displacement follows the c024 stamp: content-sized, host-calibrated, draggable."""

from __future__ import annotations

import numpy as np
import pytest

from core.credit_displacement import (
    CREDIT_CONSPICUITY,
    apply_credit_displacement,
    content_bbox,
    content_short_side,
    credit_font_size,
    credit_stamp_hint,
    plan_credit_stamp,
)
from core.displacement_watermark import apply_displacement_single_at
from core.host_texture import conspicuity, region_texture
from core.visible_edit import apply_visible_edits


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
