"""署名·快速 (credit) visible-layer recipe.

Textured pictures use the dog c024 font/shadow (7%, 0.1518) with a 6 px
warp. Flat illustration-like pictures use a host-colour letter
grid from the user's 署名, plus one dotted name. White paper keeps the 2b
name; coloured flats use the nB name. Logo is an extra faint stamp and
does not turn the letter grid off.

The faint name defaults to center-low; ``halftone_anchor_*`` / a custom
position override that. Manual / stealth mode keeps the caller's logo
sliders unchanged.
"""

from __future__ import annotations

from typing import Literal, NamedTuple

import numpy as np

CREDIT_FLAT_RATIO = 0.55
CREDIT_PAPER_WHITE_RATIO = 0.50
CREDIT_PAPER_LUMA = 245.0
CREDIT_ASCII_VISIBILITY = 8
CREDIT_ASCII_SIGNATURE = 0
CREDIT_DISP_FONT_RATIO = 0.07
CREDIT_DISP_SHIFT = 6
CREDIT_DISP_SHADOW_STRENGTH = 0.1518
CREDIT_LOGO_OPACITY = 0.06
CREDIT_LOGO_SCALE = 0.08
# Same 6 px warp as credit text displacement (dog c024).
CREDIT_LOGO_SHIFT = CREDIT_DISP_SHIFT

VisibleMark = Literal["auto", "ascii", "displacement"]

_PUNCTUATION_CHARSET = " .,:;+-=~"

# Shared faint field. Name depth is overlaid per paper vs coloured flat.
CREDIT_ASCII_FAINT_KWARGS: dict[str, float | int | str | bool] = {
    "mode": "luminance",
    "use_halftone_ramp": False,
    "author_mask_mode": "fine_dots",
    # Default only; resolve_halftone_kwargs re-applies a user corner / drag.
    "author_mask_position": "center_low",
    "author_mask_scale": 1.25,
    "author_dot_radius": 1,
    # White paper must keep the field; lum_ramp was wiping dots at ~255.
    "lum_mask": "none",
    "author_background_sequence_rate": 0.32,
    "author_background_inject_rate": 0.0,
    "author_background_chain_stride": 8,
    "contour_warp_strength": 0.0,
    "author_inject_rate": 0.0,
    "author_sequence_rate": 0.0,
    "author_tile_contrast": 0.0,
    "local_contrast": 0.06,
    "opacity": 0.78,
    "dark_contrast_boost": 0.0,
    "dark_alpha_boost": 0.0,
}

# White-bg 2b name (locked on paper).
CREDIT_ASCII_PAPER_NAME: dict[str, float] = {
    "author_name_contrast": 0.10,
    "author_mask_opacity": 0.54,
}

# Coloured-flat nB name (locked on the cat).
CREDIT_ASCII_FLAT_NAME: dict[str, float] = {
    "author_name_contrast": 0.18,
    "author_mask_opacity": 0.70,
}


class CreditRecipe(NamedTuple):
    ascii_enabled: bool
    ascii_text: str
    ascii_visibility: int | None
    ascii_signature: int | None
    disp_enabled: bool
    disp_text: str
    disp_font_ratio: float | None
    disp_shift: int | None
    disp_shadow: bool | None
    disp_shadow_strength: float | None
    ascii_faint: bool


_DEFAULT_CREDIT_NAME = "Jingwei"


def credit_letter_charset(author: str) -> str:
    """Build a punctuation-free charset from the on-image 署名."""
    kept = "".join(
        c for c in (author or "").strip()
        if not c.isspace() and c not in _PUNCTUATION_CHARSET
    )
    return kept or "JW"


def estimate_paper_white_ratio(image: np.ndarray) -> float:
    """Share of pixels whose Rec.601 luma is at or above paper white.

    Coloured flats (cat ~0.15) stay below ``CREDIT_PAPER_WHITE_RATIO``;
    near-white manuscript pages sit well above it.
    """
    if image.ndim != 3 or image.shape[2] < 3:
        return 0.0
    rgb = image[:, :, :3].astype(np.float32)
    luma = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    return float((luma >= CREDIT_PAPER_LUMA).mean())


def resolve_credit_ascii_faint_kwargs(
    image: np.ndarray | None,
    author_text: str,
) -> dict[str, float | int | str | bool]:
    """Faint ASCII kwargs: shared letter field + paper or nB name depth."""
    out: dict[str, float | int | str | bool] = dict(CREDIT_ASCII_FAINT_KWARGS)
    out["charset"] = credit_letter_charset(author_text)
    if image is not None and estimate_paper_white_ratio(image) < CREDIT_PAPER_WHITE_RATIO:
        out.update(CREDIT_ASCII_FLAT_NAME)
    else:
        out.update(CREDIT_ASCII_PAPER_NAME)
    return out


def _is_placeholder_name(text: str) -> bool:
    """Product leftover ``Jingwei`` is not a slider the user chose."""
    return (text or "").strip().casefold() == "jingwei"


def _credit_visible_name(halftone_text: str, artist: str, displacement_text: str) -> str:
    """画面署名 > 创作者姓名 > ASCII. Jingwei in 署名 is a real name."""
    sign = (displacement_text or "").strip()
    if sign:
        return sign
    author = (artist or "").strip()
    if author:
        return author
    ht = (halftone_text or "").strip()
    if ht:
        return ht
    return _DEFAULT_CREDIT_NAME


def _user_chose_layer_text(enabled: bool, text: str) -> bool:
    """True when the caller enabled a layer with a non-placeholder string."""
    return bool(enabled and (text or "").strip() and not _is_placeholder_name(text))


