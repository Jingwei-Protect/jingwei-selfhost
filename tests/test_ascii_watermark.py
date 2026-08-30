"""Unit tests for core.ascii_watermark."""

from __future__ import annotations

import numpy as np
import pytest

from core.ascii_watermark import (
    apply_ascii_watermark,
    build_author_charset,
    build_author_letters,
    build_halftone_ramp_charset,
    _bayer_adjust_lum,
    _build_author_dot_mask,
    _try_pick_author_char,
)


def _solid(h: int, w: int, rgb: tuple[int, int, int]) -> np.ndarray:
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = rgb
    return img


def test_output_shape_and_dtype() -> None:
    img = _solid(128, 128, (100, 120, 140))
    out = apply_ascii_watermark(
        img, cell_size=10, opacity=0.8, color_mode="fixed", color=(40, 40, 40),
    )
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_opacity_zero_returns_copy() -> None:
    img = _solid(64, 64, (50, 50, 50))
    out = apply_ascii_watermark(img, opacity=0.0)
    np.testing.assert_array_equal(out, img)
    assert out is not img


def test_luminance_mode_changes_pixels() -> None:
    img = _solid(96, 96, (128, 128, 128))
    out = apply_ascii_watermark(
        img, opacity=0.8, mode="luminance", color_mode="fixed", color=(0, 0, 0),
        cell_size=10,
    )
    assert not np.array_equal(out, img)


def test_author_charset_includes_symbols_and_name() -> None:
    cs = build_author_charset("cccola")
    assert "?" in cs or "+" in cs
    assert "c" in cs
    assert len(cs) >= 10


def test_author_luminance_reference_style() -> None:
    img = _solid(120, 120, (180, 200, 220))
    out = apply_ascii_watermark(
        img,
        opacity=0.85,
        mode="author_luminance",
        author_text="cccola",
        cell_size=11,
        stroke_width=0,
        local_contrast=0.34,
    )
    assert np.any(out != img)


def test_repeat_text_inserts_spaces_for_author() -> None:
    img = _solid(96, 96, (200, 200, 200))
    out = apply_ascii_watermark(
        img,
        opacity=0.8,
        mode="repeat_text",
        author_text="ab",
        cell_size=12,
        color_mode="fixed",
        color=(30, 30, 30),
    )
    assert out.shape == img.shape


def test_build_author_charset_non_empty() -> None:
    assert len(build_author_charset("  ")) >= 10
    assert "c" in build_author_charset("cccola")


def test_bg_filter_skips_extremes() -> None:
    white = _solid(64, 64, (255, 255, 255))
    out_no = apply_ascii_watermark(
        white, opacity=0.8, bg_filter=0.0, color_mode="fixed", color=(0, 0, 0), cell_size=10,
    )
    out_yes = apply_ascii_watermark(
        white, opacity=0.8, bg_filter=0.2, color_mode="fixed", color=(0, 0, 0), cell_size=10,
    )
    diff_no = np.abs(out_no.astype(int) - white.astype(int)).sum()
    diff_yes = np.abs(out_yes.astype(int) - white.astype(int)).sum()
    assert diff_yes < diff_no


def test_local_color_follows_image_regions() -> None:
    img = np.zeros((80, 160, 3), dtype=np.uint8)
    img[:, :80] = (200, 60, 60)
    img[:, 80:] = (60, 60, 200)
    out = apply_ascii_watermark(
        img,
        opacity=0.92,
        color_mode="local",
        local_contrast=0.0,
        stroke_width=0,
        cell_size=18,
        mode="luminance",
    )
    left = out[20:60, 20:60].astype(np.float32).mean(axis=(0, 1))
    right = out[20:60, 100:140].astype(np.float32).mean(axis=(0, 1))
    assert left[0] > right[0] + 3
    assert right[2] > left[2] + 3


