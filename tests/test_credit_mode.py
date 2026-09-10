"""Credit / 署名·快速 defaults — c024 displacement vs faint ASCII."""

from __future__ import annotations

import numpy as np
import pytest

from core.credit_mode import (
    CREDIT_ASCII_FAINT_KWARGS,
    CREDIT_ASCII_FLAT_NAME,
    CREDIT_ASCII_PAPER_NAME,
    CREDIT_ASCII_SIGNATURE,
    CREDIT_ASCII_VISIBILITY,
    CREDIT_DISP_FONT_RATIO,
    CREDIT_DISP_SHADOW_STRENGTH,
    CREDIT_DISP_SHIFT,
    CREDIT_FLAT_RATIO,
    CREDIT_LOGO_OPACITY,
    CREDIT_LOGO_SCALE,
    CREDIT_LOGO_SHIFT,
    CREDIT_PAPER_WHITE_RATIO,
    credit_letter_charset,
    estimate_paper_white_ratio,
    resolve_credit_ascii,
    resolve_credit_ascii_faint_kwargs,
    resolve_credit_logo_opacity,
    resolve_credit_logo_scale,
    resolve_credit_recipe,
)


def test_credit_flat_enables_faint_ascii() -> None:
    img = np.full((96, 128, 3), 220, dtype=np.uint8)
    recipe = resolve_credit_recipe(
        mode="credit",
        image=img,
        halftone_enabled=False,
        halftone_text="",
        artist="小明",
        displacement_enabled=False,
        displacement_text="",
    )
    assert recipe.ascii_enabled is True
    assert recipe.ascii_text == "小明"
    assert recipe.ascii_visibility == CREDIT_ASCII_VISIBILITY
    assert recipe.ascii_signature == CREDIT_ASCII_SIGNATURE
    assert recipe.ascii_faint is True
    assert recipe.disp_enabled is False
    on, text, vis = resolve_credit_ascii(
        mode="credit",
        image=img,
        halftone_enabled=False,
        halftone_text="",
        artist="小明",
        displacement_text="",
    )
    assert on is True
    assert text == "小明"
    assert vis == 8


def test_credit_textured_uses_c024_displacement() -> None:
    rng = np.random.default_rng(0)
    img = rng.integers(0, 255, (128, 160, 3), dtype=np.uint8)
    recipe = resolve_credit_recipe(
        mode="credit",
        image=img,
        halftone_enabled=False,
        halftone_text="",
        artist="小明",
        displacement_enabled=False,
        displacement_text="",
    )
    assert recipe.disp_enabled is True
    assert recipe.disp_text == "小明"
    assert recipe.disp_font_ratio == CREDIT_DISP_FONT_RATIO
    assert recipe.disp_shift == CREDIT_DISP_SHIFT
    assert recipe.disp_shadow is True
    assert recipe.disp_shadow_strength == CREDIT_DISP_SHADOW_STRENGTH


def test_credit_displacement_shift_is_six_px() -> None:
    """Ladder pick: keep c024 font/shadow, warp 6 px instead of 3."""
    assert CREDIT_DISP_SHIFT == 6


def test_stealth_mode_does_not_auto_ascii() -> None:
    img = np.full((96, 128, 3), 220, dtype=np.uint8)
    on, text, vis = resolve_credit_ascii(
        mode="stealth",
        image=img,
        halftone_enabled=False,
        halftone_text="",
        artist="小明",
        displacement_text="",
    )
    assert on is False
    assert vis is None


def test_user_ascii_is_kept() -> None:
    img = np.full((96, 128, 3), 220, dtype=np.uint8)
    on, text, vis = resolve_credit_ascii(
        mode="credit",
        image=img,
        halftone_enabled=True,
        halftone_text="Jingwei",
        artist="小明",
        displacement_text="Mine",
    )
    assert on is True
    assert text == "Mine"
    assert vis == CREDIT_ASCII_VISIBILITY
    recipe = resolve_credit_recipe(
        mode="credit",
        image=img,
        halftone_enabled=True,
        halftone_text="Jingwei",
        artist="小明",
        displacement_enabled=False,
        displacement_text="Mine",
    )
    assert recipe.ascii_text == "Mine"
    assert recipe.ascii_faint is True