def _normalize_visible_mark(visible_mark: str) -> VisibleMark:
    mark = (visible_mark or "auto").strip().lower()
    if mark in ("ascii", "displacement"):
        return mark
    return "auto"


def _passthrough_recipe(
    *,
    halftone_enabled: bool,
    ht_text: str,
    displacement_enabled: bool,
    disp_text: str,
) -> CreditRecipe:
    return CreditRecipe(
        ascii_enabled=halftone_enabled,
        ascii_text=ht_text,
        ascii_visibility=None,
        ascii_signature=None,
        disp_enabled=displacement_enabled,
        disp_text=disp_text,
        disp_font_ratio=None,
        disp_shift=None,
        disp_shadow=None,
        disp_shadow_strength=None,
        ascii_faint=False,
    )


def _faint_ascii_recipe(
    *,
    ht_text: str,
    disp_text: str,
    name: str,
    keep_user_sliders: bool,
) -> CreditRecipe:
    return CreditRecipe(
        ascii_enabled=True,
        ascii_text=name,
        ascii_visibility=None if keep_user_sliders else CREDIT_ASCII_VISIBILITY,
        ascii_signature=None if keep_user_sliders else CREDIT_ASCII_SIGNATURE,
        disp_enabled=False,
        disp_text=disp_text,
        disp_font_ratio=None,
        disp_shift=None,
        disp_shadow=None,
        disp_shadow_strength=None,
        ascii_faint=True,
    )


def _c024_disp_recipe(
    *,
    ht_text: str,
    name: str,
) -> CreditRecipe:
    """Dog c024 stamp only — never keep a leftover ASCII grid or stealth sliders.

    署名·快速 fills displacement text from the artist name, so a non-empty
    string is not a slider the user chose. Credit displacement is always the
    experimental 7% / 6 px / 0.1518 rung (c024 font and shadow; 6 px warp).
    """
    return CreditRecipe(
        ascii_enabled=False,
        ascii_text=ht_text,
        ascii_visibility=None,
        ascii_signature=None,
        disp_enabled=True,
        disp_text=name,
        disp_font_ratio=CREDIT_DISP_FONT_RATIO,
        disp_shift=CREDIT_DISP_SHIFT,
        disp_shadow=True,
        disp_shadow_strength=CREDIT_DISP_SHADOW_STRENGTH,
        ascii_faint=False,
    )


def resolve_credit_recipe(
    *,
    mode: str,
    image: np.ndarray,
    halftone_enabled: bool,
    halftone_text: str,
    artist: str,
    displacement_enabled: bool,
    displacement_text: str,
    visible_mark: str = "auto",
    logo_present: bool = False,
) -> CreditRecipe:
    """Decide which visible layers credit mode should turn on.

    Credit displacement is always the dog c024 font/shadow with a 6 px warp
    and never keeps a leftover ASCII grid. ``ascii_faint`` is on for credit + flat
    so the host-colour grid is used even after the UI auto-enables ASCII.

    ``visible_mark``: ``auto`` (flat vs texture), ``ascii`` (cat grid),
    or ``displacement`` (dog c024). A credit-mode logo is an extra stamp
    and does not skip these layers. ``logo_present`` is kept for callers.
    """
    ht_text = (halftone_text or "").strip()
    disp_text = (displacement_text or "").strip()
    name = _credit_visible_name(ht_text, artist, disp_text)

    if mode != "credit":
        return _passthrough_recipe(
            halftone_enabled=halftone_enabled,
            ht_text=ht_text,
            displacement_enabled=displacement_enabled,
            disp_text=disp_text,
        )

    mark = _normalize_visible_mark(visible_mark)
    if mark == "ascii":
        return _faint_ascii_recipe(
            ht_text=ht_text,
            disp_text=disp_text,
            name=name,
            keep_user_sliders=_user_chose_layer_text(halftone_enabled, ht_text),
        )
    if mark == "displacement":
        return _c024_disp_recipe(
            ht_text=ht_text,
            name=name,
        )

    from core.jingwei_protocol import estimate_flat_ratio

    if estimate_flat_ratio(image) >= CREDIT_FLAT_RATIO:
        return _faint_ascii_recipe(
            ht_text=ht_text,
            disp_text=disp_text,
            name=name,
            keep_user_sliders=_user_chose_layer_text(halftone_enabled, ht_text),
        )
    return _c024_disp_recipe(
        ht_text=ht_text,
        name=name,
    )


def resolve_credit_logo_opacity(
    *,
    mode: str,
    logo_present: bool,
    requested: float,
) -> float:
    """Credit logos use a fixed faint imprint; stealth keeps the slider."""
    if mode == "credit" and logo_present:
        return CREDIT_LOGO_OPACITY
    return requested


def resolve_credit_logo_scale(
    *,
    mode: str,
    logo_present: bool,
    requested: float,
) -> float:
    """Credit logos use a small faint stamp; stealth keeps the slider."""
    if mode == "credit" and logo_present:
        return CREDIT_LOGO_SCALE
    return requested


def resolve_credit_ascii(
    *,
    mode: str,
    image: np.ndarray,
    halftone_enabled: bool,
    halftone_text: str,
    artist: str,
    displacement_text: str,
    visible_mark: str = "auto",
    logo_present: bool = False,
) -> tuple[bool, str, int | None]:
    """Compatibility wrapper — ASCII half of ``resolve_credit_recipe``."""
    recipe = resolve_credit_recipe(
        mode=mode,
        image=image,
        halftone_enabled=halftone_enabled,
        halftone_text=halftone_text,
        artist=artist,
        displacement_enabled=False,
        displacement_text=displacement_text,
        visible_mark=visible_mark,
        logo_present=logo_present,
    )
    return recipe.ascii_enabled, recipe.ascii_text, recipe.ascii_visibility
