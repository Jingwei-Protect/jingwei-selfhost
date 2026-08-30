"""Fast visible-layer-only preview (no invisible JW/DWT/LSB)."""

from __future__ import annotations

import cv2
import numpy as np

from core.pipeline import protect_image

_PREVIEW_MAX_SIDE = 1280


def compute_stealth_surface(
    *,
    mode: str,
    blur_bar_enabled: bool = False,
    emboss_enabled: bool = False,
    displacement_enabled: bool = False,
    displacement_text: str = "",
    face_emboss_enabled: bool = False,
    face_emboss_text: str = "",
    halftone_enabled: bool = False,
    halftone_text: str = "",
) -> bool:
    """Match protect API: anti-AI stack only when an attack layer is actually active."""
    if mode != "stealth":
        return False
    if mode.startswith("ultimate"):
        return True
    disp_on = displacement_enabled and bool(displacement_text.strip())
    fe_on = face_emboss_enabled and bool(face_emboss_text.strip())
    ht_on = halftone_enabled and bool(halftone_text.strip())
    return any((blur_bar_enabled, emboss_enabled, disp_on, fe_on, ht_on))


def downscale_for_preview(image: np.ndarray, max_side: int = _PREVIEW_MAX_SIDE) -> tuple[np.ndarray, float]:
    """Return a copy scaled for preview (max side ``max_side``) and the scale factor."""
    return _downscale_for_preview(image, max_side)


def _downscale_for_preview(image: np.ndarray, max_side: int = _PREVIEW_MAX_SIDE) -> tuple[np.ndarray, float]:
    h, w = image.shape[:2]
    scale = 1.0
    longest = max(h, w)
    if longest <= max_side:
        return image.copy(), scale
    scale = max_side / longest
    nh = max(64, int(round(h * scale)))
    nw = max(64, int(round(w * scale)))
    out = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_AREA)
    return out, scale