def test_local_color_stays_close_to_sampled_base() -> None:
    """local 模式：glyph 色应贴近采样底色，仅有轻微差异。"""
    from core.ascii_watermark import _resolve_glyph_color

    rgb = np.array([180, 90, 70], dtype=np.uint8)
    subtle = _resolve_glyph_color(
        rgb, 140.0,
        color_mode="local",
        fixed_color=(0, 0, 0),
        local_contrast=0.12,
    )
    diff = sum(abs(int(rgb[i]) - subtle[i]) for i in range(3))
    assert 0 < diff < 95
    assert subtle[0] > subtle[2]


def test_author_inject_rate() -> None:
    letters = build_author_letters("ab")
    img = _solid(80, 80, (120, 140, 160))
    out = apply_ascii_watermark(
        img,
        opacity=0.9,
        cell_size=12,
        mode="author_luminance",
        author_text="ab",
        author_inject_rate=1.0,
        color_mode="fixed",
        color=(0, 0, 0),
    )
    assert np.any(out != img)


def test_local_gradient_mode() -> None:
    img = _solid(96, 96, (150, 170, 190))
    out = apply_ascii_watermark(
        img,
        opacity=0.85,
        cell_size=14,
        color_mode="local_gradient",
        gradient_strength=0.5,
        local_contrast=0.08,
        mode="fixed_char",
        fixed_char="?",
    )
    assert np.any(out != img)


def test_dark_fade_skips_bright_areas() -> None:
    white = _solid(96, 96, (250, 250, 250))
    dark_patch = white.copy()
    dark_patch[40:70, 40:70] = (40, 50, 60)
    out = apply_ascii_watermark(
        dark_patch,
        opacity=0.95,
        cell_size=14,
        lum_mask="dark_fade",
        mask_full_below=100.0,
        mask_fade_end=200.0,
        mode="fixed_char",
        fixed_char="#",
        color_mode="fixed",
        color=(0, 0, 0),
    )
    bright_diff = np.abs(out[0:20, 0:20].astype(int) - white[0:20, 0:20].astype(int)).sum()
    dark_diff = np.abs(out[45:65, 45:65].astype(int) - dark_patch[45:65, 45:65].astype(int)).sum()
    assert bright_diff < dark_diff


def test_grid_passes_increases_coverage() -> None:
    img = _solid(120, 120, (140, 160, 180))
    single = apply_ascii_watermark(
        img, opacity=0.95, cell_size=18, grid_passes=1,
        mode="fixed_char", fixed_char="#", color_mode="fixed", color=(20, 20, 20),
    )
    triple = apply_ascii_watermark(
        img, opacity=0.95, cell_size=18, grid_passes=3,
        mode="fixed_char", fixed_char="#", color_mode="fixed", color=(20, 20, 20),
    )
    d1 = np.abs(single.astype(int) - img.astype(int)).sum()
    d3 = np.abs(triple.astype(int) - img.astype(int)).sum()
    assert d3 > d1 * 1.5


def test_lum_ramp_keeps_faint_bright_watermark() -> None:
    """lum_ramp：亮区仍有 faint 水印，暗区更强。"""
    white = _solid(96, 96, (250, 250, 250))
    dark_patch = white.copy()
    dark_patch[40:70, 40:70] = (40, 50, 60)
    out = apply_ascii_watermark(
        dark_patch,
        opacity=0.95,
        cell_size=14,
        lum_mask="lum_ramp",
        mask_full_below=200.0,
        mask_fade_end=250.0,
        mask_bright_floor=0.10,
        mode="fixed_char",
        fixed_char="#",
        color_mode="fixed",
        color=(0, 0, 0),
    )
    bright_diff = np.abs(out[0:20, 0:20].astype(int) - white[0:20, 0:20].astype(int)).sum()
    dark_diff = np.abs(out[45:65, 45:65].astype(int) - dark_patch[45:65, 45:65].astype(int)).sum()
    assert bright_diff > 0
    assert dark_diff > bright_diff


