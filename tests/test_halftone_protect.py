"""Unit tests for product halftone protection layer mapping."""

from __future__ import annotations

import numpy as np
import pytest

from core.ascii_watermark import apply_ascii_watermark
from core.halftone_protect import (
    apply_halftone_protect,
    dot_preset_from_texture,
    normalize_halftone_style,
    resolve_halftone_anchor_from_placements,
    resolve_halftone_kwargs,
)


def _rgb(w: int = 128, h: int = 96) -> np.ndarray:
    rng = np.random.default_rng(7)
    return rng.integers(40, 220, size=(h, w, 3), dtype=np.uint8)


def test_normalize_halftone_style_legacy() -> None:
    assert normalize_halftone_style("author_dots") == ("halftone_dots", 0)
    assert normalize_halftone_style("fine_full") == ("halftone_dots", 100)


def test_dot_preset_from_texture() -> None:
    assert dot_preset_from_texture(0) == "author_dots"
    assert dot_preset_from_texture(49) == "author_dots"
    assert dot_preset_from_texture(50) == "fine_full"
    assert dot_preset_from_texture(100) == "fine_full"


def test_resolve_halftone_kwargs_ascii_chars_bounds() -> None:
    lo = resolve_halftone_kwargs(
        "ascii_chars",
        author_text="Jingwei",
        size=0,
        density=0,
        visibility=0,
        signature=0,
    )
    hi = resolve_halftone_kwargs(
        "ascii_chars",
        author_text="Jingwei",
        size=100,
        density=100,
        visibility=100,
        signature=100,
    )
    assert lo["render_font_size"] == 8
    assert hi["render_font_size"] == 56
    assert lo["author_sequence_rate"] == pytest.approx(0.10)
    assert hi["author_sequence_rate"] == pytest.approx(0.48)
    assert lo["author_mask_scale"] == pytest.approx(0.95)
    assert hi["author_mask_scale"] == pytest.approx(0.95)
    assert lo["cell_size"] == 8
    assert hi["cell_size"] == 28


def test_author_mask_font_size_uses_short_side_not_cell() -> None:
    from core.ascii_watermark import _author_mask_font_size

    big_cell = _author_mask_font_size(56, 0.95, tiled=False, img_w=1280, img_h=960)
    small_cell = _author_mask_font_size(14, 0.95, tiled=False, img_w=1280, img_h=960)
    assert big_cell == small_cell
    assert big_cell == max(12, int(min(1280, 960) * 0.085))


def test_deterministic_background_letter_spells_in_order() -> None:
    from core.ascii_watermark import _deterministic_background_letter

    letters = [
        _deterministic_background_letter(gx, 0, 20, "AB", stride=3, phase=0)
        for gx in range(12)
    ]
    picked = [c for c in letters if c is not None]
    assert picked[:4] == ["A", "B", "A", "B"]


def test_resolve_halftone_kwargs_ascii_chars_background_and_warp() -> None:
    """背景链与轮廓跟随为产品固定值，不随 API 参数关闭。"""
    kwargs = resolve_halftone_kwargs("ascii_chars", author_text="A")
    assert kwargs["author_background_sequence_rate"] == pytest.approx(0.373, abs=0.01)
    assert kwargs["author_background_chain_stride"] == 8
    assert kwargs["contour_warp_strength"] == pytest.approx(0.70)

    forced_off = resolve_halftone_kwargs(
        "ascii_chars", author_text="A", background_chain=0, contour_warp=0,
    )
    assert forced_off["author_background_chain_stride"] == 8
    assert forced_off["contour_warp_strength"] == pytest.approx(0.70)


def test_credit_faint_overrides_signature_and_chain() -> None:
    loud = resolve_halftone_kwargs(
        "ascii_chars", author_text="Jingwei", visibility=8, signature=0,
    )
    faint = resolve_halftone_kwargs(
        "ascii_chars", author_text="Jingwei", visibility=8, signature=0, credit_faint=True,
    )
    assert loud["author_mask_mode"] == "fine_dots"
    assert faint["author_mask_mode"] == "fine_dots"
    assert faint["mode"] == "luminance"
    assert faint["author_background_chain_stride"] == 8
    assert faint["contour_warp_strength"] == 0.0
    assert faint["local_contrast"] < loud["local_contrast"]
    assert faint["author_name_contrast"] < loud["author_name_contrast"]
    assert faint["opacity"] < loud["opacity"]
    assert faint["lum_mask"] == "none"
    assert faint["author_name_contrast"] == pytest.approx(0.10)
    assert faint["author_mask_opacity"] == pytest.approx(0.54)
    assert faint["charset"] == "Jingwei"
    assert all(ch not in str(faint["charset"]) for ch in ".,:;+-=~")


