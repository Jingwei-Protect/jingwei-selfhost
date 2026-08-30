"""Displacement watermark sizing and blending."""

from __future__ import annotations

import numpy as np

from core.displacement_watermark import (
    _logo_shape_mask,
    _render_char_mask,
    _render_word_mask,
    apply_displacement_logo,
    apply_displacement_watermark,
)


def test_c024_font_ratio_is_not_clipped() -> None:
    rng = np.random.default_rng(5)
    img = rng.integers(40, 200, (200, 280, 3), dtype=np.uint8)
    out = apply_displacement_watermark(
        img, text="Jingwei", font_size_ratio=0.07, mode="band",
        shift_px=3, shadow_enabled=True, shadow_strength=0.1518, seed=1,
    )
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_font_ratio_scales_word_mask() -> None:
    small = _render_word_mask("Jingwei", max(12, int(round(800 * 0.08))))
    large = _render_word_mask("Jingwei", max(12, int(round(800 * 0.25))))
    assert large.shape[0] > small.shape[0]
    assert large.shape[1] > small.shape[1]


def test_font_ratio_changes_output_energy() -> None:
    rng = np.random.default_rng(0)
    img = rng.integers(40, 200, (800, 1024, 3), dtype=np.uint8)
    out_small = apply_displacement_watermark(
        img, text="Jingwei", font_size_ratio=0.08, mode="band", shift_px=6, seed=42,
    )
    out_large = apply_displacement_watermark(
        img, text="Jingwei", font_size_ratio=0.25, mode="band", shift_px=6, seed=42,
    )
    diff_small = int(np.abs(out_small.astype(np.int32) - img.astype(np.int32)).sum())
    diff_large = int(np.abs(out_large.astype(np.int32) - img.astype(np.int32)).sum())
    assert diff_large > diff_small * 1.5


def test_chinese_word_mask_renders() -> None:
    mask = _render_word_mask("小明", 48)
    assert mask.max() > 0.5
    assert mask.shape[0] >= 20
    assert mask.shape[1] >= 40


def test_chinese_scatter_char_masks_render() -> None:
    for ch in "画师":
        mask = _render_char_mask(ch, 48)
        assert mask.max() > 0.5, ch


def _block_logo(h: int = 32, w: int = 40) -> np.ndarray:
    logo = np.zeros((h, w, 4), dtype=np.uint8)
    logo[6:-6, 8:-8, :3] = 255
    logo[6:-6, 8:-8, 3] = 255
    return logo


def test_displacement_logo_shifts_host_pixels_not_paste() -> None:
    """Logo shape pushes the photo; it must not stamp white/gray ink."""
    rng = np.random.default_rng(3)
    img = rng.integers(30, 220, (160, 220, 3), dtype=np.uint8)
    out = apply_displacement_logo(
        img,
        _block_logo(),
        scale=0.28,
        position="center",
        shift_px=10,
        shadow_enabled=True,
        shadow_strength=0.35,
        seed=7,
    )
    assert out.shape == img.shape
    assert out.dtype == np.uint8
    assert not np.array_equal(out, img)
    cy, cx = 80, 110
    # A pasted white block would sit near 255; displacement stays in the host range.
    assert int(out[cy, cx].max()) < 250


def test_displacement_logo_anchor_overrides_corner() -> None:
    """Normalized anchors place the silhouette instead of the named corner."""
    rng = np.random.default_rng(6)
    img = rng.integers(40, 200, (160, 220, 3), dtype=np.uint8)
    kwargs = dict(scale=0.22, position="bottom_right", shift_px=8, seed=1)
    out_tl = apply_displacement_logo(img, _block_logo(), anchor_x=0.18, anchor_y=0.18, **kwargs)
    out_br = apply_displacement_logo(img, _block_logo(), anchor_x=0.85, anchor_y=0.85, **kwargs)
    assert not np.array_equal(out_tl[24, 28], img[24, 28])
    assert np.array_equal(out_br[24, 28], img[24, 28])
    assert not np.array_equal(out_br[-20, -24], img[-20, -24])


def test_displacement_logo_bottom_right_spares_top_left() -> None:
    rng = np.random.default_rng(4)
    img = rng.integers(40, 200, (160, 220, 3), dtype=np.uint8)
    out = apply_displacement_logo(
        img,
        _block_logo(),
        scale=0.22,
        position="bottom_right",
        shift_px=8,
        seed=1,
    )
    assert np.array_equal(out[2, 2], img[2, 2])
    assert not np.array_equal(out[-20, -24], img[-20, -24])


def test_opaque_light_background_logo_keeps_ink_not_full_plate() -> None:
    """A logo on white, with no alpha, should mask the mark — not the whole card."""
    logo = np.full((48, 56, 4), 255, dtype=np.uint8)
    logo[12:36, 16:40, :3] = (24, 28, 160)
    mask = _logo_shape_mask(logo)
    assert float(mask[3, 3]) < 0.2
    assert float(mask[24, 28]) > 0.5


def test_opaque_light_colour_on_white_is_kept() -> None:
    """Pale ink on a white card must not collapse to a full rectangle."""
    logo = np.full((48, 56, 4), 255, dtype=np.uint8)
    logo[12:36, 16:40, :3] = (160, 210, 255)
    mask = _logo_shape_mask(logo)
    assert float(mask[3, 3]) < 0.2
    assert float(mask[24, 28]) > 0.4


def test_photo_on_white_card_uses_full_plate() -> None:
    """A photograph with white margins is not a silhouette — use the whole card."""
    logo = np.full((48, 56, 4), 255, dtype=np.uint8)
    rng = np.random.default_rng(1)
    logo[4:44, 4:52, :3] = rng.integers(30, 230, size=(40, 48, 3), dtype=np.uint8)
    mask = _logo_shape_mask(logo)
    assert float(mask.mean()) > 0.9