def test_dark_adaptive_boost() -> None:
    """暗部 adaptive boost 应比亮部改动更大。"""
    img = np.zeros((80, 160, 3), dtype=np.uint8)
    img[:, :80] = (35, 45, 55)
    img[:, 80:] = (230, 235, 240)
    out = apply_ascii_watermark(
        img,
        opacity=0.95,
        cell_size=14,
        lum_mask="none",
        dark_contrast_boost=0.8,
        dark_alpha_boost=0.3,
        local_contrast=0.12,
        mode="fixed_char",
        fixed_char="#",
        color_mode="fixed",
        color=(200, 200, 200),
    )
    dark_diff = np.abs(out[20:60, 20:60].astype(int) - img[20:60, 20:60].astype(int)).sum()
    bright_diff = np.abs(out[20:60, 100:140].astype(int) - img[20:60, 100:140].astype(int)).sum()
    assert dark_diff > bright_diff * 1.5


def test_halftone_char_gate() -> None:
    """半调门控字符：与无门控网格输出不同。"""
    img = _solid(96, 96, (100, 120, 160))
    plain = apply_ascii_watermark(
        img, opacity=0.9, cell_size=12, layout="grid",
        mode="fixed_char", fixed_char="#", color_mode="fixed", color=(0, 0, 0),
    )
    gated = apply_ascii_watermark(
        img, opacity=0.9, cell_size=12, layout="grid", halftone_gate=True,
        mode="fixed_char", fixed_char="#", color_mode="fixed", color=(0, 0, 0),
    )
    assert not np.array_equal(plain, gated)


def test_halftone_layout() -> None:
    """半调网格：确定性输出，暗区改动大于亮区。"""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:, :50] = (40, 50, 60)
    img[:, 50:] = (240, 245, 250)
    out_a = apply_ascii_watermark(
        img, opacity=0.92, cell_size=10, layout="halftone", seed=1,
        lum_mask="none", color_mode="local", local_contrast=0.12,
    )
    out_b = apply_ascii_watermark(
        img, opacity=0.92, cell_size=10, layout="halftone", seed=1,
        lum_mask="none", color_mode="local", local_contrast=0.12,
    )
    np.testing.assert_array_equal(out_a, out_b)
    dark_diff = np.abs(out_a[:, :50].astype(int) - img[:, :50].astype(int)).sum()
    bright_diff = np.abs(out_a[:, 50:].astype(int) - img[:, 50:].astype(int)).sum()
    assert dark_diff > bright_diff


def test_dot_particles() -> None:
    """纯圆点粒子：有像素变化且不依赖字符。"""
    img = _solid(120, 120, (80, 100, 140))
    out = apply_ascii_watermark(
        img,
        opacity=0.9,
        cell_size=12,
        glyph_mode="dot",
        lum_mask="none",
        color_mode="local",
        local_contrast=0.14,
        particle_dot_scale=0.18,
    )
    assert np.any(out != img)


def test_particle_layout() -> None:
    """粒子布局应产生与规则网格不同的像素分布。"""
    img = _solid(120, 120, (120, 140, 160))
    grid = apply_ascii_watermark(
        img, opacity=0.9, cell_size=14, layout="grid", seed=5,
        mode="fixed_char", fixed_char="#", color_mode="fixed", color=(0, 0, 0),
    )
    particle = apply_ascii_watermark(
        img, opacity=0.9, cell_size=14, layout="particle", glyph_mode="ascii", seed=5,
        mode="fixed_char", fixed_char="#", color_mode="fixed", color=(0, 0, 0),
        particle_jitter=0.7, particle_size_min=0.5, particle_size_max=1.5,
    )
    assert not np.array_equal(grid, particle)


def test_invalid_input_raises() -> None:
    with pytest.raises(ValueError):
        apply_ascii_watermark(np.zeros((8, 8), dtype=np.uint8))
    with pytest.raises(ValueError):
        apply_ascii_watermark(np.zeros((4, 4, 3), dtype=np.uint8))


def test_halftone_ramp_charset_includes_author() -> None:
    cs = build_halftone_ramp_charset("cccola")
    assert "@" in cs
    assert "c" in cs
    assert cs.endswith(" ") or "." in cs