def test_credit_faint_colored_flat_uses_nb_name() -> None:
    wash = np.full((96, 128, 3), 160, dtype=np.uint8)
    faint = resolve_halftone_kwargs(
        "ascii_chars",
        author_text="SIGA",
        visibility=8,
        signature=0,
        credit_faint=True,
        image=wash,
    )
    assert faint["author_name_contrast"] == pytest.approx(0.18)
    assert faint["author_mask_opacity"] == pytest.approx(0.70)
    assert faint["charset"] == "SIGA"


def test_credit_faint_paper_uses_2b_name() -> None:
    paper = np.full((96, 128, 3), 252, dtype=np.uint8)
    faint = resolve_halftone_kwargs(
        "ascii_chars",
        author_text="Jingwei",
        visibility=8,
        signature=0,
        credit_faint=True,
        image=paper,
    )
    assert faint["author_name_contrast"] == pytest.approx(0.10)
    assert faint["charset"] == "Jingwei"


def test_credit_faint_keeps_quiet_center_signature() -> None:
    img = np.full((160, 220, 3), 210, dtype=np.uint8)
    loud = apply_halftone_protect(
        img, style="ascii_chars", author_text="Jingwei", visibility=8, signature=0,
    )
    faint = apply_halftone_protect(
        img,
        style="ascii_chars",
        author_text="Jingwei",
        visibility=8,
        signature=0,
        credit_faint=True,
    )
    loud_d = np.abs(loud.astype(np.int16) - img.astype(np.int16)).mean()
    faint_d = np.abs(faint.astype(np.int16) - img.astype(np.int16)).mean()
    assert faint_d < loud_d * 0.55
    h, w = img.shape[:2]
    cy0, cy1 = int(h * 0.35), int(h * 0.70)
    cx0, cx1 = int(w * 0.25), int(w * 0.75)
    center = np.abs(faint[cy0:cy1, cx0:cx1].astype(np.int16) - img[cy0:cy1, cx0:cx1].astype(np.int16)).mean()
    edge = np.abs(faint[: h // 8].astype(np.int16) - img[: h // 8].astype(np.int16)).mean()
    loud_center = np.abs(loud[cy0:cy1, cx0:cx1].astype(np.int16) - img[cy0:cy1, cx0:cx1].astype(np.int16)).mean()
    assert center > edge + 0.05
    assert center < loud_center * 0.7


def test_resolve_halftone_kwargs_signature_size_changes_scale() -> None:
    lo = resolve_halftone_kwargs("ascii_chars", author_text="A", signature_size=0)
    hi = resolve_halftone_kwargs("ascii_chars", author_text="A", signature_size=100)
    assert lo["author_mask_scale"] == pytest.approx(0.55)
    assert hi["author_mask_scale"] == pytest.approx(1.35)
    assert lo["author_dot_radius"] == 1
    assert hi["author_dot_radius"] == 3
    assert lo["author_name_contrast"] == hi["author_name_contrast"]


def test_resolve_halftone_kwargs_ascii_chars_custom_anchor() -> None:
    kwargs = resolve_halftone_kwargs(
        "ascii_chars",
        author_text="A",
        anchor_x=0.3,
        anchor_y=0.6,
    )
    assert kwargs["author_mask_position"] == "custom"
    assert kwargs["author_anchor_x"] == pytest.approx(0.3)
    assert kwargs["author_anchor_y"] == pytest.approx(0.6)


def test_credit_faint_keeps_custom_anchor() -> None:
    """淡印配方不得把用户落点写回 center_low。"""
    kwargs = resolve_halftone_kwargs(
        "ascii_chars",
        author_text="Jingwei",
        visibility=8,
        signature=0,
        credit_faint=True,
        anchor_x=0.18,
        anchor_y=0.82,
    )
    assert kwargs["author_mask_position"] == "custom"
    assert kwargs["author_anchor_x"] == pytest.approx(0.18)
    assert kwargs["author_anchor_y"] == pytest.approx(0.82)


def test_credit_faint_default_anchor_stays_center_low() -> None:
    kwargs = resolve_halftone_kwargs(
        "ascii_chars",
        author_text="Jingwei",
        visibility=8,
        signature=0,
        credit_faint=True,
    )
    assert kwargs["author_mask_position"] == "center_low"


def test_resolve_halftone_kwargs_ascii_chars_has_faint_tile() -> None:
    kwargs = resolve_halftone_kwargs("ascii_chars", author_text="Jingwei")
    assert kwargs["layout"] == "grid"
    assert kwargs["author_mask_mode"] == "fine_dots"
    assert kwargs["author_tile_contrast"] == pytest.approx(0.088)
    assert kwargs["author_tile_alpha_scale"] == pytest.approx(0.45)


def test_ascii_chars_no_readable_center_tile_at_custom_anchor() -> None:
    """全页底纹不应在中心重复可读完整署名。"""
    h, w = 480, 360
    img = np.full((h, w, 3), 180, dtype=np.uint8)
    cx, cy = w // 2, h // 2
    kwargs = resolve_halftone_kwargs(
        "ascii_chars",
        author_text="Jingwei",
        anchor_x=0.15,
        anchor_y=0.85,
        signature=80,
    )
    out = apply_ascii_watermark(img, **kwargs)
    corner = out[int(h * 0.78) : int(h * 0.92), int(w * 0.05) : int(w * 0.32)]
    center = out[cy - 40 : cy + 40, cx - 80 : cx + 80]
    corner_var = float(np.std(corner.astype(np.float32)))
    center_var = float(np.std(center.astype(np.float32)))
    assert corner_var > center_var * 0.85
    img = _rgb(160, 120)
    kwargs = resolve_halftone_kwargs("ascii_chars", author_text="Jingwei")
    with_tile = apply_ascii_watermark(img, **kwargs)
    without_tile = apply_ascii_watermark(
        img,
        **{**kwargs, "author_tile_contrast": 0.0, "author_tile_alpha_scale": 0.0},
    )
    diff = float(np.mean(np.abs(with_tile.astype(np.int16) - without_tile.astype(np.int16))))
    assert diff > 0.5


def test_resolve_halftone_anchor_from_placements_prefers_form_anchor() -> None:
    ax, ay = resolve_halftone_anchor_from_placements(
        [{"layer": "halftone_signature", "x": 0.12, "y": 0.88}],
        anchor_x=0.5,
        anchor_y=0.54,
    )
    assert ax == pytest.approx(0.5)
    assert ay == pytest.approx(0.54)


def test_resolve_halftone_anchor_from_placements_uses_box_when_form_missing() -> None:
    ax, ay = resolve_halftone_anchor_from_placements(
        [{"layer": "halftone_signature", "x": 0.12, "y": 0.88}],
        anchor_x=-1.0,
        anchor_y=-1.0,
    )
    assert ax == pytest.approx(0.12)
    assert ay == pytest.approx(0.88)


def test_resolve_halftone_anchor_from_placements_falls_back_to_form() -> None:
    ax, ay = resolve_halftone_anchor_from_placements([], anchor_x=0.3, anchor_y=0.7)
    assert ax == pytest.approx(0.3)
    assert ay == pytest.approx(0.7)


def test_halftone_custom_anchor_moves_signature_region_ascii() -> None:
    img = _rgb(160, 120)
    center = apply_halftone_protect(
        img, style="ascii_chars", author_text="JW", anchor_x=0.5, anchor_y=0.54,
    )
    corner = apply_halftone_protect(
        img, style="ascii_chars", author_text="JW", anchor_x=0.12, anchor_y=0.88,
    )
    h, w = img.shape[:2]
    cx, cy = w // 2, int(h * 0.54)
    bx, by = int(0.12 * w), int(0.88 * h)

    def region_diff(a: np.ndarray, b: np.ndarray, px: int, py: int, r: int = 40) -> float:
        y0, y1 = max(0, py - r), min(h, py + r)
        x0, x1 = max(0, px - r), min(w, px + r)
        return float(np.mean(np.abs(a[y0:y1, x0:x1].astype(np.int16) - b[y0:y1, x0:x1].astype(np.int16))))

    assert region_diff(corner, center, bx, by) > 2.0
    assert region_diff(center, corner, cx, cy) > 2.0


def test_credit_faint_custom_anchor_moves_signature() -> None:
    img = np.full((160, 220, 3), 210, dtype=np.uint8)
    center = apply_halftone_protect(
        img,
        style="ascii_chars",
        author_text="JW",
        visibility=8,
        signature=0,
        credit_faint=True,
        anchor_x=0.5,
        anchor_y=0.54,
    )
    corner = apply_halftone_protect(
        img,
        style="ascii_chars",
        author_text="JW",
        visibility=8,
        signature=0,
        credit_faint=True,
        anchor_x=0.18,
        anchor_y=0.82,
    )
    h, w = img.shape[:2]
    cx, cy = w // 2, int(h * 0.54)
    bx, by = int(0.18 * w), int(0.82 * h)

    def region_amp(marked: np.ndarray, px: int, py: int, r: int = 50) -> float:
        y0, y1 = max(0, py - r), min(h, py + r)
        x0, x1 = max(0, px - r), min(w, px + r)
        return float(np.mean(np.abs(
            marked[y0:y1, x0:x1].astype(np.int16) - img[y0:y1, x0:x1].astype(np.int16)
        )))

    assert float(np.mean(np.abs(center.astype(np.int16) - corner.astype(np.int16)))) > 0.02
    assert region_amp(corner, bx, by) > region_amp(center, bx, by)
    assert region_amp(center, cx, cy) > region_amp(corner, cx, cy)


def test_halftone_custom_anchor_moves_signature_region() -> None:
    img = _rgb(160, 120)
    center = apply_halftone_protect(
        img, style="halftone_dots", author_text="JW", anchor_x=0.5, anchor_y=0.54,
    )
    corner = apply_halftone_protect(
        img, style="halftone_dots", author_text="JW", anchor_x=0.12, anchor_y=0.88,
    )
    diff = float(np.mean(np.abs(center.astype(np.int16) - corner.astype(np.int16))))
    assert diff > 0.5


def test_resolve_halftone_kwargs_halftone_dots_local() -> None:
    kwargs = resolve_halftone_kwargs(
        "halftone_dots",
        author_text="A",
        dot_texture=0,
        size=0,
        density=100,
        signature=100,
    )
    assert kwargs["author_mask_mode"] == "fine_stealth"
    assert kwargs["halftone_size"] == pytest.approx(0.32)
    assert kwargs["author_name_contrast"] == pytest.approx(0.68)
    assert kwargs["author_mask_scale"] == pytest.approx(0.95)
    assert kwargs["author_dot_radius"] == 2


def test_resolve_halftone_kwargs_halftone_dots_full() -> None:
    kwargs = resolve_halftone_kwargs(
        "halftone_dots",
        author_text="A",
        dot_texture=100,
        density=100,
        signature=0,
    )
    assert kwargs["author_mask_mode"] == "fine_full"
    assert kwargs["author_fine_step"] == 8
    assert kwargs["fine_dot_name_boost"] == pytest.approx(0.10)
    assert kwargs["author_dot_radius"] == 2


def test_resolve_halftone_kwargs_halftone_dots_custom_anchor() -> None:
    kwargs = resolve_halftone_kwargs(
        "halftone_dots",
        author_text="A",
        anchor_x=0.2,
        anchor_y=0.7,
    )
    assert kwargs["author_mask_position"] == "custom"
    assert kwargs["author_anchor_x"] == pytest.approx(0.2)


def test_halftone_dots_density_changes_output() -> None:
    img = np.full((1280, 960, 3), 120, dtype=np.uint8)
    dense = apply_halftone_protect(
        img, style="halftone_dots", author_text="Jingwei", dot_texture=0, density=0,
    )
    sparse = apply_halftone_protect(
        img, style="halftone_dots", author_text="Jingwei", dot_texture=0, density=100,
    )
    diff = float(np.mean(np.abs(sparse.astype(np.int16) - dense.astype(np.int16))))
    assert diff > 0.15


def test_ascii_size_slider_changes_output() -> None:
    img = np.full((1280, 960, 3), 120, dtype=np.uint8)
    mid = apply_halftone_protect(
        img, style="ascii_chars", author_text="COCOMANGO", density=50, visibility=55, size=50,
    )
    hi = apply_halftone_protect(
        img, style="ascii_chars", author_text="COCOMANGO", density=50, visibility=55, size=100,
    )
    diff = float(np.mean(np.abs(mid.astype(np.int16) - hi.astype(np.int16))))
    assert diff > 3.5


def test_halftone_dots_size_slider_changes_output() -> None:
    img = np.full((1280, 960, 3), 120, dtype=np.uint8)
    kw = dict(
        style="halftone_dots", author_text="JW", dot_texture=0,
        density=50, visibility=55, anchor_x=0.12, anchor_y=0.88,
    )
    lo = apply_halftone_protect(img, **kw, size=0)
    hi = apply_halftone_protect(img, **kw, size=100)
    diff = float(np.mean(np.abs(lo.astype(np.int16) - hi.astype(np.int16))))
    assert int(np.abs(lo.astype(np.int16) - hi.astype(np.int16)).max()) >= 8
    assert diff > 0.45


def test_signature_visibility_only_changes_contrast() -> None:
    lo = resolve_halftone_kwargs("halftone_dots", author_text="A", signature=0)
    hi = resolve_halftone_kwargs("halftone_dots", author_text="A", signature=100)
    assert lo["author_name_contrast"] < hi["author_name_contrast"]
    assert lo["author_mask_scale"] == hi["author_mask_scale"]
    assert lo["author_dot_radius"] == hi["author_dot_radius"]


def test_halftone_dots_visibility_keeps_defense_floor() -> None:
    """Low 明度 must not collapse dot perturbation (non-signature grid still matters)."""
    lo = resolve_halftone_kwargs("halftone_dots", author_text="JW", visibility=0, signature=0)
    assert lo["local_contrast"] >= 0.26
    assert lo["halftone_screen_mix"] >= 0.15
    assert lo["dark_contrast_boost"] >= 0.74

    img = np.full((640, 480, 3), 140, dtype=np.uint8)
    out = apply_halftone_protect(
        img,
        style="halftone_dots",
        author_text="JW",
        dot_texture=0,
        visibility=0,
        signature=0,
        anchor_x=0.5,
        anchor_y=0.54,
    )
    # Exclude a small center crop (signature zone) — background dots must still move pixels.
    h, w = img.shape[:2]
    cy, cx = h // 2, w // 2
    pad_y, pad_x = h // 8, w // 8
    mask = np.ones((h, w), dtype=bool)
    mask[cy - pad_y:cy + pad_y, cx - pad_x:cx + pad_x] = False
    diff = float(np.mean(np.abs(out[mask].astype(np.int16) - img[mask].astype(np.int16))))
    assert diff >= 0.35


def test_signature_size_only_changes_scale() -> None:
    lo = resolve_halftone_kwargs("halftone_dots", author_text="A", signature_size=0)
    hi = resolve_halftone_kwargs("halftone_dots", author_text="A", signature_size=100)
    assert lo["author_mask_scale"] < hi["author_mask_scale"]
    assert lo["author_name_contrast"] == hi["author_name_contrast"]


def test_resolve_halftone_kwargs_requires_text() -> None:
    with pytest.raises(ValueError, match="halftone_text"):
        resolve_halftone_kwargs("ascii_chars", author_text="  ")


def test_apply_halftone_protect_smoke_styles() -> None:
    img = _rgb()
    for style, texture in (("ascii_chars", 0), ("halftone_dots", 0), ("halftone_dots", 100)):
        out = apply_halftone_protect(
            img,
            style=style,
            author_text="Jingwei",
            dot_texture=texture,
        )
        assert out.shape == img.shape
        assert out.dtype == np.uint8
        assert not np.array_equal(out, img)


def test_halftone_resolution_scale_matches_relative_appearance() -> None:
    """1280 预览与 2× 成图在相对字号一致（长边缩放 cell）。"""
    import cv2

    from core.halftone_protect import halftone_resolution_scale

    base = np.full((1280, 960, 3), 120, dtype=np.uint8)
    large = cv2.resize(base, (2560, 1920), interpolation=cv2.INTER_LINEAR)
    kw = dict(
        style="ascii_chars",
        author_text="COCOMANGO",
        size=50,
        density=50,
        visibility=35,
        signature=50,
        background_chain=50,
        contour_warp=50,
        anchor_x=0.12,
        anchor_y=0.88,
    )
    out_small = apply_halftone_protect(base, **kw)
    out_large = apply_halftone_protect(large, **kw)
    out_large_down = cv2.resize(out_large, (960, 1280), interpolation=cv2.INTER_AREA)
    diff = np.abs(out_small.astype(np.float32) - out_large_down.astype(np.float32)).mean()
    assert diff < 2.5
    assert halftone_resolution_scale(2560, 1920) == pytest.approx(2.0)


def test_halftone_large_image_matches_preview_render_side() -> None:
    """大图成图应与预览同参考分辨率渲染（含轮廓错位 + 背景链）。"""
    import cv2

    from core.halftone_protect import HALFTONE_REF_LONG_SIDE
    from core.pipeline import STEALTH_MAX_COMPUTE_DIM

    rng = np.random.default_rng(7)
    src = rng.integers(30, 220, (900, 600, 3), dtype=np.uint8)
    src[100:400, 80:320] = (40, 45, 55)
    src[200:350, 350:520] = (210, 215, 220)
    large = cv2.resize(src, (3840, 2880), interpolation=cv2.INTER_CUBIC)
    ref = STEALTH_MAX_COMPUTE_DIM
    lh, lw = large.shape[:2]
    sc = ref / float(max(lh, lw))
    pw = max(64, int(round(lw * sc)))
    ph = max(64, int(round(lh * sc)))
    preview = cv2.resize(large, (pw, ph), interpolation=cv2.INTER_AREA)
    kw = dict(
        style="ascii_chars",
        author_text="COCOMANGO",
        size=50,
        density=50,
        visibility=50,
        signature=50,
        signature_size=50,
        anchor_x=0.5,
        anchor_y=0.54,
        render_long_side=ref,
    )
    out_preview = apply_halftone_protect(preview, **kw)
    out_full = apply_halftone_protect(large, **kw)
    out_full_down = cv2.resize(out_full, (pw, ph), interpolation=cv2.INTER_AREA)
    diff = np.abs(out_preview.astype(np.float32) - out_full_down.astype(np.float32)).mean()
    assert diff < 4.0
    assert ref > HALFTONE_REF_LONG_SIDE


def test_halftone_dots_large_stealth_matches_preview() -> None:
    """大图 + stealth：波点预览与成图应对齐（ref 1280 + 整数倍 NEAREST 放大）。"""
    import cv2

    from core.halftone_protect import HALFTONE_REF_LONG_SIDE
    from core.pipeline import protect_image
    from core.visible_preview import render_visible_preview

    rng = np.random.default_rng(9)
    src = rng.integers(30, 220, (900, 600, 3), dtype=np.uint8)
    src[80:420, 60:280] = (35, 40, 48)
    src[180:360, 320:540] = (205, 210, 215)
    large = cv2.resize(src, (3840, 2880), interpolation=cv2.INTER_CUBIC)
    ht = dict(
        halftone_enabled=True,
        halftone_style="halftone_dots",
        halftone_text="COCOMANGO",
        halftone_size=50,
        halftone_density=50,
        halftone_visibility=50,
        halftone_signature=50,
        halftone_signature_size=50,
        halftone_dot_texture=0,
        halftone_anchor_x=0.5,
        halftone_anchor_y=0.54,
    )
    prev = render_visible_preview(
        large,
        mode="stealth",
        max_side=HALFTONE_REF_LONG_SIDE,
        face_emboss_enabled=False,
        **ht,
    )
    full = protect_image(
        large,
        level="standard",
        delivery_mode=True,
        protection_mode="stealth",
        stealth_surface=True,
        face_emboss_copies=0,
        blur_bar=False,
        emboss=False,
        displacement=False,
        **ht,
    )
    full_d = cv2.resize(full, (prev.shape[1], prev.shape[0]), interpolation=cv2.INTER_AREA)
    diff = np.abs(prev.astype(np.float32) - full_d.astype(np.float32)).mean()
    assert diff < 0.5


def test_halftone_dots_resolution_scale_matches_relative_appearance() -> None:
    import cv2

    base = np.full((1280, 960, 3), 120, dtype=np.uint8)
    large = cv2.resize(base, (2560, 1920), interpolation=cv2.INTER_LINEAR)
    kw = dict(
        style="halftone_dots",
        author_text="JW",
        size=50,
        density=50,
        visibility=35,
        signature=50,
        dot_texture=0,
        anchor_x=0.12,
        anchor_y=0.88,
    )
    out_small = apply_halftone_protect(base, **kw)
    out_large = apply_halftone_protect(large, **kw)
    out_large_down = cv2.resize(out_large, (960, 1280), interpolation=cv2.INTER_AREA)
    diff = np.abs(out_small.astype(np.float32) - out_large_down.astype(np.float32)).mean()
    assert diff < 2.5