def render_visible_preview(
    image: np.ndarray,
    *,
    mode: str = "stealth",
    signature_text: str = "",
    signature_position: str = "bottom_right",
    blur_bar_enabled: bool = False,
    blur_bar_text: str = "",
    blur_bar_y_ratio: float = 0.5,
    blur_bar_sigma: int = 12,
    blur_bar_count: int = 1,
    blur_region_mask: np.ndarray | None = None,
    emboss_enabled: bool = False,
    emboss_pattern: str = "diagonal",
    emboss_text: str = "",
    emboss_text_density: str = "dense",
    emboss_strength: str = "medium",
    displacement_enabled: bool = False,
    displacement_text: str = "",
    displacement_shift: int = 10,
    displacement_density: str = "normal",
    displacement_font_ratio: float = 0.15,
    displacement_mode: str = "scatter",
    displacement_seed: int = 42,
    displacement_shadow: bool = True,
    displacement_shadow_strength: float = 0.35,
    displacement_anchor_x: float = -1.0,
    displacement_anchor_y: float = -1.0,
    face_emboss_enabled: bool = False,
    face_emboss_text: str = "",
    face_emboss_copies: int = 3,
    face_emboss_seed: int = 42,
    face_emboss_patch_ratio: float = 0.30,
    face_emboss_shift: int = 12,
    face_emboss_opacity: float = 0.25,
    jw_footer_preview: bool = False,
    jw_footer_artist: str = "",
    jw_creation: str = "OC",
    jw_restrictions: list[str] | None = None,
    stealth_surface: bool | None = None,
    max_side: int = _PREVIEW_MAX_SIDE,
    halftone_enabled: bool = False,
    halftone_style: str = "ascii_chars",
    halftone_text: str = "",
    halftone_size: int = 50,
    halftone_density: int = 50,
    halftone_visibility: int = 50,
    halftone_anchor_x: float = -1.0,
    halftone_anchor_y: float = -1.0,
    halftone_signature: int = 50,
    halftone_signature_size: int = 50,
    halftone_dot_texture: int = 0,
    halftone_advanced: int = 50,
    halftone_background_chain: int = 78,
    halftone_contour_warp: int = 70,
    halftone_credit_faint: bool = False,
    logo_rgba: np.ndarray | None = None,
    logo_opacity: float = 0.40,
    logo_scale: float = 0.18,
    logo_position: str = "bottom_right",
    logo_anchor_x: float = -1.0,
    logo_anchor_y: float = -1.0,
    logo_tint: str = "gray",
    logo_shift_px: int = 10,
) -> np.ndarray:
    """Return RGB preview with visible layers only.

    ``max_side`` caps the working resolution. Callers lower it when the
    (expensive) anti-AI stealth surface is rendered into the preview so the
    faithful texture stays fast and memory-bounded.
    """
    if stealth_surface is None:
        stealth_surface = compute_stealth_surface(
            mode=mode,
            blur_bar_enabled=blur_bar_enabled,
            emboss_enabled=emboss_enabled,
            displacement_enabled=displacement_enabled,
            displacement_text=displacement_text,
            face_emboss_enabled=face_emboss_enabled,
            face_emboss_text=face_emboss_text,
            halftone_enabled=halftone_enabled,
            halftone_text=halftone_text,
        )

    work, _ = _downscale_for_preview(image, max_side)

    if blur_region_mask is not None and blur_region_mask.shape[:2] != work.shape[:2]:
        h, w = work.shape[:2]
        blur_region_mask = cv2.resize(
            blur_region_mask.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR,
        )

    out = protect_image(
        work,
        level="standard",
        delivery_mode=True,
        protection_mode=mode,
        blur_bar=blur_bar_enabled,
        blur_bar_text=blur_bar_text,
        blur_bar_position="custom" if blur_bar_y_ratio >= 0 else "below_face",
        blur_bar_sigma=blur_bar_sigma,
        blur_bar_count=blur_bar_count,
        blur_bar_y_ratio=blur_bar_y_ratio,
        blur_region_mask=blur_region_mask,
        emboss=emboss_enabled,
        emboss_pattern=emboss_pattern,
        emboss_text=emboss_text,
        emboss_text_density=emboss_text_density,
        emboss_strength=emboss_strength,
        displacement=displacement_enabled,
        displacement_text=displacement_text,
        displacement_shift=displacement_shift,
        displacement_density=displacement_density,
        displacement_font_ratio=displacement_font_ratio,
        displacement_mode=displacement_mode,
        displacement_seed=displacement_seed,
        displacement_shadow=displacement_shadow,
        displacement_shadow_strength=displacement_shadow_strength,
        displacement_anchor_x=displacement_anchor_x,
        displacement_anchor_y=displacement_anchor_y,
        face_emboss_text=face_emboss_text if face_emboss_enabled else "",
        face_emboss_copies=face_emboss_copies if face_emboss_enabled else 0,
        face_emboss_seed=face_emboss_seed,
        face_emboss_patch_ratio=face_emboss_patch_ratio,
        face_emboss_shift=face_emboss_shift,
        face_emboss_opacity=face_emboss_opacity,
        artist_signature=signature_text,
        artist_signature_position=signature_position,
        stealth_surface=stealth_surface,
        halftone_enabled=halftone_enabled,
        halftone_style=halftone_style,
        halftone_text=halftone_text,
        halftone_size=halftone_size,
        halftone_density=halftone_density,
        halftone_visibility=halftone_visibility,
        halftone_anchor_x=halftone_anchor_x,
        halftone_anchor_y=halftone_anchor_y,
        halftone_signature=halftone_signature,
        halftone_signature_size=halftone_signature_size,
        halftone_dot_texture=halftone_dot_texture,
        halftone_background_chain=halftone_background_chain,
        halftone_contour_warp=halftone_contour_warp,
        halftone_credit_faint=halftone_credit_faint,
        logo_rgba=logo_rgba,
        logo_opacity=logo_opacity,
        logo_scale=logo_scale,
        logo_position=logo_position,
        logo_anchor_x=logo_anchor_x,
        logo_anchor_y=logo_anchor_y,
        logo_tint=logo_tint,
        logo_shift_px=logo_shift_px,
    )

    if jw_footer_preview and jw_footer_artist.strip():
        from core.jingwei_protocol import (
            JwManifest,
            apply_jw_footer_strip,
            parse_creation,
            restrictions_from_ids,
        )

        manifest = JwManifest(
            creation=parse_creation(jw_creation),
            restrictions=restrictions_from_ids(jw_restrictions or []),
            visible_badge=False,
            artist=jw_footer_artist.strip(),
        )
        out = apply_jw_footer_strip(out, manifest)

    return out