def test_bayer_dither_offsets_lum() -> None:
    a = _bayer_adjust_lum(200.0, 0, 0, levels=7, strength=0.8)
    b = _bayer_adjust_lum(200.0, 1, 0, levels=7, strength=0.8)
    assert a != b


def test_halftone_ramp_v2_changes_image() -> None:
    img = _solid(120, 120, (140, 160, 180))
    out = apply_ascii_watermark(
        img,
        opacity=0.88,
        cell_size=14,
        mode="author_luminance",
        author_text="cccola",
        use_halftone_ramp=True,
        dither="bayer",
        render_font_size=15,
        lum_mask="lum_ramp",
    )
    assert np.any(out != img)


def test_halftone_ramp_bright_has_gaps() -> None:
    """亮区 ramp 空格跳过 → 像素变化少于全铺满。"""
    white = _solid(96, 96, (250, 250, 250))
    ramp = apply_ascii_watermark(
        white,
        opacity=0.9,
        cell_size=12,
        mode="luminance",
        charset="@O0o·. ",
        use_halftone_ramp=True,
        dither="bayer",
        render_font_size=13,
        lum_mask="none",
        color_mode="fixed",
        color=(80, 80, 80),
    )
    solid = apply_ascii_watermark(
        white,
        opacity=0.9,
        cell_size=12,
        mode="fixed_char",
        fixed_char="#",
        lum_mask="none",
        color_mode="fixed",
        color=(80, 80, 80),
    )
    diff_ramp = np.abs(ramp.astype(int) - white.astype(int)).sum()
    diff_solid = np.abs(solid.astype(int) - white.astype(int)).sum()
    assert diff_ramp < diff_solid


def test_author_dot_mask_nonempty() -> None:
    grid, pixel, bbox = _build_author_dot_mask(
        "cccola",
        img_w=200,
        img_h=120,
        cell_w=10,
        cell_h=10,
        position="corner_br",
        mask_scale=1.0,
    )
    assert grid.any()
    assert pixel.any()
    assert bbox is not None


def test_halftone_author_fine_dots_corner_diff() -> None:
    """细点 stealth 署名应在署名侧比对侧改动更大。"""
    img = _solid(160, 200, (140, 150, 160))
    base = apply_ascii_watermark(
        img,
        opacity=0.9,
        cell_size=12,
        layout="halftone",
        seed=3,
        lum_mask="lum_ramp",
    )
    signed = apply_ascii_watermark(
        img,
        opacity=0.9,
        cell_size=12,
        layout="halftone",
        author_text="Jingwei",
        author_mask_mode="fine_stealth",
        author_mask_position="center_low",
        author_mask_scale=0.9,
        author_name_contrast=0.24,
        seed=3,
        lum_mask="lum_ramp",
    )
    mid = np.abs(signed[60:120, 70:130].astype(int) - base[60:120, 70:130].astype(int)).sum()
    corner = np.abs(signed[:40, :40].astype(int) - base[:40, :40].astype(int)).sum()
    assert mid > corner
    assert np.any(signed != base)


def test_author_center_low_position() -> None:
    _, pixel, bbox = _build_author_dot_mask(
        "Jingwei",
        img_w=240,
        img_h=180,
        cell_w=10,
        cell_h=10,
        position="center_low",
        mask_scale=1.0,
    )
    assert pixel.any()
    assert bbox is not None
    cx = (bbox[0] + bbox[2]) // 2
    cy = (bbox[1] + bbox[3]) // 2
    assert 240 * 0.35 < cx < 240 * 0.65
    assert 180 * 0.45 < cy < 180 * 0.72


