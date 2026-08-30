"""Stage 5：保護管線（Pipeline）— 依強度預設串接 M1–M7，檔案 API 另接 M10。

記憶體路徑 ``protect_image`` 按固定順序套用擾動模組；**M10（合規元數據）僅在**
``protect_image_file`` 寫檔後以檔案路徑嵌入。

套用順序（重要）
----------------
1. **M7** 梯度擾動（若該強度啟用）— 邊緣偵測需相對乾淨的輸入。
2. **M1** DCT 擾動
3. **M2** 自適應噪聲（若啟用）
4. **M3** 藍通道擾動
5. **M6** 紋理疊加（若啟用）
6. **M5** 可見水印（見下方 OPTION A）— 疊在最終像素語意上、且在 LSB 之前
7. **M4** LSB 隱形水印（若 ``watermark_text`` 非空）— 須最後，避免後續運算破壞位元平面

可見水印（M5）— PRD OPTION A
----------------------------
**僅在** ``level=="strong"`` **且** ``visible_watermark_text`` 經 ``strip()`` 後非空時
套用 M5。``strong`` 預設配方「具備 M5 能力」，並**不**強制疊加；空字串則不套用。

若在 ``light`` 或 ``standard`` 下傳入非空（strip 後）的可見水印字串，則**不套用**
M5，並發出 ``UserWarning``（訊息含實際 ``level``）。強度專用 PSNR 驗收通常在
**不啟用可見水印** 下量測；可見水印會明顯拉低 PSNR，屬設計預期。

種子去相關：M7→``seed``、M1→``seed+1``、M2→``seed+2``、M3→``seed+3``、M6→``seed+4``；
M4/M5 底層 API 無 ``seed`` 參數，不傳。
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image

from core.adaptive_noise import apply_adaptive_noise
from core.blue_channel import apply_blue_channel_perturbation
from core.compliance_metadata import embed_compliance_metadata
from core.dct_perturb import apply_dct_perturbation
from core.gradient_disturb import apply_gradient_disturbance
from core.lsb_watermark import embed_lsb_watermark
from core.texture_pollution import apply_texture_pollution
from core.visible_watermark import apply_visible_watermark
from core.microtext_overlay import (
    DEFAULT_DELIVERY_MICROTEXT,
    apply_microtext_overlay,
)
from core.semantic_injection import apply_semantic_injection
from core.instruction_injection import apply_instruction_injection

Level = Literal["light", "standard", "strong"]
_LEVELS = frozenset({"light", "standard", "strong"})

ProtectionMode = Literal[
    "microtext", "watermark", "hybrid",
    "poison_semantic", "poison_instruction", "poison_full",
    "framed_canvas",
    "jumping_moire",
    "jumping_moire_plus",
    "max_protection",
    "max_protection_v2",
    "ultimate",
    "ultimate_color",
    "ultimate_grayscale",
    "stealth",
    "credit",
    "face_emboss_lock",
]

SignaturePosition = Literal[
    "bottom_right", "bottom_left", "top_right", "top_left",
]

_DELIVERY_MICROTEXT_OPACITY = 0.08
_DELIVERY_WATERMARK_OPACITY = 0.35
_DELIVERY_WATERMARK_DENSITY = "dense"

_POISON_SEMANTIC_OPACITY = 0.25
_POISON_SEMANTIC_PATCH_COUNT = 12
_POISON_INSTRUCTION_OPACITY = 0.12
_POISON_INSTRUCTION_CONTRAST = 6

_DELIVERY_MOIRE_OPACITY = 0.04
_DELIVERY_MOIRE_PLUS_OPACITY = 0.10
_DELIVERY_RGB_OFFSET_R: tuple[int, int] = (2, 0)
_DELIVERY_RGB_OFFSET_B: tuple[int, int] = (-2, 0)
_MAX_MOIRE_OPACITY = 0.20
_MAX_RGB_R: tuple[int, int] = (6, 0)
_MAX_RGB_B: tuple[int, int] = (-6, 0)
_MAX_TRIPLE_OPACITY = 0.18
_MAX_EDGE_INTENSITY = 0.4

_MAX_V2_TRIPLE_OPACITY = 0.45
_MAX_V2_RGB_SPLIT = 5
_MAX_V2_BRIGHTNESS_DELTA = 25

_MAX_V2_MOIRE_OPACITY = 0.08
_MAX_V2_EDGE_INTENSITY = 0.45
_MAX_V2_RGB_R: tuple[int, int] = (5, 1)
_MAX_V2_RGB_B: tuple[int, int] = (-5, -1)
_MAX_V2_WM_OPACITY = 0.55
_MAX_V2_WM_RGB_SPLIT = 4
_MAX_V2_WM_BRIGHTNESS_DELTA = 22
_MAX_V2_FACE_WARP_AMP = 3.5
_MAX_V2_EYE_DISPLACEMENT = 2.5
_MAX_V2_EYE_IRIS_HUE = 10
_MAX_V2_EYE_RADIUS_RATIO = 0.15
_MAX_V2_BLOB_COUNT = 3
_MAX_V2_BLOB_SIZE_RATIO = 0.28
_MAX_V2_BLOB_HUE_RANGE: tuple[int, int] = (40, 70)
_MAX_V2_BLOB_SATURATION = 1.4
_MAX_V2_BLOB_ROUGHNESS = 8
_MAX_V2_BLOB_FEATHER = 6

# ----- Ultimate COLOR mode — reduced green/magenta artifacts ----
_UC_MICROTEXT_OPACITY = 0.10
_UC_WATERMARK_OPACITY = 0.30
_UC_EDGE_INTENSITY = 0.12
_UC_RGB_R: tuple[int, int] = (3, 1)
_UC_RGB_B: tuple[int, int] = (-3, -1)
_UC_TRIPLE_WM_OPACITY = 0.30
_UC_TRIPLE_WM_BRIGHTNESS = 10
_UC_BLOB_COUNT = 1
_UC_BLOB_SIZE_RATIO = 0.15
_UC_BLOB_HUE_RANGE: tuple[int, int] = (90, 130)
_UC_BLOB_SATURATION = 1.15
_UC_BLOB_ROUGHNESS = 8
_UC_BLOB_FEATHER = 10

# ----- Ultimate GRAYSCALE mode — structural/luminance attacks ----
_UG_MICROTEXT_OPACITY = 0.12
_UG_WATERMARK_OPACITY = 0.35
_UG_EDGE_INTENSITY = 0.18
_UG_EDGE_LUMA_SHIFT = 30
_UG_MOIRE_OPACITY = 0.15
_UG_FACE_WARP_AMP = 4.0
_UG_EYE_DISPLACEMENT = 3.0
_UG_STROKE_COUNT = 60
_UG_STROKE_DARKNESS = 50
_UG_LUMA_INV_PATCHES = 80
_UG_LUMA_INV_STRENGTH = 18

# ----- Shared ultimate constants ----
_ULTIMATE_FALLBACK_TEXT = "Preview Only - All Rights Reserved"
_ULTIMATE_SIGNATURE_FONT_RATIO = 0.04
_ULTIMATE_SIGNATURE_PADDING_RATIO = 0.025
_ULTIMATE_SIGNATURE_DEPTH = 2
_ULTIMATE_BLUR_BAR_SIGMA = 12
_ULTIMATE_BLUR_BAR_WIDTH_RATIO = 0.80
_ULTIMATE_BLUR_BAR_HEIGHT_RATIO = 0.07

# ----- Stealth (社媒) mode — invisible frequency-domain attacks only --------
# No visible watermark, no text overlay, no blobs — just hue/geometry/moire
# perturbations that are nearly invisible to humans but make AI edits
# produce blurred, color-shifted, or structurally wrong results.
_STEALTH_MOIRE_OPACITY = 0.04
_STEALTH_EDGE_INTENSITY = 0.10
_STEALTH_FACE_WARP_AMP = 0.8
_STEALTH_EYE_DISPLACEMENT = 0.8
_STEALTH_EYE_IRIS_HUE = 4
_STEALTH_EYE_RADIUS_RATIO = 0.10

# The stealth surface stacks several near-invisible adversarial layers, each
# allocating full-resolution float buffers. On large images this peaks at
# hundreds of MB and can exhaust the system memory-commit limit. Since the
# surface is low-amplitude perturbation, we compute it on a downscaled copy
# above this dimension and upscale only the resulting delta back onto the
# full-resolution image — keeping the base photo and the visible layers
# (drawn afterwards at full res) sharp while bounding peak memory.
STEALTH_MAX_COMPUTE_DIM = 1600
_STEALTH_MAX_COMPUTE_DIM = STEALTH_MAX_COMPUTE_DIM


def _is_grayscale(image: np.ndarray) -> bool:
    """Detect if an image is effectively grayscale (R ≈ G ≈ B)."""
    if image.ndim != 3 or image.shape[2] != 3:
        return False
    diff_rg = np.abs(image[:, :, 0].astype(np.int16) - image[:, :, 1].astype(np.int16))
    diff_rb = np.abs(image[:, :, 0].astype(np.int16) - image[:, :, 2].astype(np.int16))
    mean_diff = (np.mean(diff_rg) + np.mean(diff_rb)) / 2.0
    return mean_diff < 5.0


def _validate_rgb_uint8(image: np.ndarray) -> None:
    """與各 M 模組一致：uint8、HxWx3、至少 8×8。"""
    if image.dtype != np.uint8:
        raise ValueError(
            f"Input dtype must be uint8, got {image.dtype}. "
            "Convert to uint8 RGB before calling protect_image."
        )
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(
            f"Input must be an HxWx3 RGB array, got shape {image.shape}."
        )
    h, w = image.shape[:2]
    if h < 8 or w < 8:
        raise ValueError(
            f"Image dimensions must be at least 8×8, got {h}×{w}."
        )


def _validate_level(level: str) -> Level:
    if level not in _LEVELS:
        raise ValueError(
            f"level must be one of {sorted(_LEVELS)!r}, got {level!r}."
        )
    return level  # type: ignore[return-value]


def _maybe_warn_visible_only_strong(level: Level, visible_watermark_text: str) -> None:
    if level != "strong" and visible_watermark_text.strip():
        warnings.warn(
            f"Visible watermark requires level='strong'; ignored at level={level!r}.",
            UserWarning,
            stacklevel=3,
        )


def protect_image(
    image: np.ndarray,
    level: Level = "standard",
    watermark_text: str = "",
    visible_watermark_text: str = "",
    seed: int = 42,
    *,
    delivery_mode: bool = False,
    protection_mode: ProtectionMode | None = None,
    delivery_text: str = "",
    poison_commands: list[str] | None = None,
    face_shield: bool = False,
    artist_signature: str = "",
    artist_signature_position: SignaturePosition = "bottom_right",
    blur_bar: bool = False,
    blur_bar_text: str = "",
    blur_bar_position: str = "below_face",
    blur_bar_sigma: int = 12,
    emboss: bool = False,
    emboss_pattern: str = "diagonal",
    emboss_intensity: float = 0.28,
    emboss_text: str = "",
    emboss_text_density: str = "normal",
    emboss_strength: str | None = None,
    displacement: bool = False,
    displacement_text: str = "",
    displacement_shift: int = 10,
    displacement_density: str = "normal",
    displacement_font_ratio: float = 0.15,
    displacement_mode: str = "scatter",
    displacement_seed: int = 42,
    displacement_shadow: bool = False,
    displacement_shadow_strength: float = 0.35,
    displacement_anchor_x: float = -1.0,
    displacement_anchor_y: float = -1.0,
    face_emboss_text: str = "",
    face_emboss_copies: int = 0,
    face_emboss_seed: int = 42,
    face_emboss_patch_ratio: float = 0.30,
    face_emboss_shift: int = 12,
    face_emboss_opacity: float = 0.25,
    dwt_payload: str = "",
    blur_bar_count: int = 1,
    blur_bar_y_ratio: float = -1.0,
    blur_region_mask: np.ndarray | None = None,
    stealth_surface: bool = True,
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
    halftone_background_chain: int = 50,
    halftone_contour_warp: int = 50,
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
    """依強度預設對 **uint8 RGB** 影像套用 M1–M7（不含 M10）。

    Parameters
    ----------
    image:
        ``uint8`` ndarray，shape ``(H, W, 3)``，H、W 至少 8。
    level:
        ``'light'`` | ``'standard'`` | ``'strong'`` — 模組與強度見模組 docstring
        與 PRD §6.4。僅在 ``delivery_mode=False`` 時使用。
    watermark_text:
        非空（strip 後）則最後套用 **M4** LSB 嵌入；否則跳過 M4。
        **在 delivery_mode=True 時忽略**（LSB 不適合交付場景）。
    visible_watermark_text:
        見模組頂部 **M5 OPTION A**：僅 ``strong`` 且 strip 後非空時套用 M5。
    seed:
        底層隨機種子。
    delivery_mode:
        ``True`` 時跳過 M1–M7，改為交付保護疊加。
    protection_mode:
        僅 ``delivery_mode=True`` 有效。
    delivery_text:
        微字與/或可見水印共用文字；空字串時 microtext 使用模組內預設。
    poison_commands:
        自訂注入指令列表（僅 poison_instruction / poison_full 使用）。
        ``None`` 時使用 ``instruction_injection`` 模組內建預設。
    face_shield:
        ``True`` 時在 delivery 保護疊加後，額外對臉部區域施加局部干擾。
        **僅在 ``delivery_mode=True`` 時生效**；``delivery_mode=False`` 時忽略。

    Returns
    -------
    np.ndarray
        處理後 **uint8 RGB**，shape 與輸入相同。

    Raises
    ------
    ValueError
        輸入格式不合法，或 delivery watermark 文字為空。
    """
    _validate_rgb_uint8(image)

    if delivery_mode:
        user_text = delivery_text.strip()
        microtext_resolved = user_text if user_text else DEFAULT_DELIVERY_MICROTEXT

        out = image.copy()
        _visible_upscale_to: tuple[int, int] | None = None
        _visible_full_base: np.ndarray | None = None
        _visible_ref_base: np.ndarray | None = None
        _visible_ref_side: int | None = None
        # 半调/波点按 1280 标定；优先于 stealth 1600，便于常见 2×/3× 整数放大
        if halftone_enabled and halftone_text.strip():
            from core.halftone_protect import HALFTONE_REF_LONG_SIDE

            _visible_ref_side = HALFTONE_REF_LONG_SIDE
        elif protection_mode in ("stealth", "credit") and stealth_surface:
            _visible_ref_side = _STEALTH_MAX_COMPUTE_DIM

        if _visible_ref_side is not None:
            import cv2

            _oh, _ow = out.shape[:2]
            if max(_oh, _ow) > _visible_ref_side * 1.05:
                _visible_full_base = out.copy()
                _sc = _visible_ref_side / max(_oh, _ow)
                _dw = max(64, int(round(_ow * _sc)))
                _dh = max(64, int(round(_oh * _sc)))
                out = cv2.resize(out, (_dw, _dh), interpolation=cv2.INTER_AREA)
                _visible_ref_base = out.copy()
                _visible_upscale_to = (_ow, _oh)

        if protection_mode == "microtext":
            out = apply_microtext_overlay(
                out, microtext_resolved,
                opacity=_DELIVERY_MICROTEXT_OPACITY, seed=seed,
            )
        elif protection_mode == "watermark":
            if not user_text:
                raise ValueError("delivery_text required for watermark mode")
            out = apply_visible_watermark(
                out, user_text,
                opacity=_DELIVERY_WATERMARK_OPACITY,
                density=_DELIVERY_WATERMARK_DENSITY,
            )
        elif protection_mode == "hybrid":
            if not user_text:
                raise ValueError("delivery_text required for hybrid mode (watermark layer)")
            out = apply_microtext_overlay(
                out, microtext_resolved,
                opacity=_DELIVERY_MICROTEXT_OPACITY, seed=seed,
            )
            out = apply_visible_watermark(
                out, user_text,
                opacity=_DELIVERY_WATERMARK_OPACITY,
                density=_DELIVERY_WATERMARK_DENSITY,
            )
        elif protection_mode == "poison_semantic":
            out = apply_semantic_injection(
                out,
                opacity=_POISON_SEMANTIC_OPACITY,
                patch_count=_POISON_SEMANTIC_PATCH_COUNT,
                seed=seed,
            )
        elif protection_mode == "poison_instruction":
            resolved_commands = poison_commands if poison_commands else None
            out = apply_instruction_injection(
                out,
                commands=resolved_commands,
                contrast_delta=_POISON_INSTRUCTION_CONTRAST,
                opacity=_POISON_INSTRUCTION_OPACITY,
                seed=seed,
            )
        elif protection_mode == "poison_full":
            out = apply_semantic_injection(
                out,
                opacity=_POISON_SEMANTIC_OPACITY,
                patch_count=_POISON_SEMANTIC_PATCH_COUNT,
                seed=seed,
            )
            resolved_commands = poison_commands if poison_commands else None
            out = apply_instruction_injection(
                out,
                commands=resolved_commands,
                contrast_delta=_POISON_INSTRUCTION_CONTRAST,
                opacity=_POISON_INSTRUCTION_OPACITY,
                seed=seed,
            )
        elif protection_mode == "framed_canvas":
            from core.framed_canvas import apply_framed_canvas
            out = apply_framed_canvas(out, border_text=delivery_text or "", seed=seed)
            return out
        elif protection_mode == "jumping_moire":
            from core.jumping_moire import apply_jumping_moire
            out = apply_jumping_moire(out, opacity=_DELIVERY_MOIRE_OPACITY, seed=seed)
        elif protection_mode == "jumping_moire_plus":
            from core.jumping_moire import apply_jumping_moire
            from core.rgb_offset import apply_rgb_offset
            out = apply_jumping_moire(out, opacity=_DELIVERY_MOIRE_PLUS_OPACITY, seed=seed)
            out = apply_rgb_offset(
                out,
                r_shift=_DELIVERY_RGB_OFFSET_R,
                b_shift=_DELIVERY_RGB_OFFSET_B,
                seed=seed,
            )
        elif protection_mode == "max_protection":
            from core.jumping_moire import apply_jumping_moire
            from core.edge_corruption import apply_edge_corruption
            from core.rgb_offset import apply_rgb_offset
            from core.triple_watermark import apply_triple_watermark
            out = apply_jumping_moire(out, opacity=_MAX_MOIRE_OPACITY, seed=seed)
            out = apply_edge_corruption(out, intensity=_MAX_EDGE_INTENSITY, seed=seed)
            out = apply_rgb_offset(
                out,
                r_shift=_MAX_RGB_R,
                b_shift=_MAX_RGB_B,
                seed=seed,
            )
            out = apply_triple_watermark(out, opacity=_MAX_TRIPLE_OPACITY, seed=seed)
        elif protection_mode == "max_protection_v2":
            from core.face_geometry_warp import apply_face_geometry_warp
            from core.face_eye_disruption import apply_face_eye_disruption
            from core.jumping_moire import apply_jumping_moire
            from core.edge_corruption import apply_edge_corruption
            from core.rgb_offset import apply_rgb_offset
            from core.triple_watermark_v2 import apply_triple_watermark_v2
            from core.face_blob_disruption import apply_face_blob_disruption
            out = apply_face_geometry_warp(
                out,
                warp_amplitude=_MAX_V2_FACE_WARP_AMP,
                seed=seed,
            )
            out = apply_face_eye_disruption(
                out,
                eye_radius_ratio=_MAX_V2_EYE_RADIUS_RATIO,
                displacement_px=_MAX_V2_EYE_DISPLACEMENT,
                iris_hue_shift=_MAX_V2_EYE_IRIS_HUE,
                seed=seed,
            )
            if _MAX_V2_MOIRE_OPACITY > 0:
                out = apply_jumping_moire(
                    out, opacity=_MAX_V2_MOIRE_OPACITY, seed=seed
                )
            out = apply_edge_corruption(
                out, intensity=_MAX_V2_EDGE_INTENSITY, seed=seed
            )
            out = apply_rgb_offset(
                out,
                r_shift=_MAX_V2_RGB_R,
                b_shift=_MAX_V2_RGB_B,
                seed=seed,
            )
            out = apply_triple_watermark_v2(
                out,
                opacity=_MAX_V2_WM_OPACITY,
                rgb_split_offset=_MAX_V2_WM_RGB_SPLIT,
                brightness_delta=_MAX_V2_WM_BRIGHTNESS_DELTA,
                use_adaptive_colors=False,
                content_aware=True,
                seed=seed,
            )
            out = apply_face_blob_disruption(
                out,
                n_blobs=_MAX_V2_BLOB_COUNT,
                blob_size_ratio=_MAX_V2_BLOB_SIZE_RATIO,
                hue_shift_range=_MAX_V2_BLOB_HUE_RANGE,
                saturation_boost=_MAX_V2_BLOB_SATURATION,
                edge_roughness=_MAX_V2_BLOB_ROUGHNESS,
                feather_px=_MAX_V2_BLOB_FEATHER,
                seed=seed,
            )
        elif protection_mode in ("ultimate", "ultimate_color"):
            # ── ULTIMATE · COLOR ─────────────────────────────────
            from core.face_geometry_warp import apply_face_geometry_warp
            from core.face_eye_disruption import apply_face_eye_disruption
            from core.jumping_moire import apply_jumping_moire
            from core.edge_corruption import apply_edge_corruption
            from core.rgb_offset import apply_rgb_offset
            from core.triple_watermark_v2 import apply_triple_watermark_v2
            from core.face_blob_disruption import apply_face_blob_disruption
            from core.artist_emboss import apply_artist_emboss_signature
            from core.detail_mask import compute_detail_mask

            wm_text = user_text or _ULTIMATE_FALLBACK_TEXT
            dmask = compute_detail_mask(out)

            out = apply_microtext_overlay(
                out, microtext_resolved,
                opacity=_UC_MICROTEXT_OPACITY, seed=seed,
            )
            out = apply_visible_watermark(
                out, wm_text,
                opacity=_UC_WATERMARK_OPACITY,
                density=_DELIVERY_WATERMARK_DENSITY,
            )
            out = apply_face_geometry_warp(
                out, warp_amplitude=_MAX_V2_FACE_WARP_AMP, seed=seed,
            )
            out = apply_face_eye_disruption(
                out,
                eye_radius_ratio=_MAX_V2_EYE_RADIUS_RATIO,
                displacement_px=_MAX_V2_EYE_DISPLACEMENT,
                iris_hue_shift=_MAX_V2_EYE_IRIS_HUE,
                seed=seed,
            )
            out = apply_jumping_moire(
                out, opacity=_STEALTH_MOIRE_OPACITY, seed=seed,
            )
            out = apply_edge_corruption(
                out, intensity=_UC_EDGE_INTENSITY, seed=seed,
            )
            out = apply_rgb_offset(
                out,
                r_shift=_UC_RGB_R,
                b_shift=_UC_RGB_B,
                seed=seed,
                detail_mask=dmask,
            )
            out = apply_triple_watermark_v2(
                out,
                opacity=_UC_TRIPLE_WM_OPACITY,
                rgb_split_offset=_MAX_V2_WM_RGB_SPLIT,
                brightness_delta=_UC_TRIPLE_WM_BRIGHTNESS,
                use_adaptive_colors=False,
                content_aware=True,
                seed=seed,
            )
            out = apply_face_blob_disruption(
                out,
                n_blobs=_UC_BLOB_COUNT,
                blob_size_ratio=_UC_BLOB_SIZE_RATIO,
                hue_shift_range=_UC_BLOB_HUE_RANGE,
                saturation_boost=_UC_BLOB_SATURATION,
                edge_roughness=_UC_BLOB_ROUGHNESS,
                feather_px=_UC_BLOB_FEATHER,
                seed=seed,
            )
            sig_text = (artist_signature or "").strip()
            if sig_text:
                out = apply_artist_emboss_signature(
                    out,
                    artist_name=sig_text,
                    position=artist_signature_position,
                    font_size_ratio=_ULTIMATE_SIGNATURE_FONT_RATIO,
                    padding_ratio=_ULTIMATE_SIGNATURE_PADDING_RATIO,
                    emboss_depth=_ULTIMATE_SIGNATURE_DEPTH,
                    seed=seed,
                )
            if blur_bar:
                from core.blur_bar import apply_blur_bar
                out = apply_blur_bar(
                    out,
                    text=blur_bar_text,
                    position=blur_bar_position,  # type: ignore[arg-type]
                    blur_sigma=blur_bar_sigma,
                    width_ratio=_ULTIMATE_BLUR_BAR_WIDTH_RATIO,
                    height_ratio=_ULTIMATE_BLUR_BAR_HEIGHT_RATIO,
                    seed=seed,
                )
        elif protection_mode == "ultimate_grayscale":
            # ── ULTIMATE · GRAYSCALE ─────────────────────────────
            from core.face_geometry_warp import apply_face_geometry_warp
            from core.face_eye_disruption import apply_face_eye_disruption
            from core.jumping_moire import apply_jumping_moire
            from core.edge_corruption import apply_edge_corruption
            from core.luminance_inversion import apply_luminance_inversion
            from core.face_stroke_injection import apply_face_stroke_injection
            from core.artist_emboss import apply_artist_emboss_signature

            wm_text = user_text or _ULTIMATE_FALLBACK_TEXT

            out = apply_microtext_overlay(
                out, microtext_resolved,
                opacity=_UG_MICROTEXT_OPACITY, seed=seed,
                adaptive_contrast=True,
            )
            out = apply_visible_watermark(
                out, wm_text,
                opacity=_UG_WATERMARK_OPACITY,
                density=_DELIVERY_WATERMARK_DENSITY,
            )
            out = apply_face_geometry_warp(
                out, warp_amplitude=_UG_FACE_WARP_AMP, seed=seed,
            )
            out = apply_face_eye_disruption(
                out,
                eye_radius_ratio=_MAX_V2_EYE_RADIUS_RATIO,
                displacement_px=_UG_EYE_DISPLACEMENT,
                iris_hue_shift=0,
                seed=seed,
            )
            out = apply_jumping_moire(
                out, opacity=_UG_MOIRE_OPACITY, seed=seed,
            )
            out = apply_edge_corruption(
                out, intensity=_UG_EDGE_INTENSITY,
                grayscale_mode=True, luma_shift=_UG_EDGE_LUMA_SHIFT,
                seed=seed,
            )
            out = apply_luminance_inversion(
                out,
                n_patches=_UG_LUMA_INV_PATCHES,
                strength=_UG_LUMA_INV_STRENGTH,
                seed=seed,
            )
            out = apply_face_stroke_injection(
                out,
                n_strokes=_UG_STROKE_COUNT,
                stroke_length_range=(4, 20),
                stroke_width_range=(1, 3),
                brightness_threshold=130,
                darkness=_UG_STROKE_DARKNESS,
                seed=seed,
            )
            sig_text = (artist_signature or "").strip()
            if sig_text:
                out = apply_artist_emboss_signature(
                    out,
                    artist_name=sig_text,
                    position=artist_signature_position,
                    font_size_ratio=_ULTIMATE_SIGNATURE_FONT_RATIO,
                    padding_ratio=_ULTIMATE_SIGNATURE_PADDING_RATIO,
                    emboss_depth=_ULTIMATE_SIGNATURE_DEPTH,
                    seed=seed,
                )
            if blur_bar:
                from core.blur_bar import apply_blur_bar
                out = apply_blur_bar(
                    out,
                    text=blur_bar_text,
                    position=blur_bar_position,  # type: ignore[arg-type]
                    blur_sigma=blur_bar_sigma,
                    width_ratio=_ULTIMATE_BLUR_BAR_WIDTH_RATIO,
                    height_ratio=_ULTIMATE_BLUR_BAR_HEIGHT_RATIO,
                    seed=seed,
                )
        elif protection_mode in ("stealth", "credit"):
            if stealth_surface:
                import cv2

                from core.face_geometry_warp import apply_face_geometry_warp
                from core.face_eye_disruption import apply_face_eye_disruption
                from core.perlin_structural_noise import apply_perlin_structural_noise
                from core.jumping_moire import apply_jumping_moire
                from core.luminance_inversion import apply_luminance_inversion

                # Bound peak memory on large images: compute the (low-amplitude)
                # stealth surface on a downscaled copy, then upscale only the
                # delta back onto the full-resolution image.
                _stealth_full = out
                _sh, _sw = out.shape[:2]
                _stealth_downscaled = max(_sh, _sw) > _STEALTH_MAX_COMPUTE_DIM
                if _stealth_downscaled:
                    _sc = _STEALTH_MAX_COMPUTE_DIM / max(_sh, _sw)
                    _dw = max(64, int(round(_sw * _sc)))
                    _dh = max(64, int(round(_sh * _sc)))
                    out = cv2.resize(out, (_dw, _dh), interpolation=cv2.INTER_AREA)
                    _stealth_base = out.copy()

                is_gray = _is_grayscale(out)

                # Layer 0 (color): microtext as structural base layer
                # — pollutes the frequency domain; raised to 0.06 for stronger
                # high-freq disruption while remaining below perceptual threshold.
                if not is_gray:
                    out = apply_microtext_overlay(
                        out, DEFAULT_DELIVERY_MICROTEXT,
                        opacity=0.06, seed=seed,
                    )

                # Layer 1-2: face identity attacks
                _warp_amp = 0.6 if is_gray else _STEALTH_FACE_WARP_AMP
                _eye_disp = 0.6 if is_gray else _STEALTH_EYE_DISPLACEMENT
                out = apply_face_geometry_warp(
                    out, warp_amplitude=_warp_amp, seed=seed,
                )
                out = apply_face_eye_disruption(
                    out,
                    eye_radius_ratio=_STEALTH_EYE_RADIUS_RATIO,
                    displacement_px=_eye_disp,
                    iris_hue_shift=0 if is_gray else _STEALTH_EYE_IRIS_HUE,
                    seed=seed,
                )
                # Layer 3: moire — subtle VAE frequency disruption
                _moire_op = 0.04 if is_gray else _STEALTH_MOIRE_OPACITY
                out = apply_jumping_moire(
                    out, opacity=_moire_op, seed=seed,
                )
                # Layer 4: low-intensity edge corruption — adds faint hue-shifted
                # ghost edges parallel to real edges.  At intensity 0.10 the
                # ghosts are nearly invisible to humans but pollute the edge map
                # that ControlNet / img2img relies on.  Does NOT alter the
                # geometry of existing lines.
                from core.edge_corruption import apply_edge_corruption
                _edge_int = 0.06 if is_gray else _STEALTH_EDGE_INTENSITY
                out = apply_edge_corruption(
                    out, intensity=_edge_int,
                    grayscale_mode=is_gray,
                    luma_shift=15,
                    seed=seed,
                )
                # Layer 5.5: luminance inversion — subtle local brightness flips
                _luma_patches = 12 if is_gray else 20
                _luma_strength = 6 if is_gray else 8
                out = apply_luminance_inversion(
                    out, n_patches=_luma_patches,
                    strength=_luma_strength, seed=seed,
                )
                # Layer 5.8: Perlin structural noise — low-frequency edge-aware
                # noise that survives JPEG compression.
                _perlin_strength = 0.15 if is_gray else 0.25
                out = apply_perlin_structural_noise(
                    out,
                    strength=_perlin_strength,
                    seed=seed,
                )
                # Layer 6 (optional): blur bar with hue pollution. Skipped on the
                # downscaled path — a blur bar is a region replacement (not an
                # additive perturbation), so it cannot be carried through the
                # delta; the full-resolution blur bar later in the pipeline
                # renders it correctly.
                if blur_bar and not _stealth_downscaled:
                    from core.blur_bar import apply_blur_bar
                    out = apply_blur_bar(
                        out,
                        text=blur_bar_text,
                        position=blur_bar_position,  # type: ignore[arg-type]
                        blur_sigma=blur_bar_sigma,
                        width_ratio=_ULTIMATE_BLUR_BAR_WIDTH_RATIO,
                        height_ratio=_ULTIMATE_BLUR_BAR_HEIGHT_RATIO,
                        seed=seed,
                    )

                if _stealth_downscaled:
                    delta = out.astype(np.float32) - _stealth_base.astype(np.float32)
                    delta_full = cv2.resize(
                        delta, (_sw, _sh), interpolation=cv2.INTER_LINEAR,
                    )
                    out = np.clip(
                        _stealth_full.astype(np.float32) + delta_full, 0, 255,
                    ).astype(np.uint8)
            # stealth_surface=False: invisible JW only — pass image through unchanged
        elif protection_mode == "face_emboss_lock":
            from core.face_emboss_lock import apply_face_emboss_lock
            out = apply_face_emboss_lock(
                out,
                shift_px=face_emboss_shift,
                opacity=face_emboss_opacity,
                chromatic_shift=3,
                seed=face_emboss_seed,
                emboss_text=face_emboss_text,
                n_copies=face_emboss_copies,
                patch_ratio=face_emboss_patch_ratio,
            )
        else:
            raise ValueError(
                "protection_mode must be one of 'microtext', 'watermark', 'hybrid', "
                "'poison_semantic', 'poison_instruction', 'poison_full', "
                "'framed_canvas', 'jumping_moire', 'jumping_moire_plus', "
                "'max_protection', 'max_protection_v2', 'ultimate', "
                "'ultimate_color', 'ultimate_grayscale', 'stealth', 'credit', "
                "'face_emboss_lock', "
                f"got {protection_mode!r}."
            )

        if face_shield:
            from core.face_shield import apply_face_shield
            out = apply_face_shield(out, seed=seed)

        # Artist signature — available for all modes
        sig_text = (artist_signature or "").strip()
        if sig_text and not protection_mode.startswith("ultimate"):
            from core.artist_emboss import apply_artist_emboss_signature
            out = apply_artist_emboss_signature(
                out,
                artist_name=sig_text,
                position=artist_signature_position,
                font_size_ratio=_ULTIMATE_SIGNATURE_FONT_RATIO,
                padding_ratio=_ULTIMATE_SIGNATURE_PADDING_RATIO,
                emboss_depth=_ULTIMATE_SIGNATURE_DEPTH,
                seed=seed,
            )

        # Add-on blur bar with count and custom position support
        if blur_bar and not protection_mode.startswith("ultimate"):
            if blur_region_mask is not None:
                from core.blur_bar import apply_blur_bar_from_mask
                out = apply_blur_bar_from_mask(
                    out,
                    blur_region_mask,
                    text=blur_bar_text,
                    blur_sigma=blur_bar_sigma,
                    seed=seed,
                )
            else:
                from core.blur_bar import apply_blur_bar
                _bar_count = max(1, min(blur_bar_count, 3))
                for bar_i in range(_bar_count):
                    _pos = blur_bar_position
                    _y = 0.5
                    if blur_bar_y_ratio >= 0:
                        _pos = "custom"
                        _y = blur_bar_y_ratio
                        if _bar_count > 1:
                            spread = 0.15
                            _y = blur_bar_y_ratio + (bar_i - (_bar_count - 1) / 2) * spread
                            _y = max(0.0, min(1.0, _y))
                    out = apply_blur_bar(
                        out,
                        text=blur_bar_text,
                        position=_pos,
                        y_ratio=_y,
                        blur_sigma=blur_bar_sigma,
                        seed=seed + bar_i * 17,
                    )

        if halftone_enabled and halftone_text.strip():
            from core.halftone_protect import (
                HALFTONE_REF_LONG_SIDE,
                apply_halftone_protect,
            )

            # 可见层已在 ref 分辨率跑完；半调不再二次降采样
            _ht_render_side = HALFTONE_REF_LONG_SIDE
            out = apply_halftone_protect(
                out,
                style=halftone_style,  # type: ignore[arg-type]
                author_text=halftone_text.strip(),
                size=halftone_size,
                density=halftone_density,
                visibility=halftone_visibility,
                anchor_x=halftone_anchor_x,
                anchor_y=halftone_anchor_y,
                signature=halftone_signature,
                signature_size=halftone_signature_size,
                dot_texture=halftone_dot_texture,
                background_chain=halftone_background_chain,
                contour_warp=halftone_contour_warp,
                render_long_side=_ht_render_side,
                credit_faint=halftone_credit_faint,
            )

        if emboss:
            from core.emboss_texture import apply_emboss_texture
            out = apply_emboss_texture(
                out,
                pattern=emboss_pattern,
                intensity=emboss_intensity,
                text=emboss_text,
                text_density=emboss_text_density,
                seed=seed,
                emboss_strength=emboss_strength,
            )

        if displacement and displacement_text.strip():
            from core.displacement_watermark import apply_displacement_watermark
            out = apply_displacement_watermark(
                out,
                text=displacement_text.strip(),
                shift_px=displacement_shift,
                font_size_ratio=displacement_font_ratio,
                density=displacement_density,
                mode=displacement_mode,
                seed=displacement_seed,
                shadow_enabled=displacement_shadow,
                shadow_strength=float(displacement_shadow_strength),
                anchor_x=displacement_anchor_x,
                anchor_y=displacement_anchor_y,
            )

        if face_emboss_copies > 0:
            from core.face_emboss_lock import apply_face_emboss_lock
            out = apply_face_emboss_lock(
                out,
                shift_px=face_emboss_shift,
                opacity=face_emboss_opacity,
                chromatic_shift=3,
                seed=face_emboss_seed,
                emboss_text=face_emboss_text,
                n_copies=face_emboss_copies,
                patch_ratio=face_emboss_patch_ratio,
            )

        # Displacement logo — silhouette pushes host pixels (dog-style), not a paste.
        if logo_rgba is not None:
            from core.displacement_watermark import apply_displacement_logo

            out = apply_displacement_logo(
                out,
                logo_rgba,
                scale=logo_scale,
                position=logo_position,
                anchor_x=logo_anchor_x,
                anchor_y=logo_anchor_y,
                shift_px=int(logo_shift_px),
                shadow_enabled=True,
                shadow_strength=float(logo_opacity),
            )

        # DWT frequency-domain watermark — survives JPEG/screenshot/social media
        if dwt_payload.strip():
            from core.dwt_watermark import embed_dwt_watermark
            out = embed_dwt_watermark(out, payload_text=dwt_payload.strip())

        # LSB watermark — available for all modes
        if watermark_text.strip():
            out = embed_lsb_watermark(out, watermark_text)

        if _visible_upscale_to is not None:
            import cv2

            _tw, _th = _visible_upscale_to
            _rh, _rw = out.shape[:2]
            _sx, _sy = _tw / _rw, _th / _rh
            _int_scale = (
                abs(_sx - round(_sx)) < 0.02
                and abs(_sy - round(_sy)) < 0.02
            )
            if _int_scale:
                out = cv2.resize(out, (_tw, _th), interpolation=cv2.INTER_NEAREST)
            elif _visible_full_base is not None and _visible_ref_base is not None:
                _delta = out.astype(np.float32) - _visible_ref_base.astype(np.float32)
                _delta_full = cv2.resize(
                    _delta, (_tw, _th), interpolation=cv2.INTER_CUBIC,
                )
                out = np.clip(
                    _visible_full_base.astype(np.float32) + _delta_full, 0, 255,
                ).astype(np.uint8)
            else:
                out = cv2.resize(out, (_tw, _th), interpolation=cv2.INTER_CUBIC)

        return out

    # --- existing pipeline (delivery_mode=False) ---
    lvl = _validate_level(level)
    _maybe_warn_visible_only_strong(lvl, visible_watermark_text)

    out = image.copy()

    # M7
    if lvl == "standard":
        out = apply_gradient_disturbance(out, strength=0.3, seed=seed + 0)
    elif lvl == "strong":
        out = apply_gradient_disturbance(out, strength=0.6, seed=seed + 0)

    # M1
    if lvl == "light":
        out = apply_dct_perturbation(out, strength=0.3, seed=seed + 1)
    elif lvl == "standard":
        out = apply_dct_perturbation(out, strength=0.5, seed=seed + 1)
    else:
        out = apply_dct_perturbation(out, strength=0.8, seed=seed + 1)

    # M2
    if lvl == "standard":
        out = apply_adaptive_noise(out, strength=0.3, seed=seed + 2)
    elif lvl == "strong":
        out = apply_adaptive_noise(out, strength=0.6, seed=seed + 2)

    # M3
    out = apply_blue_channel_perturbation(out, strength=0.5, seed=seed + 3)

    # M6
    if lvl == "standard":
        out = apply_texture_pollution(
            out, texture_type="moire", opacity=0.05, seed=seed + 4,
        )
    elif lvl == "strong":
        out = apply_texture_pollution(
            out, texture_type="moire", opacity=0.08, seed=seed + 4,
        )

    # M5
    if lvl == "strong" and visible_watermark_text.strip():
        out = apply_visible_watermark(
            out, visible_watermark_text, opacity=0.1, density="normal",
        )

    # M4
    if watermark_text.strip():
        out = embed_lsb_watermark(out, watermark_text)

    return out


def protect_image_file(
    input_path: str,
    output_path: str,
    level: Level = "standard",
    watermark_text: str = "",
    visible_watermark_text: str = "",
    artist: str = "",
    embed_metadata: bool = True,
    seed: int = 42,
    *,
    delivery_mode: bool = False,
    protection_mode: ProtectionMode | None = None,
    delivery_text: str = "",
    poison_commands: list[str] | None = None,
    face_shield: bool = False,
    artist_signature: str = "",
    artist_signature_position: SignaturePosition = "bottom_right",
    blur_bar: bool = False,
    blur_bar_text: str = "",
    blur_bar_position: str = "below_face",
    blur_bar_sigma: int = 12,
    emboss: bool = False,
    emboss_pattern: str = "diagonal",
    emboss_intensity: float = 0.28,
    emboss_text: str = "",
    emboss_text_density: str = "normal",
    emboss_strength: str | None = None,
    displacement: bool = False,
    displacement_text: str = "",
    displacement_shift: int = 10,
    displacement_density: str = "normal",
    displacement_font_ratio: float = 0.15,
    displacement_mode: str = "scatter",
    displacement_seed: int = 42,
    displacement_shadow: bool = False,
    displacement_shadow_strength: float = 0.35,
    displacement_anchor_x: float = -1.0,
    displacement_anchor_y: float = -1.0,
    face_emboss_text: str = "",
    face_emboss_copies: int = 0,
    face_emboss_seed: int = 42,
    face_emboss_patch_ratio: float = 0.30,
) -> None:
    """載入影像 → ``protect_image`` → 儲存 →（可選）M10 合規元數據。

    JPEG 以 **quality=95** 寫出以保持視覺保真（本階段不可設定品質參數）。
    說明：*JPEG saved at quality=95 for visual fidelity.*

    Parameters
    ----------
    input_path:
        來源影像路徑（Pillow 可開啟之格式）。
    output_path:
        輸出路徑；副檔名決定格式（支援至少 ``.png``、``.jpg``、``.jpeg``）。
    level, watermark_text, visible_watermark_text, seed:
        同 ``protect_image``。
    artist:
        寫入 M10 之創作者；當 ``embed_metadata=True`` 時須 **strip 後非空**。
    embed_metadata:
        為 True 時在存檔後呼叫 ``embed_compliance_metadata``。

    Raises
    ------
    ValueError
        ``embed_metadata=True`` 且 ``artist.strip()`` 為空。
    FileNotFoundError
        來源檔不存在（由 Pillow 或 Path 併發生）。
    """
    if embed_metadata and not artist.strip():
        raise ValueError(
            "embed_metadata=True requires a non-empty artist (after strip)."
        )

    in_path = Path(input_path)
    if not in_path.is_file():
        raise FileNotFoundError(f"找不到檔案：{in_path}")

    with Image.open(in_path) as im:
        im = im.convert("RGB")
        arr = np.asarray(im, dtype=np.uint8)

    out = protect_image(
        arr,
        level=level,
        watermark_text=watermark_text,
        visible_watermark_text=visible_watermark_text,
        seed=seed,
        delivery_mode=delivery_mode,
        protection_mode=protection_mode,
        delivery_text=delivery_text,
        poison_commands=poison_commands,
        face_shield=face_shield,
        artist_signature=artist_signature,
        artist_signature_position=artist_signature_position,
        blur_bar=blur_bar,
        blur_bar_text=blur_bar_text,
        blur_bar_position=blur_bar_position,
        blur_bar_sigma=blur_bar_sigma,
        emboss=emboss,
        emboss_pattern=emboss_pattern,
        emboss_intensity=emboss_intensity,
        emboss_text=emboss_text,
        emboss_text_density=emboss_text_density,
        emboss_strength=emboss_strength,
        displacement=displacement,
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
        face_emboss_text=face_emboss_text,
        face_emboss_copies=face_emboss_copies,
        face_emboss_seed=face_emboss_seed,
        face_emboss_patch_ratio=face_emboss_patch_ratio,
    )

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pil_out = Image.fromarray(out)
    suf = out_path.suffix.lower()
    if suf in (".jpg", ".jpeg"):
        pil_out.save(out_path, format="JPEG", quality=95)
    elif suf == ".png":
        pil_out.save(out_path, format="PNG")
    else:
        raise ValueError(
            f"不支援的輸出副檔名 {out_path.suffix!r}，請使用 .png、.jpg 或 .jpeg。"
        )

    if embed_metadata:
        embed_compliance_metadata(out_path, artist=artist.strip())