def test_credit_leftover_jingwei_yields_to_artist() -> None:
    img = np.full((96, 128, 3), 220, dtype=np.uint8)
    recipe = resolve_credit_recipe(
        mode="credit",
        image=img,
        halftone_enabled=True,
        halftone_text="Jingwei",
        artist="小明",
        displacement_enabled=False,
        displacement_text="",
    )
    assert recipe.ascii_text == "小明"
    assert recipe.ascii_faint is True


def test_credit_jingwei_sign_is_kept() -> None:
    rng = np.random.default_rng(3)
    img = rng.integers(0, 255, (128, 160, 3), dtype=np.uint8)
    recipe = resolve_credit_recipe(
        mode="credit",
        image=img,
        halftone_enabled=False,
        halftone_text="jingwei",
        artist="小明",
        displacement_enabled=True,
        displacement_text="Jingwei",
    )
    assert recipe.disp_text == "Jingwei"
    assert recipe.disp_font_ratio == CREDIT_DISP_FONT_RATIO


def _assert_c024_displacement(recipe: object, *, text: str) -> None:
    assert recipe.disp_enabled is True
    assert recipe.disp_text == text
    assert recipe.disp_font_ratio == CREDIT_DISP_FONT_RATIO
    assert recipe.disp_shift == CREDIT_DISP_SHIFT
    assert recipe.disp_shadow is True
    assert recipe.disp_shadow_strength == CREDIT_DISP_SHADOW_STRENGTH
    assert recipe.ascii_enabled is False
    assert recipe.ascii_faint is False


def test_credit_named_displacement_still_uses_c024() -> None:
    """署名·快速 auto-fills the artist as displacement text — that is not a slider choice."""
    rng = np.random.default_rng(1)
    img = rng.integers(0, 255, (128, 160, 3), dtype=np.uint8)
    recipe = resolve_credit_recipe(
        mode="credit",
        image=img,
        halftone_enabled=False,
        halftone_text="",
        artist="小明",
        displacement_enabled=True,
        displacement_text="Mine",
    )
    _assert_c024_displacement(recipe, text="Mine")


def test_credit_displacement_ignores_leftover_ascii() -> None:
    rng = np.random.default_rng(1)
    img = rng.integers(0, 255, (128, 160, 3), dtype=np.uint8)
    recipe = resolve_credit_recipe(
        mode="credit",
        image=img,
        halftone_enabled=True,
        halftone_text="小明",
        artist="小明",
        displacement_enabled=True,
        displacement_text="小明",
        visible_mark="displacement",
    )
    _assert_c024_displacement(recipe, text="小明")


def test_credit_auto_textured_ignores_leftover_ascii() -> None:
    rng = np.random.default_rng(2)
    img = rng.integers(0, 255, (128, 160, 3), dtype=np.uint8)
    recipe = resolve_credit_recipe(
        mode="credit",
        image=img,
        halftone_enabled=True,
        halftone_text="小明",
        artist="小明",
        displacement_enabled=True,
        displacement_text="小明",
        visible_mark="auto",
    )
    _assert_c024_displacement(recipe, text="小明")


def test_stealth_displacement_keeps_caller_sliders() -> None:
    rng = np.random.default_rng(1)
    img = rng.integers(0, 255, (128, 160, 3), dtype=np.uint8)
    recipe = resolve_credit_recipe(
        mode="stealth",
        image=img,
        halftone_enabled=False,
        halftone_text="",
        artist="小明",
        displacement_enabled=True,
        displacement_text="Mine",
    )
    assert recipe.disp_enabled is True
    assert recipe.disp_text == "Mine"
    assert recipe.disp_font_ratio is None
    assert recipe.disp_shadow_strength is None
    assert recipe.ascii_enabled is False


def test_credit_ascii_faint_kwargs_keep_large_faint_signature() -> None:
    kw = CREDIT_ASCII_FAINT_KWARGS
    assert kw["author_mask_mode"] == "fine_dots"
    assert kw["author_mask_position"] == "center_low"
    assert float(kw["author_mask_scale"]) >= 1.2
    assert kw["lum_mask"] == "none"
    assert kw["mode"] == "luminance"
    assert kw["author_background_chain_stride"] == 8
    assert kw["contour_warp_strength"] == 0.0
    assert kw["local_contrast"] < 0.12
    assert kw["opacity"] < 0.88
    assert float(CREDIT_ASCII_PAPER_NAME["author_name_contrast"]) == pytest.approx(0.10)
    assert float(CREDIT_ASCII_PAPER_NAME["author_mask_opacity"]) == pytest.approx(0.54)
    assert float(CREDIT_ASCII_FLAT_NAME["author_name_contrast"]) == pytest.approx(0.18)
    assert float(CREDIT_ASCII_FLAT_NAME["author_mask_opacity"]) == pytest.approx(0.70)