def test_author_custom_anchor_moves_bbox() -> None:
    _, _, bbox_left = _build_author_dot_mask(
        "JW",
        img_w=400,
        img_h=240,
        cell_w=10,
        cell_h=10,
        position="custom",
        mask_scale=1.0,
        anchor_x=0.20,
        anchor_y=0.50,
    )
    _, _, bbox_right = _build_author_dot_mask(
        "JW",
        img_w=400,
        img_h=240,
        cell_w=10,
        cell_h=10,
        position="custom",
        mask_scale=1.0,
        anchor_x=0.80,
        anchor_y=0.50,
    )
    assert bbox_left is not None and bbox_right is not None
    cx_left = (bbox_left[0] + bbox_left[2]) // 2
    cx_right = (bbox_right[0] + bbox_right[2]) // 2
    assert cx_left < cx_right


def test_halftone_fine_full_covers_image() -> None:
    img = _solid(120, 120, (150, 160, 170))
    out = apply_ascii_watermark(
        img,
        opacity=0.9,
        cell_size=14,
        layout="halftone",
        author_text="ab",
        author_mask_mode="fine_full",
        fine_dot_base_contrast=0.09,
        lum_mask="none",
    )
    assert np.any(out != img)


def test_tile_grid_changes_image() -> None:
    img = _solid(120, 160, (140, 150, 160))
    out = apply_ascii_watermark(
        img,
        opacity=0.9,
        layout="tile_grid",
        tile_fade_mode="horizontal_lr",
        tile_fade_start=0.0,
        tile_fade_end=1.0,
        tile_blur_radius=4.0,
        tile_size=10,
    )
    assert np.any(out != img)


def test_tile_grid_diagonal_tl_clearer_than_br() -> None:
    """对角线渐变：左上清晰、右下磨砂。"""
    h, w = 160, 160
    img = _solid(h, w, (140, 150, 160))
    out = apply_ascii_watermark(
        img,
        opacity=0.88,
        layout="tile_grid",
        tile_fade_mode="diagonal_tl_br",
        tile_fade_start=0.10,
        tile_fade_end=0.85,
        tile_blur_radius=6.0,
        tile_size=22,
        tile_gap=4,
    )
    tl_diff = np.abs(out[:40, :40].astype(int) - img[:40, :40].astype(int)).mean()
    br_diff = np.abs(out[120:, 120:].astype(int) - img[120:, 120:].astype(int)).mean()
    assert br_diff > tl_diff * 1.5


def test_tile_center_protect_keeps_subject_clearer() -> None:
    """中心主体保护：开启后中心区域变化应小于未保护。"""
    h, w = 160, 160
    img = _solid(h, w, (140, 150, 160))
    common = dict(
        opacity=0.88,
        layout="tile_grid",
        tile_fade_mode="diagonal_tl_br",
        tile_fade_start=0.05,
        tile_fade_end=0.95,
        tile_blur_radius=6.0,
        tile_size=22,
        tile_gap=4,
    )
    bare = apply_ascii_watermark(img, tile_center_protect=0.0, **common)
    protected = apply_ascii_watermark(
        img, tile_center_protect=1.0, tile_center_protect_radius=0.58, **common,
    )
    cy, cx = h // 2, w // 2
    r = 28
    bare_center = np.abs(
        bare[cy - r:cy + r, cx - r:cx + r].astype(int)
        - img[cy - r:cy + r, cx - r:cx + r].astype(int)
    ).mean()
    prot_center = np.abs(
        protected[cy - r:cy + r, cx - r:cx + r].astype(int)
        - img[cy - r:cy + r, cx - r:cx + r].astype(int)
    ).mean()
    assert prot_center < bare_center * 0.35


def test_author_sequence_spells_in_order() -> None:
    """顺序注入应按作者名循环拼字。"""
    rng = np.random.default_rng(0)
    seq = [0]
    out: list[str] = []
    for _ in range(16):
        ch = _try_pick_author_char(
            author_name="Jingwei",
            author_letters="Jingwei",
            author_sequence_rate=1.0,
            author_inject_rate=0.0,
            author_seq_idx=seq,
            rng=rng,
        )
        assert ch is not None
        out.append(ch)
    assert out[:7] == list("Jingwei")
    assert out[7] == "J"


def test_halftone_keeps_dots_near_author_bbox() -> None:
    """署名 bbox 附近仍应有粗半调波点（亮底也不挖空）。"""
    img = _solid(200, 240, (230, 235, 240))
    out = apply_ascii_watermark(
        img,
        opacity=0.94,
        cell_size=14,
        layout="halftone",
        author_text="Jingwei",
        author_mask_mode="fine_stealth",
        author_mask_position="center_low",
        lum_mask="none",
        color_mode="local",
        local_contrast=0.18,
        seed=5,
    )
    _, _, bbox = _build_author_dot_mask(
        "Jingwei", img_w=240, img_h=200, cell_w=14, cell_h=14,
        position="center_low", mask_scale=0.85,
    )
    assert bbox is not None
    x0, y0, x1, y1 = bbox
    pad = 28
    region = out[
        max(0, y0 - pad):min(200, y1 + pad),
        max(0, x0 - pad):min(240, x1 + pad),
    ]
    base = img[
        max(0, y0 - pad):min(200, y1 + pad),
        max(0, x0 - pad):min(240, x1 + pad),
    ]
    assert np.abs(region.astype(int) - base.astype(int)).sum() > 500


def test_build_contour_warp_maps_stronger_on_edges() -> None:
    """垂直边缘图在边缘列应有更大位移。"""
    from core.ascii_watermark import _build_contour_warp_maps

    img = _solid(120, 120, (40, 40, 40))
    img[:, 60:] = (200, 200, 200)
    off_x, off_y, ang = _build_contour_warp_maps(
        img,
        cell_w=12,
        cell_h=12,
        n_rows=10,
        n_cols=10,
        img_w=120,
        img_h=120,
        strength=1.0,
    )
    edge_mag = float(np.abs(off_x[:, 5]).mean() + np.abs(off_y[:, 5]).mean())
    flat_mag = float(np.abs(off_x[:, 1]).mean() + np.abs(off_y[:, 1]).mean())
    assert edge_mag > flat_mag * 2.0
    assert float(np.abs(ang).max()) > 5.0


def test_background_chain_changes_output_outside_signature() -> None:
    """背景顺序链开启后，远离署名区的像素应有更多变化。"""
    img = _solid(200, 240, (120, 130, 140))
    base_kw = dict(
        opacity=0.94,
        cell_size=14,
        layout="grid",
        mode="author_luminance",
        author_text="AB",
        use_halftone_ramp=True,
        dither="bayer",
        lum_mask="none",
        author_sequence_rate=0.0,
        author_inject_rate=0.0,
        author_mask_mode="none",
        seed=3,
    )
    off = apply_ascii_watermark(
        img,
        author_background_sequence_rate=0.0,
        author_background_chain_stride=0,
        contour_warp_strength=0.0,
        **base_kw,
    )
    on = apply_ascii_watermark(
        img,
        author_background_sequence_rate=0.2,
        author_background_chain_stride=6,
        contour_warp_strength=0.0,
        **base_kw,
    )
    tl = np.abs(off[:80, :80].astype(int) - on[:80, :80].astype(int)).mean()
    assert tl > 0.12


def test_contour_warp_breaks_grid_regularity() -> None:
    """轮廓错位开启后输出应与规则网格版有可见差异。"""
    img = _solid(160, 160, (90, 100, 110))
    img[40:120, 60:100] = (210, 215, 220)
    common = dict(
        opacity=0.92,
        cell_size=12,
        layout="grid",
        mode="author_luminance",
        author_text="X",
        use_halftone_ramp=True,
        lum_mask="none",
        author_mask_mode="none",
        author_background_sequence_rate=0.0,
        seed=11,
    )
    flat = apply_ascii_watermark(img, contour_warp_strength=0.0, **common)
    warped = apply_ascii_watermark(img, contour_warp_strength=0.85, **common)
    diff = float(np.mean(np.abs(flat.astype(int) - warped.astype(int))))
    assert diff > 0.25