def test_credit_letter_charset_has_no_punctuation() -> None:
    assert credit_letter_charset("Jingwei") == "Jingwei"
    assert credit_letter_charset("SIGA") == "SIGA"
    assert credit_letter_charset("小明") == "小明"
    for ch in " .,:;+-=~":
        assert ch not in credit_letter_charset("Jingwei")


def test_paper_white_ratio_splits_cat_from_paper() -> None:
    paper = np.full((80, 100, 3), 252, dtype=np.uint8)
    wash = np.full((80, 100, 3), 160, dtype=np.uint8)
    assert estimate_paper_white_ratio(paper) >= CREDIT_PAPER_WHITE_RATIO
    assert estimate_paper_white_ratio(wash) < CREDIT_PAPER_WHITE_RATIO
    paper_kw = resolve_credit_ascii_faint_kwargs(paper, "Jingwei")
    flat_kw = resolve_credit_ascii_faint_kwargs(wash, "SIGA")
    assert paper_kw["author_name_contrast"] == pytest.approx(0.10)
    assert flat_kw["author_name_contrast"] == pytest.approx(0.18)
    assert paper_kw["charset"] == "Jingwei"
    assert flat_kw["charset"] == "SIGA"
    assert paper_kw["author_background_chain_stride"] == 8
    assert flat_kw["author_background_chain_stride"] == 8


def test_credit_logo_keeps_fullscreen_layers() -> None:
    img = np.full((96, 128, 3), 220, dtype=np.uint8)
    recipe = resolve_credit_recipe(
        mode="credit",
        image=img,
        halftone_enabled=True,
        halftone_text="Mine",
        artist="小明",
        displacement_enabled=True,
        displacement_text="Mine",
        visible_mark="ascii",
        logo_present=True,
    )
    assert recipe.ascii_enabled is True
    assert recipe.ascii_faint is True
    assert recipe.ascii_text == "Mine"
    assert recipe.disp_enabled is False


def test_credit_force_ascii_on_textured() -> None:
    rng = np.random.default_rng(0)
    img = rng.integers(0, 255, (128, 160, 3), dtype=np.uint8)
    recipe = resolve_credit_recipe(
        mode="credit",
        image=img,
        halftone_enabled=False,
        halftone_text="",
        artist="小明",
        displacement_enabled=False,
        displacement_text="",
        visible_mark="ascii",
    )
    assert recipe.ascii_enabled is True
    assert recipe.ascii_faint is True
    assert recipe.disp_enabled is False
    assert recipe.ascii_text == "小明"


def test_credit_force_displacement_on_flat() -> None:
    img = np.full((96, 128, 3), 220, dtype=np.uint8)
    recipe = resolve_credit_recipe(
        mode="credit",
        image=img,
        halftone_enabled=True,
        halftone_text="小明",
        artist="小明",
        displacement_enabled=False,
        displacement_text="",
        visible_mark="displacement",
    )
    assert recipe.disp_enabled is True
    assert recipe.disp_font_ratio == CREDIT_DISP_FONT_RATIO
    assert recipe.disp_shadow_strength == CREDIT_DISP_SHADOW_STRENGTH
    assert recipe.ascii_enabled is False
    assert recipe.ascii_faint is False


def test_credit_logo_uses_faint_opacity() -> None:
    assert resolve_credit_logo_opacity(
        mode="credit",
        logo_present=True,
        requested=0.80,
    ) == CREDIT_LOGO_OPACITY
    assert CREDIT_LOGO_OPACITY == pytest.approx(0.06)
    assert CREDIT_LOGO_SCALE == pytest.approx(0.08)
    assert CREDIT_LOGO_SHIFT == CREDIT_DISP_SHIFT
    assert CREDIT_LOGO_SHIFT == 6
    assert resolve_credit_logo_scale(mode="credit", logo_present=True, requested=0.18) == pytest.approx(
        CREDIT_LOGO_SCALE
    )
    assert resolve_credit_logo_scale(mode="stealth", logo_present=True, requested=0.18) == pytest.approx(0.18)


def test_stealth_logo_keeps_requested_opacity() -> None:
    assert resolve_credit_logo_opacity(
        mode="stealth",
        logo_present=True,
        requested=0.80,
    ) == 0.80
