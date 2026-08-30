"""Protection API — accepts an image + settings, returns protected image + metrics."""

from __future__ import annotations

import base64
import io
import math
import tempfile
import time
import uuid
import warnings
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import numpy as np
from fastapi import APIRouter, File, Form, Header, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from PIL import Image

from api.error_codes import (
    DISP_TEXT_REQUIRED,
    LOGO_FILE_REQUIRED,
    HOLO_CAPTURE_FAILED,
    HOLO_CAPTURE_UNAVAILABLE,
    OUTPUT_FAILED,
    PREVIEW_FAILED,
    SERVER_ERROR,
)
from api.services.limits import (
    check_image_pixels,
    check_rate_limit,
    check_upload_size,
    rate_limit_preview_per_min,
    rate_limit_protect_per_min,
)
from core.holo_card_export import HoloCaptureError, export_holo_mp4_from_image
from core.pipeline import protect_image
from evaluation.psnr_ssim import evaluate_protection
from ui.handlers import quality_assessment

router = APIRouter(tags=["protect"])


def _resolve_user(authorization: str | None = None):  # noqa: ARG001
    """Self-host edition has no accounts."""
    return None


def record_jw_protect(_user_id: int) -> dict:
    """No Pixel Sea quota on self-host."""
    return {}


def record_protect_success() -> None:
    """No public counters on self-host."""
    return None


_TEMP = Path(tempfile.gettempdir()) / "ai_proof_api"


def _resolve_track_artist(
    *,
    track_artist: str = "",
    artist: str = "",
    dwt_payload: str = "",
    watermark_text: str = "",
    signature_text: str = "",
    halftone_text: str = "",
) -> str:
    """Pick the identity string for 追踪巩固 (independent of JW).

    Uses the explicit ``track_artist`` from the client when set; otherwise the
    first non-empty among the signature fields under 隐性追踪 / 署名, including
    the halftone protection signature when that is the only name entered.
    """
    if track_artist.strip():
        return track_artist.strip()
    for raw in (artist, dwt_payload, watermark_text, signature_text, halftone_text):
        if raw and str(raw).strip():
            return str(raw).strip()
    return ""


def _apply_credit_visible_recipe(
    *,
    mode: str,
    image: np.ndarray,
    halftone_enabled: bool,
    halftone_text: str,
    halftone_visibility: int,
    halftone_signature: int,
    artist: str,
    displacement_enabled: bool,
    displacement_text: str,
    displacement_font_ratio: float,
    displacement_shift: int,
    displacement_shadow: bool,
    displacement_shadow_strength: float,
    visible_mark: str = "auto",
    logo_present: bool = False,
) -> tuple[bool, str, int, int, bool, str, float, int, bool, float, bool]:
    """Apply 署名·快速 defaults; keep caller sliders when the layer is already on."""
    from core.credit_mode import resolve_credit_recipe

    recipe = resolve_credit_recipe(
        mode=mode,
        image=image,
        halftone_enabled=halftone_enabled,
        halftone_text=halftone_text,
        artist=artist,
        displacement_enabled=displacement_enabled,
        displacement_text=displacement_text,
        visible_mark=visible_mark,
        logo_present=logo_present,
    )
    vis = recipe.ascii_visibility if recipe.ascii_visibility is not None else halftone_visibility
    sig = recipe.ascii_signature if recipe.ascii_signature is not None else halftone_signature
    font = recipe.disp_font_ratio if recipe.disp_font_ratio is not None else displacement_font_ratio
    shift = recipe.disp_shift if recipe.disp_shift is not None else displacement_shift
    shadow = recipe.disp_shadow if recipe.disp_shadow is not None else displacement_shadow
    strength = (
        recipe.disp_shadow_strength
        if recipe.disp_shadow_strength is not None
        else displacement_shadow_strength
    )
    return (
        recipe.ascii_enabled,
        recipe.ascii_text,
        vis,
        sig,
        recipe.disp_enabled,
        recipe.disp_text,
        font,
        shift,
        shadow,
        strength,
        recipe.ascii_faint,
    )


def _json_safe_metrics(metrics: dict) -> dict:
    """Make evaluate_protection output JSON-serializable (PSNR may be inf)."""
    safe = dict(metrics)
    psnr = safe.get("psnr")
    if isinstance(psnr, float) and not math.isfinite(psnr):
        safe["psnr"] = None
    mean_diff = safe.get("mean_diff")
    if isinstance(mean_diff, float) and not math.isfinite(mean_diff):
        safe["mean_diff"] = 0.0
    return safe


def _wants_stealth_surface(
    *,
    mode: str,
    is_ultimate: bool,
    blur_bar_enabled: bool,
    emboss_enabled: bool,
    displacement_enabled: bool,
    displacement_text: str = "",
    face_emboss_enabled: bool,
    face_emboss_text: str = "",
    halftone_enabled: bool = False,
    halftone_text: str = "",
) -> bool:
    """Stealth anti-AI surface stack — only when explicit visible attack layers are on."""
    from core.visible_preview import compute_stealth_surface

    if is_ultimate:
        return True
    if mode == "credit":
        return False
    return compute_stealth_surface(
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
_TEMP.mkdir(parents=True, exist_ok=True)


def _read_upload(upload: UploadFile) -> tuple[np.ndarray, np.ndarray | None]:
    """Read upload → (HxWx3 sRGB RGB, optional HxW alpha)."""
    from core.color_profile import decode_upload_pil
    from core.upload_decode import open_upload_image

    data = upload.file.read()
    check_upload_size(len(data))
    img = open_upload_image(data)
    return decode_upload_pil(img)


async def _read_logo_upload(upload: UploadFile | None) -> np.ndarray | None:
    """Optional courtesy-logo file → RGBA, or None if the field was omitted."""
    if upload is None:
        return None
    data = await upload.read()
    if not data:
        return None
    check_upload_size(len(data))
    from core.logo_watermark import decode_logo_bytes

    return decode_logo_bytes(data)


def _bool(v: str | None) -> bool:
    return v is not None and v.lower() in ("true", "1", "yes")


def _validate_image(image_array: np.ndarray) -> None:
    if image_array.dtype != np.uint8 or image_array.ndim != 3 or image_array.shape[2] != 3:
        raise ValueError("图片格式不支持，请上传 RGB 图片")
    h, w = image_array.shape[:2]
    if h < 64 or w < 64:
        raise ValueError("图片太小，请上传至少 64x64 像素的图片")


def _embed_jw_verifiable(
    image: np.ndarray,
    manifest,
    *,
    priority: str = "balanced",
) -> tuple[np.ndarray, bool, str | None]:
    """Embed JW via strength ladder; see core.jingwei_protocol.embed_jw_verifiable."""
    from core.jingwei_protocol import embed_jw_verifiable

    return embed_jw_verifiable(image, manifest, priority=priority)


def _ensure_jw_verifiable_on_output(
    image: np.ndarray,
    manifest,
    *,
    priority: str = "auto",
    embed_timestamp: int | None = None,
) -> tuple[np.ndarray, bool, str | None, str | None]:
    """Embed JW on final RGB: texture-first freq, then LSB backup.

    Returns (image, applied, tier_or_lsb, embed_method).
    embed_method is ``invisible`` | ``lsb`` | None.
    """
    from core.jingwei_protocol import (
        embed_jw_lsb_fallback,
        embed_jw_verifiable,
        extract_jw_from_lsb,
        extract_jw_watermark,
    )

    if extract_jw_watermark(image).get("found"):
        return image, True, None, "invisible"

    lsb_hit = extract_jw_from_lsb(image)
    if lsb_hit and lsb_hit.get("found"):
        return image, True, "lsb", "lsb"

    out, applied, tier = embed_jw_verifiable(
        image, manifest, priority=priority, embed_timestamp=embed_timestamp,
    )
    if applied:
        return out, True, tier, "invisible"

    try:
        out_lsb = embed_jw_lsb_fallback(out, manifest, embed_timestamp=embed_timestamp)
        if extract_jw_from_lsb(out_lsb):
            return out_lsb, True, "lsb", "lsb"
    except Exception:
        pass

    return out, False, tier, None


def _append_jw_embed_status(
    status_msgs: list[str],
    *,
    jw_applied: bool,
    jw_embed_tier: str | None,
    jw_embed_method: str | None,
    source_image: np.ndarray,
    has_visible_declaration: bool,
) -> None:
    from core.jingwei_protocol import estimate_flat_ratio, jw_write_hint_for_image

    if jw_applied and jw_embed_method == "lsb":
        status_msgs.append(
            "本图大色块较多，隐形写入较浅，已改用备用方式在同一张图中留下精卫声明。"
        )
        status_msgs.append("请保存 PNG 原图用于验证。")
    elif jw_applied:
        status_msgs.append(
            "精卫声明已写入；大色块区域已尽量保持原样。请保存 PNG 原图用于验证。",
        )
    else:
        hint = jw_write_hint_for_image(source_image)
        status_msgs.append(
            "暂时无法在本图可靠写入精卫声明。",
        )
        status_msgs.append(hint["suggest"])
        if estimate_flat_ratio(source_image) >= 0.55 and not has_visible_declaration:
            status_msgs.append("建议开启底部白边后重新保护。")


def _run_protection(
    image_array: np.ndarray,
    *,
    mode: str,
    is_ultimate: bool,
    delivery_text: str,
    signature_text: str,
    signature_position: str,
    blur_bar_enabled: bool,
    blur_bar_text: str,
    blur_bar_y_ratio: float,
    blur_bar_sigma: int,
    blur_bar_count: int,
    emboss_enabled: bool,
    emboss_pattern: str,
    emboss_text: str,
    emboss_text_density: str,
    emboss_strength: str,
    displacement_enabled: bool,
    displacement_text: str,
    displacement_shift: int,
    displacement_density: str,
    displacement_font_ratio: float,
    displacement_mode: str,
    displacement_seed: int,
    displacement_shadow: bool,
    displacement_shadow_strength: float = 0.35,
    displacement_anchor_x: float,
    displacement_anchor_y: float,
    face_emboss_enabled: bool,
    face_emboss_text: str,
    face_emboss_copies: int,
    face_emboss_seed: int,
    face_emboss_patch_ratio: float,
    face_emboss_shift: int,
    face_emboss_opacity: float,
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
) -> tuple[np.ndarray, dict, str, str, str]:
    """Run pixel pipeline in-memory only (no DWT/LSB — those run after JW)."""
    status_msgs: list[str] = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        protected = protect_image(
            image_array,
            level="standard",
            watermark_text="",
            visible_watermark_text="",
            delivery_mode=True,
            protection_mode=mode,
            delivery_text=delivery_text if is_ultimate else "",
            face_shield=is_ultimate,
            artist_signature=signature_text,
            artist_signature_position=signature_position,
            blur_bar=blur_bar_enabled,
            blur_bar_text=blur_bar_text,
            blur_bar_position="custom" if blur_bar_y_ratio >= 0 else "below_face",
            blur_bar_sigma=blur_bar_sigma,
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
            dwt_payload="",
            blur_bar_count=blur_bar_count,
            blur_bar_y_ratio=blur_bar_y_ratio,
            blur_region_mask=blur_region_mask,
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
    for w_item in caught:
        if issubclass(w_item.category, UserWarning):
            status_msgs.append(str(w_item.message))

    metrics = evaluate_protection(image_array, protected)
    quality_label, quality_text = quality_assessment(metrics["psnr"])
    return protected, metrics, quality_label, quality_text, "; ".join(status_msgs)


async def _read_visible_edit_masks(
    image_array: np.ndarray,
    visible_erase_mask: UploadFile | None,
    visible_add_blur_mask: UploadFile | None,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Load erase / brush-blur masks; resize to *image_array* size.

    Do not gate on ``UploadFile.filename`` — some browsers send the bytes
    without a filename when the client uses ``Blob`` instead of ``File``.
    """
    from core.visible_edit import load_erase_mask_png

    oh, ow = image_array.shape[:2]
    erase_mask_arr: np.ndarray | None = None
    add_blur_arr: np.ndarray | None = None
    if visible_erase_mask is not None:
        mask_bytes = await visible_erase_mask.read()
        if mask_bytes:
            erase_mask_arr = load_erase_mask_png(mask_bytes, oh, ow)
    if visible_add_blur_mask is not None:
        blur_bytes = await visible_add_blur_mask.read()
        if blur_bytes:
            add_blur_arr = load_erase_mask_png(blur_bytes, oh, ow)
    return erase_mask_arr, add_blur_arr


def _has_visible_edit_payload(
    *,
    visible_edits_requested: bool,
    erase_mask_arr: np.ndarray | None,
    add_blur_arr: np.ndarray | None,
    add_placements: list[dict],
) -> bool:
    """True when the client explicitly committed visible-layer edits."""
    if visible_edits_requested:
        return True
    if erase_mask_arr is not None or add_blur_arr is not None:
        return True
    return bool(_placements_for_visible_edits(add_placements))


def _placements_for_visible_edits(add_placements: list[dict]) -> list[dict]:
    """``halftone_signature`` / ``logo`` 仅用于锚点，不参与 visible_edit 合成。"""
    return [
        p for p in add_placements
        if str(p.get("layer", "")) not in {"halftone_signature", "logo"}
    ]


def _visible_edits_empty(
    erase_mask_arr: np.ndarray | None,
    add_placements: list[dict],
    add_blur_arr: np.ndarray | None,
) -> bool:
    """True when no visible-layer edit payload was supplied (safe for ndarray masks)."""
    return (
        erase_mask_arr is None
        and not _placements_for_visible_edits(add_placements)
        and add_blur_arr is None
    )


def _visible_edit_layer_opts(
    *,
    add_placements: list[dict],
    displacement_enabled: bool,
    displacement_text: str,
    displacement_shift: int,
    displacement_font_ratio: float,
    displacement_seed: int,
    displacement_shadow: bool,
    displacement_shadow_strength: float = 0.35,
    blur_bar_enabled: bool,
    blur_bar_text: str,
    blur_bar_sigma: int,
    emboss_enabled: bool,
    emboss_pattern: str,
    emboss_strength: str,
    emboss_text: str,
    emboss_text_density: str,
    face_emboss_enabled: bool,
    face_emboss_text: str,
    face_emboss_shift: int,
    face_emboss_opacity: float,
    face_emboss_seed: int,
) -> tuple[dict | None, dict | None, dict | None, dict | None]:
    disp_opts = None
    if any(p.get("layer", "displacement") == "displacement" for p in add_placements):
        if displacement_enabled and displacement_text.strip():
            disp_opts = {
                "text": displacement_text,
                "shift": displacement_shift,
                "font_ratio": displacement_font_ratio,
                "seed": displacement_seed,
                "shadow": displacement_shadow,
                "shadow_strength": displacement_shadow_strength,
            }

    blur_opts = None
    if blur_bar_enabled and (
        any(p.get("layer") == "blur_bar" for p in add_placements)
    ):
        blur_opts = {
            "text": blur_bar_text,
            "sigma": blur_bar_sigma,
            "seed": 42,
            "width_ratio": 0.28,
            "height_ratio": 0.07,
        }

    emboss_opts = None
    if emboss_enabled and any(p.get("layer") == "emboss" for p in add_placements):
        emboss_opts = {
            "pattern": emboss_pattern,
            "strength": emboss_strength,
            "text": emboss_text,
            "text_density": emboss_text_density,
            "seed": 42,
        }

    face_emboss_opts = None
    if face_emboss_enabled and any(p.get("layer") == "face_emboss" for p in add_placements):
        face_emboss_opts = {
            "text": face_emboss_text,
            "shift": face_emboss_shift,
            "opacity": face_emboss_opacity,
            "seed": face_emboss_seed,
        }

    return disp_opts, blur_opts, emboss_opts, face_emboss_opts


def _apply_visible_edits_to_frame(
    image_array: np.ndarray,
    full_frame: np.ndarray,
    *,
    erase_mask_arr: np.ndarray | None,
    add_placements: list[dict],
    add_blur_arr: np.ndarray | None,
    displacement_enabled: bool,
    displacement_text: str,
    displacement_shift: int,
    displacement_font_ratio: float,
    displacement_seed: int,
    displacement_shadow: bool,
    displacement_shadow_strength: float = 0.35,
    blur_bar_enabled: bool,
    blur_bar_text: str,
    blur_bar_sigma: int,
    emboss_enabled: bool,
    emboss_pattern: str,
    emboss_strength: str,
    emboss_text: str,
    emboss_text_density: str,
    face_emboss_enabled: bool,
    face_emboss_text: str,
    face_emboss_shift: int,
    face_emboss_opacity: float,
    face_emboss_seed: int,
) -> np.ndarray:
    from core.visible_edit import apply_visible_edits

    if _visible_edits_empty(erase_mask_arr, add_placements, add_blur_arr):
        return full_frame

    edit_placements = _placements_for_visible_edits(add_placements)
    disp_opts, blur_opts, emboss_opts, face_emboss_opts = _visible_edit_layer_opts(
        add_placements=add_placements,
        displacement_enabled=displacement_enabled,
        displacement_text=displacement_text,
        displacement_shift=displacement_shift,
        displacement_font_ratio=displacement_font_ratio,
        displacement_seed=displacement_seed,
        displacement_shadow=displacement_shadow,
        displacement_shadow_strength=displacement_shadow_strength,
        blur_bar_enabled=blur_bar_enabled,
        blur_bar_text=blur_bar_text,
        blur_bar_sigma=blur_bar_sigma,
        emboss_enabled=emboss_enabled,
        emboss_pattern=emboss_pattern,
        emboss_strength=emboss_strength,
        emboss_text=emboss_text,
        emboss_text_density=emboss_text_density,
        face_emboss_enabled=face_emboss_enabled,
        face_emboss_text=face_emboss_text,
        face_emboss_shift=face_emboss_shift,
        face_emboss_opacity=face_emboss_opacity,
        face_emboss_seed=face_emboss_seed,
    )
    if add_blur_arr is not None and blur_bar_enabled and blur_opts is None:
        blur_opts = {
            "text": blur_bar_text,
            "sigma": blur_bar_sigma,
            "seed": 42,
            "width_ratio": 0.28,
            "height_ratio": 0.07,
        }

    return apply_visible_edits(
        image_array,
        full_frame,
        image_array,
        erase_mask=erase_mask_arr,
        add_placements=edit_placements or None,
        add_blur_mask=add_blur_arr,
        displacement=disp_opts,
        blur_opts=blur_opts,
        emboss_opts=emboss_opts,
        face_emboss_opts=face_emboss_opts,
    )


def _apply_invisible_layers(
    image_array: np.ndarray,
    *,
    blind_wm_enabled: bool,
    blind_wm_text: str,
    blind_wm_password: int,
    jw_enabled: bool,
    jw_creation: str,
    jw_restrictions: str,
    jw_embed_priority: str,
    artist: str,
    dwt_payload: str,
    lsb_payload: str,
    status_msgs: list[str],
) -> tuple[np.ndarray, bool]:
    """Embed only invisible layers (JW / DWT / LSB / blind) — no visible overlays."""
    protected = image_array.copy()
    blind_wm_len = 0

    if blind_wm_enabled and blind_wm_text.strip():
        try:
            from core.blind_watermark_adapter import embed_blind_watermark

            protected, blind_wm_len = embed_blind_watermark(
                protected, blind_wm_text.strip(), password=blind_wm_password
            )
        except Exception as exc:
            status_msgs.append(f"强化盲水印失败：{exc}")

    jw_applied = False
    _dwt = dwt_payload.strip() if dwt_payload else ""
    if jw_enabled:
        _dwt = ""
    if jw_enabled:
        try:
            from core.jingwei_protocol import (
                JwManifest,
                parse_creation,
                restrictions_from_ids,
            )

            restriction_ids = [r.strip() for r in jw_restrictions.split(",") if r.strip()]
            manifest = JwManifest(
                creation=parse_creation(jw_creation),
                restrictions=restrictions_from_ids(restriction_ids),
                visible_badge=False,
                artist=artist,
            )
            protected, jw_applied, _tier, _method = _ensure_jw_verifiable_on_output(
                protected, manifest, priority="auto",
            )
        except Exception as exc:
            status_msgs.append(f"精卫协议嵌入失败：{exc}")

    if _dwt and not jw_enabled:
        try:
            from core.dwt_watermark import embed_dwt_watermark

            protected = embed_dwt_watermark(protected, payload_text=_dwt)
        except Exception as exc:
            status_msgs.append(f"DWT 频域水印失败：{exc}")

    if lsb_payload:
        try:
            from core.lsb_watermark import embed_lsb_watermark

            protected = embed_lsb_watermark(protected, lsb_payload)
        except Exception as exc:
            status_msgs.append(f"LSB 隐写失败：{exc}")

    return protected, jw_applied


def _finalize_image_bytes(
    protected: np.ndarray,
    *,
    output_format: str,
    embed_metadata: bool,
    artist: str,
    status_msgs: list[str],
    alpha_channel: np.ndarray | None = None,
    protected_at: int | float | None = None,
) -> tuple[bytes, str]:
    """Save final pixels, embed EXIF/IPTC on disk, return raw bytes + mime.

    If *alpha_channel* is provided and output is PNG, the alpha is restored
    so transparent PNGs stay transparent.  JPEG always drops alpha.
    """
    _TEMP.mkdir(parents=True, exist_ok=True)
    fmt = "PNG" if output_format == "png" else "JPEG"
    suffix = ".png" if fmt == "PNG" else ".jpg"
    mime = "image/png" if fmt == "PNG" else "image/jpeg"
    out_path = _TEMP / f"protect_{uuid.uuid4().hex}{suffix}"

    if protected.ndim == 3 and protected.shape[2] == 4:
        pil = Image.fromarray(protected, "RGBA")
    elif alpha_channel is not None and fmt == "PNG":
        ph, pw = protected.shape[:2]
        ah, aw = alpha_channel.shape[:2]
        if ph != ah or pw != aw:
            alpha_resized = np.full((ph, pw), 255, dtype=np.uint8)
            copy_h = min(ph, ah)
            copy_w = min(pw, aw)
            alpha_resized[:copy_h, :copy_w] = alpha_channel[:copy_h, :copy_w]
            alpha_out = alpha_resized
        else:
            alpha_out = alpha_channel
        rgba = np.dstack([protected, alpha_out])
        pil = Image.fromarray(rgba, "RGBA")
    else:
        pil = Image.fromarray(protected)

    from core.color_profile import srgb_icc_bytes

    icc = srgb_icc_bytes()
    save_kw: dict = {}
    if icc:
        save_kw["icc_profile"] = icc

    if fmt == "PNG":
        pil.save(out_path, format="PNG", **save_kw)
    else:
        if pil.mode == "RGBA":
            pil = pil.convert("RGB")
        pil.save(out_path, format="JPEG", quality=95, **save_kw)

    if embed_metadata:
        meta_artist = artist.strip() or None
        if meta_artist or protected_at is not None:
            try:
                from core.compliance_metadata import embed_compliance_metadata

                embed_compliance_metadata(
                    out_path, artist=meta_artist, protected_at=protected_at,
                )
            except Exception as exc:
                status_msgs.append(f"元数据嵌入失败：{exc}")
        else:
            status_msgs.append("需要填写作者姓名才能嵌入元数据，已跳过元数据嵌入")

    data = out_path.read_bytes()
    out_path.unlink(missing_ok=True)
    return data, mime


@router.post("/protect")
async def protect(
    request: Request,
    authorization: str | None = Header(default=None),
    image: UploadFile = File(...),
    mode: str = Form("stealth"),
    auto_timestamp: str = Form("true"),
    dwt_payload: str = Form(""),
    watermark_text: str = Form(""),
    signature_text: str = Form(""),
    signature_position: str = Form("bottom_right"),
    artist: str = Form(""),
    embed_metadata: str = Form("true"),
    delivery_text: str = Form(""),
    output_format: str = Form("png"),
    displacement_enabled: str = Form("false"),
    displacement_text: str = Form(""),
    displacement_mode: str = Form("scatter"),
    displacement_font_ratio: float = Form(0.15),
    displacement_shift: int = Form(10),
    displacement_density: str = Form("normal"),
    displacement_seed: int = Form(42),
    displacement_shadow: str = Form("true"),
    displacement_shadow_strength: float = Form(0.35),
    displacement_anchor_x: float = Form(-1.0),
    displacement_anchor_y: float = Form(-1.0),
    face_emboss_enabled: str = Form("false"),
    face_emboss_text: str = Form(""),
    face_emboss_copies: int = Form(3),
    face_emboss_shift: int = Form(12),
    face_emboss_opacity: float = Form(0.25),
    face_emboss_patch_ratio: float = Form(0.30),
    face_emboss_seed: int = Form(42),
    emboss_enabled: str = Form("false"),
    emboss_pattern: str = Form("diagonal"),
    emboss_strength: str = Form("medium"),
    emboss_text: str = Form(""),
    emboss_text_density: str = Form("dense"),
    blur_bar_enabled: str = Form("false"),
    blur_bar_y_ratio: float = Form(0.50),
    blur_bar_count: int = Form(1),
    blur_bar_sigma: int = Form(12),
    blur_bar_text: str = Form(""),
    blind_wm_enabled: str = Form("false"),
    blind_wm_text: str = Form(""),
    blind_wm_password: int = Form(1234),
    jw_enabled: str = Form("false"),
    jw_creation: str = Form("OC"),
    jw_restrictions: str = Form(""),
    jw_badge: str = Form("true"),
    jw_footer_strip: str = Form("false"),
    jw_embed_priority: str = Form("auto"),
    track_enabled: str = Form("false"),
    track_artist: str = Form(""),
    visible_add_points: str = Form(""),
    visible_edits_requested: str = Form("false"),
    visible_erase_mask: UploadFile | None = File(None),
    visible_add_blur_mask: UploadFile | None = File(None),
    blur_region_mask: UploadFile | None = File(None),
    halftone_enabled: str = Form("false"),
    halftone_style: str = Form("ascii_chars"),
    halftone_text: str = Form(""),
    halftone_size: int = Form(50),
    halftone_density: int = Form(50),
    halftone_visibility: int = Form(50),
    halftone_anchor_x: float = Form(-1.0),
    halftone_anchor_y: float = Form(-1.0),
    halftone_signature: int = Form(50),
    halftone_signature_size: int = Form(50),
    halftone_dot_texture: int = Form(0),
    halftone_advanced: int = Form(50),
    halftone_background_chain: int = Form(78),
    halftone_contour_warp: int = Form(70),
    logo_enabled: str = Form("false"),
    logo_image: UploadFile | None = File(None),
    logo_opacity: float = Form(0.40),
    logo_scale: float = Form(0.18),
    logo_position: str = Form("bottom_right"),
    logo_anchor_x: float = Form(-1.0),
    logo_anchor_y: float = Form(-1.0),
    logo_tint: str = Form("gray"),
    visible_mark: str = Form("auto"),
) -> JSONResponse:
    check_rate_limit(request, "protect", rate_limit_protect_per_min())
    try:
        image_array, original_alpha = _read_upload(image)
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    check_image_pixels(image_array)

    logo_rgba: np.ndarray | None = None
    if _bool(logo_enabled):
        try:
            logo_rgba = await _read_logo_upload(logo_image)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        if logo_rgba is None:
            return JSONResponse(
                {
                    "ok": False,
                    "error_code": LOGO_FILE_REQUIRED,
                    "error": "启用 Logo 水印时必须上传图片",
                },
                status_code=400,
            )

    from core.credit_mode import (
        CREDIT_LOGO_SHIFT,
        resolve_credit_logo_opacity,
        resolve_credit_logo_scale,
    )

    logo_opacity = resolve_credit_logo_opacity(
        mode=mode,
        logo_present=logo_rgba is not None,
        requested=logo_opacity,
    )
    logo_scale = resolve_credit_logo_scale(
        mode=mode,
        logo_present=logo_rgba is not None,
        requested=logo_scale,
    )
    logo_shift_px = CREDIT_LOGO_SHIFT if mode == "credit" and logo_rgba is not None else 10

    if mode == "credit" and (artist or "").strip():
        jw_enabled = "true"
        if not (watermark_text or "").strip():
            watermark_text = artist.strip()

    (
        _ht_on, halftone_text, halftone_visibility, halftone_signature,
        _disp_on, displacement_text, displacement_font_ratio, displacement_shift,
        _disp_shadow, displacement_shadow_strength, _ascii_faint,
    ) = _apply_credit_visible_recipe(
        mode=mode,
        image=image_array,
        halftone_enabled=_bool(halftone_enabled),
        halftone_text=halftone_text,
        halftone_visibility=halftone_visibility,
        halftone_signature=halftone_signature,
        artist=artist,
        displacement_enabled=_bool(displacement_enabled),
        displacement_text=displacement_text,
        displacement_font_ratio=displacement_font_ratio,
        displacement_shift=displacement_shift,
        displacement_shadow=_bool(displacement_shadow),
        displacement_shadow_strength=displacement_shadow_strength,
        visible_mark=visible_mark,
        logo_present=logo_rgba is not None,
    )
    if _ht_on:
        halftone_enabled = "true"
        if not (halftone_style or "").strip():
            halftone_style = "ascii_chars"
    else:
        halftone_enabled = "false"
    if _disp_on:
        displacement_enabled = "true"
        displacement_shadow = "true" if _disp_shadow else "false"
    else:
        displacement_enabled = "false"

    if _bool(displacement_enabled) and not displacement_text.strip():
        return JSONResponse(
            {
                "ok": False,
                "error_code": DISP_TEXT_REQUIRED,
                "error": "启用位移水印时必须填写水印文字",
            },
            status_code=400,
        )

    if _bool(halftone_enabled) and not halftone_text.strip():
        return JSONResponse(
            {
                "ok": False,
                "error": "启用半调防盗层时必须填写署名文字",
            },
            status_code=400,
        )

    _dwt = (dwt_payload or "").strip()
    _lsb = (watermark_text or "").strip()
    _jw_on = _bool(jw_enabled)
    _jw_priority = "auto"
    _jw_embed_timestamp: int | None = None
    _track_dwt = ""
    if _jw_on:
        _dwt = ""
    # 追踪巩固: anchor only carries year-month. The exact date rides invisible
    # layers (DWT + file metadata DateTime) so verify can show signature+年月日
    # without the user typing a date. _track_dwt is independent of JW / user DWT.
    if _bool(track_enabled):
        _track_id = _resolve_track_artist(
            track_artist=track_artist,
            artist=artist,
            dwt_payload=(dwt_payload or "").strip(),
            watermark_text=_lsb,
            signature_text=(signature_text or "").strip(),
            halftone_text=(halftone_text or "").strip(),
        )
        if _track_id:
            _track_dwt = _track_id
    if _bool(auto_timestamp):
        ts = datetime.now().strftime("%m%d_%H%M")
        if _jw_on or _bool(track_enabled):
            _jw_embed_timestamp = int(time.time())
        if _dwt:
            _dwt = (_dwt + "_" + ts)[:24]
        if _track_dwt:
            _track_dwt = (_track_dwt + "_" + ts)[:24]
        if _lsb:
            _lsb = _lsb + " | " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elif _jw_on:
        _jw_embed_timestamp = 0

    is_ultimate = mode.startswith("ultimate")
    status_msgs: list[str] = []

    blur_region_arr: np.ndarray | None = None
    if blur_region_mask is not None and blur_region_mask.filename and _bool(blur_bar_enabled):
        try:
            from core.visible_edit import load_erase_mask_png

            mask_bytes = await blur_region_mask.read()
            if mask_bytes:
                oh, ow = image_array.shape[:2]
                blur_region_arr = load_erase_mask_png(mask_bytes, oh, ow)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    # When a layer is driven by user-placed dashed boxes (位移整词 / 整条横向
    # 模糊条), the main pipeline must NOT also auto-render it, or the box-based
    # render in apply_visible_edits would duplicate it. Anti-AI stealth surface
    # is computed from the user's original intent below, so suppressing the
    # auto layer never weakens protection.
    disp_box_flow = _bool(displacement_enabled) and displacement_mode == "band"
    blur_box_flow = _bool(blur_bar_enabled) and blur_region_arr is None
    # Face emboss is now placed via draggable boxes on the front end, so the
    # pipeline must not auto-place it too (that would double-render).
    fe_box_flow = _bool(face_emboss_enabled) and bool(face_emboss_text.strip())
    main_displacement_enabled = _bool(displacement_enabled) and not disp_box_flow
    main_blur_bar_enabled = _bool(blur_bar_enabled) and not blur_box_flow
    main_face_emboss_enabled = _bool(face_emboss_enabled) and not fe_box_flow

    _ht_placements: list[dict] = []
    if visible_add_points.strip():
        from core.visible_edit import parse_add_placements

        _ht_placements = parse_add_placements(visible_add_points)
    from core.halftone_protect import resolve_halftone_anchor_from_placements

    _ht_ax, _ht_ay = resolve_halftone_anchor_from_placements(
        _ht_placements,
        anchor_x=halftone_anchor_x,
        anchor_y=halftone_anchor_y,
    )

    try:
        _validate_image(image_array)
        stealth_surface = _wants_stealth_surface(
            mode=mode,
            is_ultimate=is_ultimate,
            blur_bar_enabled=_bool(blur_bar_enabled),
            emboss_enabled=_bool(emboss_enabled),
            displacement_enabled=_bool(displacement_enabled),
            displacement_text=displacement_text,
            face_emboss_enabled=_bool(face_emboss_enabled),
            face_emboss_text=face_emboss_text,
            halftone_enabled=_bool(halftone_enabled),
            halftone_text=halftone_text,
        )
        jw_manifest = None
        if _jw_on:
            from core.jingwei_protocol import (
                JwManifest,
                parse_creation,
                restrictions_from_ids,
            )

            restriction_ids = [r.strip() for r in jw_restrictions.split(",") if r.strip()]
            jw_manifest = JwManifest(
                creation=parse_creation(jw_creation),
                restrictions=restrictions_from_ids(restriction_ids),
                visible_badge=_bool(jw_badge) and not _bool(jw_footer_strip),
                artist=artist,
            )
        protected, metrics, quality_label, quality_text, pipe_status = _run_protection(
            image_array,
            mode=mode,
            is_ultimate=is_ultimate,
            delivery_text=delivery_text,
            signature_text=signature_text,
            signature_position=signature_position,
            blur_bar_enabled=main_blur_bar_enabled,
            blur_bar_text=blur_bar_text,
            blur_bar_y_ratio=blur_bar_y_ratio,
            blur_bar_sigma=blur_bar_sigma,
            blur_bar_count=blur_bar_count,
            emboss_enabled=_bool(emboss_enabled),
            emboss_pattern=emboss_pattern,
            emboss_text=emboss_text,
            emboss_text_density=emboss_text_density,
            emboss_strength=emboss_strength,
            displacement_enabled=main_displacement_enabled,
            displacement_text=displacement_text,
            displacement_shift=displacement_shift,
            displacement_density=displacement_density,
            displacement_font_ratio=displacement_font_ratio,
            displacement_mode=displacement_mode,
            displacement_seed=displacement_seed,
            displacement_shadow=_bool(displacement_shadow),
            displacement_shadow_strength=displacement_shadow_strength,
            displacement_anchor_x=displacement_anchor_x,
            displacement_anchor_y=displacement_anchor_y,
            face_emboss_enabled=main_face_emboss_enabled,
            face_emboss_text=face_emboss_text,
            face_emboss_copies=face_emboss_copies,
            face_emboss_seed=face_emboss_seed,
            face_emboss_patch_ratio=face_emboss_patch_ratio,
            face_emboss_shift=face_emboss_shift,
            face_emboss_opacity=face_emboss_opacity,
            blur_region_mask=blur_region_arr,
            stealth_surface=stealth_surface,
            halftone_enabled=_bool(halftone_enabled),
            halftone_style=halftone_style,
            halftone_text=halftone_text,
            halftone_size=halftone_size,
            halftone_density=halftone_density,
            halftone_visibility=halftone_visibility,
            halftone_anchor_x=_ht_ax,
            halftone_anchor_y=_ht_ay,
            halftone_signature=halftone_signature,
            halftone_signature_size=halftone_signature_size,
            halftone_dot_texture=halftone_dot_texture,
            halftone_background_chain=halftone_background_chain,
            halftone_contour_warp=halftone_contour_warp,
            halftone_credit_faint=_ascii_faint,
            logo_rgba=logo_rgba,
            logo_opacity=logo_opacity,
            logo_scale=logo_scale,
            logo_position=logo_position,
            logo_anchor_x=logo_anchor_x,
            logo_anchor_y=logo_anchor_y,
            logo_tint=logo_tint,
            logo_shift_px=logo_shift_px,
        )
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse(
            {
                "ok": False,
                "error_code": SERVER_ERROR,
                "error": f"服务器错误：{exc}",
            },
            status_code=500,
        )

    if pipe_status:
        status_msgs.append(pipe_status)

    blind_wm_len = 0
    if _bool(blind_wm_enabled) and blind_wm_text.strip():
        try:
            from core.blind_watermark_adapter import embed_blind_watermark

            protected, blind_wm_len = embed_blind_watermark(
                protected, blind_wm_text.strip(), password=blind_wm_password
            )
        except Exception as exc:
            status_msgs.append(f"强化盲水印失败：{exc}")

    want_footer = _bool(jw_footer_strip)

    jw_applied = False
    dwt_applied = False
    lsb_applied = False
    track_applied = False
    jw_embed_tier: str | None = None
    jw_embed_method: str | None = None
    if _jw_on and jw_manifest is None:
        try:
            from core.jingwei_protocol import (
                JwManifest,
                parse_creation,
                restrictions_from_ids,
            )

            restriction_ids = [r.strip() for r in jw_restrictions.split(",") if r.strip()]
            jw_manifest = JwManifest(
                creation=parse_creation(jw_creation),
                restrictions=restrictions_from_ids(restriction_ids),
                visible_badge=_bool(jw_badge) and not want_footer,
                artist=artist,
            )
        except Exception as exc:
            status_msgs.append(f"精卫协议嵌入失败：{exc}")

    _embed_dwt_payload = _dwt if (_dwt and not _jw_on) else _track_dwt
    if _embed_dwt_payload:
        try:
            from core.dwt_watermark import embed_dwt_watermark

            protected = embed_dwt_watermark(protected, payload_text=_embed_dwt_payload)
            dwt_applied = True
        except Exception as exc:
            status_msgs.append(f"DWT 频域水印失败：{exc}")

    if jw_manifest and jw_manifest.visible_badge and not want_footer:
        try:
            from core.jingwei_protocol import apply_jw_visible_badge

            protected = apply_jw_visible_badge(protected, jw_manifest)
        except Exception as exc:
            status_msgs.append(f"JW 可见徽章失败：{exc}")

    if _jw_on and jw_manifest is not None:
        try:
            has_visible = want_footer or (
                jw_manifest.visible_badge and not want_footer
            )
            protected, jw_applied, jw_embed_tier, jw_embed_method = _ensure_jw_verifiable_on_output(
                protected,
                jw_manifest,
                priority=_jw_priority,
                embed_timestamp=_jw_embed_timestamp,
            )
            _append_jw_embed_status(
                status_msgs,
                jw_applied=jw_applied,
                jw_embed_tier=jw_embed_tier,
                jw_embed_method=jw_embed_method,
                source_image=image_array,
                has_visible_declaration=has_visible,
            )
        except Exception as exc:
            status_msgs.append(f"精卫协议嵌入失败：{exc}")

    if _jw_on and jw_manifest is not None and jw_applied:
        from core.jingwei_protocol import (
            embed_jw_lsb_fallback,
            extract_jw_from_lsb,
            extract_jw_watermark,
        )

        readable = extract_jw_watermark(protected).get("found") or bool(
            extract_jw_from_lsb(protected)
        )
        if not readable:
            try:
                protected = embed_jw_lsb_fallback(
                    protected, jw_manifest, embed_timestamp=_jw_embed_timestamp,
                )
                if extract_jw_from_lsb(protected):
                    jw_embed_method = "lsb"
                    jw_embed_tier = "lsb"
                else:
                    jw_applied = False
            except Exception:
                jw_applied = False

    if _lsb:
        try:
            from core.lsb_watermark import embed_lsb_watermark

            protected = embed_lsb_watermark(protected, _lsb)
            lsb_applied = True
        except Exception as exc:
            status_msgs.append(f"LSB 隐写失败：{exc}")

    if _jw_on and jw_manifest is not None and jw_applied and jw_embed_method == "lsb":
        from core.jingwei_protocol import embed_jw_lsb_fallback, extract_jw_from_lsb

        try:
            protected = embed_jw_lsb_fallback(
                protected, jw_manifest, embed_timestamp=_jw_embed_timestamp,
            )
            if not extract_jw_from_lsb(protected):
                jw_applied = False
            elif _lsb:
                status_msgs.append(
                    "本图精卫声明已用备用方式写入；若同时填写了 LSB 栏，以精卫声明为准。",
                )
        except Exception:
            jw_applied = False

    full_protected = protected
    try:
        from core.visible_edit import apply_visible_edits, parse_add_placements

        erase_mask_arr, add_blur_arr = await _read_visible_edit_masks(
            image_array, visible_erase_mask, visible_add_blur_mask,
        )
        add_placements = parse_add_placements(visible_add_points)
        has_visible_edit = _has_visible_edit_payload(
            visible_edits_requested=_bool(visible_edits_requested),
            erase_mask_arr=erase_mask_arr,
            add_blur_arr=add_blur_arr,
            add_placements=add_placements,
        )
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    if has_visible_edit:
        try:

            disp_opts = None
            if any(p.get("layer", "displacement") == "displacement" for p in add_placements):
                if _bool(displacement_enabled) and displacement_text.strip():
                    disp_opts = {
                        "text": displacement_text,
                        "shift": displacement_shift,
                        "font_ratio": displacement_font_ratio,
                        "seed": displacement_seed,
                        "shadow": _bool(displacement_shadow),
                        "shadow_strength": displacement_shadow_strength,
                    }

            blur_opts = None
            if (
                _bool(blur_bar_enabled)
                and (
                    any(p.get("layer") == "blur_bar" for p in add_placements)
                    or add_blur_arr is not None
                )
            ):
                blur_opts = {
                    "text": blur_bar_text,
                    "sigma": blur_bar_sigma,
                    "seed": 42,
                    "width_ratio": 0.28,
                    "height_ratio": 0.07,
                }

            emboss_opts = None
            if _bool(emboss_enabled) and any(p.get("layer") == "emboss" for p in add_placements):
                emboss_opts = {
                    "pattern": emboss_pattern,
                    "strength": emboss_strength,
                    "text": emboss_text,
                    "text_density": emboss_text_density,
                    "seed": 42,
                }

            face_emboss_opts = None
            if _bool(face_emboss_enabled) and any(p.get("layer") == "face_emboss" for p in add_placements):
                face_emboss_opts = {
                    "text": face_emboss_text,
                    "shift": face_emboss_shift,
                    "opacity": face_emboss_opacity,
                    "seed": face_emboss_seed,
                }

            # Match live-preview erase UX: reveal the original upload under the
            # erased visible layers (see _apply_visible_edits_to_frame).
            protected = apply_visible_edits(
                image_array,
                full_protected,
                image_array,
                erase_mask=erase_mask_arr,
                add_placements=add_placements or None,
                add_blur_mask=add_blur_arr,
                displacement=disp_opts,
                blur_opts=blur_opts,
                emboss_opts=emboss_opts,
                face_emboss_opts=face_emboss_opts,
            )
            skipped = []
            if any(p.get("layer", "displacement") == "displacement" for p in add_placements) and not disp_opts:
                skipped.append("位移水印")
            if any(p.get("layer") == "blur_bar" for p in add_placements) and not blur_opts:
                skipped.append("模糊条")
            if any(p.get("layer") == "emboss" for p in add_placements) and not emboss_opts:
                skipped.append("浮雕纹理")
            if any(p.get("layer") == "face_emboss" for p in add_placements) and not face_emboss_opts:
                skipped.append("脸部浮雕锁")
            if skipped:
                status_msgs.append(f"部分添加未生效（需启用并配置）：{'、'.join(skipped)}")
            metrics = evaluate_protection(image_array, protected[: image_array.shape[0], : image_array.shape[1]])
            quality_label, quality_text = quality_assessment(metrics["psnr"])
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        except Exception as exc:
            status_msgs.append(f"可见层编辑失败：{exc}")

    # Traceability anchor (可追踪优先): stamp LAST so the four faint anchors +
    # year-month/artist-code payload ride on TOP of every visible & invisible
    # layer and cover the full frame — this is the only mark that survives a
    # social-media screenshot round-trip. Independent of the JW declaration.
    if _bool(track_enabled):
        # Use raw form values (before auto_timestamp suffixes) so the anchor
        # identity matches what the user typed in LSB/DWT, not the stored payload.
        _track_id = _resolve_track_artist(
            track_artist=track_artist,
            artist=artist,
            dwt_payload=(dwt_payload or "").strip(),
            watermark_text=(watermark_text or "").strip(),
            signature_text=(signature_text or "").strip(),
            halftone_text=(halftone_text or "").strip(),
        )
        if not _track_id:
            status_msgs.append(
                "已开启追踪巩固，但未在「隐性追踪 / 署名」中填写任何签名"
                "（创作者姓名、DWT、LSB、浮雕签名或半调防盗署名），追踪锚点未嵌入。",
            )
        else:
            from core.jw_anchor import anchor_size_ok, embed_anchor_signature, read_anchor_tracking

            _ph, _pw = protected.shape[:2]
            if not anchor_size_ok(protected):
                status_msgs.append(
                    f"图片短边仅 {min(_ph, _pw)} 像素（追踪锚点要求 ≥128），锚点未嵌入。"
                    "请导出更大画布（建议短边 ≥512）后重新保护。",
                )
            else:
                try:
                    when = _jw_embed_timestamp if (_jw_embed_timestamp and _jw_embed_timestamp > 0) else time.time()
                    if protected.ndim == 3 and protected.shape[2] == 4:
                        rgb = np.ascontiguousarray(protected[:, :, :3])
                        alpha = protected[:, :, 3]
                        rgb = embed_anchor_signature(rgb, _track_id, when, region="full")
                        protected = np.dstack([rgb, alpha])
                        _check = rgb
                    else:
                        protected = embed_anchor_signature(
                            np.ascontiguousarray(protected), _track_id, when, region="full"
                        )
                        _check = protected
                    _self_ok = read_anchor_tracking(_check) is not None
                    if _self_ok:
                        track_applied = True
                    else:
                        status_msgs.append(
                            "追踪锚点写入后未能自检读出（白底小图较常见）。"
                            "请换更大尺寸后重试。",
                        )
                except Exception as exc:
                    status_msgs.append(f"追踪锚点嵌入失败：{exc}")

    # JW footer is appended AFTER tracking anchors so the four corner fiducials
    # stay on the artwork canvas (not on the white metadata strip).
    if jw_manifest and want_footer:
        try:
            from core.jingwei_protocol import apply_jw_footer_strip

            protected = apply_jw_footer_strip(
                protected,
                jw_manifest,
                alpha_channel=original_alpha,
            )
            original_alpha = None
        except Exception as exc:
            status_msgs.append(f"底部白边失败：{exc}")

    if output_format != "png" and original_alpha is not None:
        status_msgs.append("输出格式为 JPEG，透明通道将丢失")

    try:
        _meta_artist = artist.strip() or (
            _resolve_track_artist(
                track_artist=track_artist,
                artist=artist,
                dwt_payload=(dwt_payload or "").strip(),
                watermark_text=(watermark_text or "").strip(),
                signature_text=(signature_text or "").strip(),
                halftone_text=(halftone_text or "").strip(),
            ) if _bool(track_enabled) else ""
        )
        img_bytes, mime = _finalize_image_bytes(
            protected,
            output_format=output_format,
            embed_metadata=_bool(embed_metadata),
            artist=_meta_artist,
            status_msgs=status_msgs,
            alpha_channel=original_alpha,
            protected_at=_jw_embed_timestamp if (
                _jw_embed_timestamp and _jw_embed_timestamp > 0 and (_jw_on or _bool(track_enabled))
            ) else None,
        )
    except Exception as exc:
        return JSONResponse(
            {
                "ok": False,
                "error_code": OUTPUT_FAILED,
                "error": f"输出失败：{exc}",
            },
            status_code=500,
        )

    img_b64 = base64.b64encode(img_bytes).decode()

    comparison_b64: str | None = None
    try:
        from evaluation.visualize import COMPARISON_DISPLAY_MAX_SIDE, generate_comparison

        cmp_path = _TEMP / f"cmp_{uuid.uuid4().hex}.png"
        prot_rgb = protected[:, :, :3] if protected.ndim == 3 and protected.shape[2] == 4 else protected
        orig_h, orig_w = image_array.shape[:2]
        prot_h, prot_w = prot_rgb.shape[:2]
        if prot_h != orig_h or prot_w != orig_w:
            cmp_protected = prot_rgb[:orig_h, :orig_w]
        else:
            cmp_protected = prot_rgb
        generate_comparison(
            image_array,
            cmp_protected,
            str(cmp_path),
            max_side=COMPARISON_DISPLAY_MAX_SIDE,
        )
        comparison_b64 = f"data:image/png;base64,{base64.b64encode(cmp_path.read_bytes()).decode()}"
        cmp_path.unlink(missing_ok=True)
    except Exception as exc:
        status_msgs.append(f"对比图生成失败：{exc}")

    try:
        record_protect_success()
    except Exception:
        pass

    jw_quota: dict | None = None
    if jw_applied:
        user = _resolve_user(authorization)
        if user:
            try:
                jw_quota = record_jw_protect(int(user["id"]))
                if jw_quota.get("jw_works_incremented"):
                    allowance = int(jw_quota["daily_allowance"])
                    status_msgs.append(
                        f"JW 作品已记录 · 每日可领 {allowance} 格（精卫之海领取）"
                    )
            except ValueError:
                pass

    return JSONResponse({
        "ok": True,
        "image": f"data:{mime};base64,{img_b64}",
        "comparison": comparison_b64,
        "metrics": _json_safe_metrics(metrics),
        "quality_label": quality_label,
        "quality_text": quality_text,
        "status": "; ".join(status_msgs) if status_msgs else "",
        "download_url": "",
        "blind_wm_len": blind_wm_len,
        "jw_applied": jw_applied,
        "jw_embed_tier": jw_embed_tier,
        "jw_embed_method": jw_embed_method if _jw_on else None,
        "jw_embed_priority": "auto" if _jw_on else None,
        "dwt_applied": dwt_applied,
        "lsb_applied": lsb_applied,
        "track_applied": track_applied,
        "jw_quota": jw_quota,
    })


@router.post("/protect/jw-hint")
async def protect_jw_hint(
    request: Request,
    image: UploadFile = File(...),
) -> JSONResponse:
    """Plain-language hint for JW write suitability (before protect)."""
    check_rate_limit(request, "protect", rate_limit_protect_per_min())
    try:
        image_array, _ = _read_upload(image)
        check_image_pixels(image_array)
        from core.jingwei_protocol import jw_write_hint_for_image

        hint = jw_write_hint_for_image(image_array)
        return JSONResponse({"ok": True, **hint})
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/protect/preview")
async def protect_preview(
    request: Request,
    image: UploadFile = File(...),
    mode: str = Form("stealth"),
    signature_text: str = Form(""),
    signature_position: str = Form("bottom_right"),
    displacement_enabled: str = Form("false"),
    displacement_text: str = Form(""),
    displacement_mode: str = Form("scatter"),
    displacement_font_ratio: float = Form(0.15),
    displacement_shift: int = Form(10),
    displacement_density: str = Form("normal"),
    displacement_seed: int = Form(42),
    displacement_shadow: str = Form("true"),
    displacement_shadow_strength: float = Form(0.35),
    displacement_anchor_x: float = Form(-1.0),
    displacement_anchor_y: float = Form(-1.0),
    face_emboss_enabled: str = Form("false"),
    face_emboss_text: str = Form(""),
    face_emboss_copies: int = Form(3),
    face_emboss_shift: int = Form(12),
    face_emboss_opacity: float = Form(0.25),
    face_emboss_patch_ratio: float = Form(0.30),
    face_emboss_seed: int = Form(42),
    emboss_enabled: str = Form("false"),
    emboss_pattern: str = Form("diagonal"),
    emboss_strength: str = Form("medium"),
    emboss_text: str = Form(""),
    emboss_text_density: str = Form("dense"),
    blur_bar_enabled: str = Form("false"),
    blur_bar_y_ratio: float = Form(0.50),
    blur_bar_count: int = Form(1),
    blur_bar_sigma: int = Form(12),
    blur_bar_text: str = Form(""),
    jw_footer_preview: str = Form("false"),
    jw_creation: str = Form("OC"),
    jw_restrictions: str = Form(""),
    jw_footer_artist: str = Form(""),
    track_enabled: str = Form("false"),
    track_artist: str = Form(""),
    artist: str = Form(""),
    dwt_payload: str = Form(""),
    watermark_text: str = Form(""),
    auto_timestamp: str = Form("true"),
    blur_region_mask: UploadFile | None = File(None),
    visible_add_points: str = Form(""),
    visible_erase_mask: UploadFile | None = File(None),
    visible_add_blur_mask: UploadFile | None = File(None),
    halftone_enabled: str = Form("false"),
    halftone_style: str = Form("ascii_chars"),
    halftone_text: str = Form(""),
    halftone_size: int = Form(50),
    halftone_density: int = Form(50),
    halftone_visibility: int = Form(50),
    halftone_anchor_x: float = Form(-1.0),
    halftone_anchor_y: float = Form(-1.0),
    halftone_signature: int = Form(50),
    halftone_signature_size: int = Form(50),
    halftone_dot_texture: int = Form(0),
    halftone_advanced: int = Form(50),
    halftone_background_chain: int = Form(78),
    halftone_contour_warp: int = Form(70),
    logo_enabled: str = Form("false"),
    logo_image: UploadFile | None = File(None),
    logo_opacity: float = Form(0.40),
    logo_scale: float = Form(0.18),
    logo_position: str = Form("bottom_right"),
    logo_anchor_x: float = Form(-1.0),
    logo_anchor_y: float = Form(-1.0),
    logo_tint: str = Form("gray"),
    visible_mark: str = Form("auto"),
) -> JSONResponse:
    """Visible-layer preview only — no invisible JW/DWT/LSB (fast debounced UI).

    When ``track_enabled`` is on and ``artist`` is set, also stamps the faint
    traceability anchors so the user can confirm the effect before protecting.
    """
    check_rate_limit(request, "preview", rate_limit_preview_per_min())
    try:
        image_array, _ = _read_upload(image)
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    check_image_pixels(image_array)

    preview_logo: np.ndarray | None = None
    if _bool(logo_enabled):
        try:
            preview_logo = await _read_logo_upload(logo_image)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    from core.credit_mode import (
        CREDIT_LOGO_SHIFT,
        resolve_credit_logo_opacity,
        resolve_credit_logo_scale,
    )

    logo_opacity = resolve_credit_logo_opacity(
        mode=mode,
        logo_present=preview_logo is not None,
        requested=logo_opacity,
    )
    logo_scale = resolve_credit_logo_scale(
        mode=mode,
        logo_present=preview_logo is not None,
        requested=logo_scale,
    )
    logo_shift_px = CREDIT_LOGO_SHIFT if mode == "credit" and preview_logo is not None else 10

    (
        _ht_on, halftone_text, halftone_visibility, halftone_signature,
        _disp_on, displacement_text, displacement_font_ratio, displacement_shift,
        _disp_shadow, displacement_shadow_strength, _ascii_faint,
    ) = _apply_credit_visible_recipe(
        mode=mode,
        image=image_array,
        halftone_enabled=_bool(halftone_enabled),
        halftone_text=halftone_text,
        halftone_visibility=halftone_visibility,
        halftone_signature=halftone_signature,
        artist=artist,
        displacement_enabled=_bool(displacement_enabled),
        displacement_text=displacement_text,
        displacement_font_ratio=displacement_font_ratio,
        displacement_shift=displacement_shift,
        displacement_shadow=_bool(displacement_shadow),
        displacement_shadow_strength=displacement_shadow_strength,
        visible_mark=visible_mark,
        logo_present=preview_logo is not None,
    )
    if _ht_on:
        halftone_enabled = "true"
        if not (halftone_style or "").strip():
            halftone_style = "ascii_chars"
    else:
        halftone_enabled = "false"
    if _disp_on:
        displacement_enabled = "true"
        displacement_shadow = "true" if _disp_shadow else "false"
    else:
        displacement_enabled = "false"

    if _bool(displacement_enabled) and not displacement_text.strip():
        return JSONResponse(
            {
                "ok": False,
                "error_code": DISP_TEXT_REQUIRED,
                "error": "启用位移水印时必须填写水印文字",
            },
            status_code=400,
        )

    if _bool(halftone_enabled) and not halftone_text.strip():
        return JSONResponse(
            {
                "ok": False,
                "error": "启用半调防盗层时必须填写署名文字",
            },
            status_code=400,
        )

    try:
        _validate_image(image_array)
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    blur_region_arr: np.ndarray | None = None
    if blur_region_mask is not None and blur_region_mask.filename and _bool(blur_bar_enabled):
        try:
            from core.visible_edit import load_erase_mask_png

            mask_bytes = await blur_region_mask.read()
            if mask_bytes:
                oh, ow = image_array.shape[:2]
                blur_region_arr = load_erase_mask_png(mask_bytes, oh, ow)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    # Box-flow layers (位移整词 / 整条横向模糊条) are rendered from the user's
    # dashed boxes in _apply_visible_edits_to_frame below, so the base preview
    # must skip their automatic render to avoid a duplicate. Keep the anti-AI
    # stealth surface based on the user's original intent.
    disp_box_flow = _bool(displacement_enabled) and displacement_mode == "band"
    blur_box_flow = _bool(blur_bar_enabled) and blur_region_arr is None
    fe_box_flow = _bool(face_emboss_enabled) and bool(face_emboss_text.strip())
    main_displacement_enabled = _bool(displacement_enabled) and not disp_box_flow
    main_blur_bar_enabled = _bool(blur_bar_enabled) and not blur_box_flow
    main_face_emboss_enabled = _bool(face_emboss_enabled) and not fe_box_flow
    # The preview must FAITHFULLY match the final output: when an attack layer
    # turns the anti-AI stealth surface on, that fine texture also visually
    # camouflages the corner tracking anchors. Skipping it (as before) made the
    # anchors look far more prominent in the preview than in the saved file. So
    # we use the SAME stealth decision as /protect. The stack is expensive
    # (~4s, large FFT/HSV buffers) and previously caused multi-second waits and
    # out-of-memory 500s, so when it IS on we render the preview at a smaller
    # working resolution to keep it fast and memory-bounded; the texture (and
    # the anchor camouflage) stays representative.
    preview_stealth_surface = _wants_stealth_surface(
        mode=mode,
        is_ultimate=mode.startswith("ultimate"),
        blur_bar_enabled=_bool(blur_bar_enabled),
        emboss_enabled=_bool(emboss_enabled),
        displacement_enabled=_bool(displacement_enabled),
        displacement_text=displacement_text,
        face_emboss_enabled=_bool(face_emboss_enabled),
        face_emboss_text=face_emboss_text,
        halftone_enabled=_bool(halftone_enabled),
        halftone_text=halftone_text,
    )
    _halftone_on = _bool(halftone_enabled) and bool(halftone_text.strip())
    if _halftone_on:
        from core.halftone_protect import HALFTONE_REF_LONG_SIDE
        # 与成图半调 ref 管线（1280）对齐；整数倍放大时预览≈成图
        preview_max_side = HALFTONE_REF_LONG_SIDE
    elif preview_stealth_surface:
        preview_max_side = 900
    else:
        preview_max_side = 1280

    _ht_placements: list[dict] = []
    if visible_add_points.strip():
        from core.visible_edit import parse_add_placements

        _ht_placements = parse_add_placements(visible_add_points)
    from core.halftone_protect import resolve_halftone_anchor_from_placements

    _ht_ax, _ht_ay = resolve_halftone_anchor_from_placements(
        _ht_placements,
        anchor_x=halftone_anchor_x,
        anchor_y=halftone_anchor_y,
    )

    try:
        from core.visible_preview import render_visible_preview

        restriction_ids = [r.strip() for r in jw_restrictions.split(",") if r.strip()]
        preview = render_visible_preview(
            image_array,
            mode=mode,
            signature_text=signature_text,
            signature_position=signature_position,
            blur_bar_enabled=main_blur_bar_enabled,
            blur_bar_text=blur_bar_text,
            blur_bar_y_ratio=blur_bar_y_ratio,
            blur_bar_sigma=blur_bar_sigma,
            blur_bar_count=blur_bar_count,
            blur_region_mask=blur_region_arr,
            emboss_enabled=_bool(emboss_enabled),
            emboss_pattern=emboss_pattern,
            emboss_text=emboss_text,
            emboss_text_density=emboss_text_density,
            emboss_strength=emboss_strength,
            displacement_enabled=main_displacement_enabled,
            displacement_text=displacement_text,
            displacement_shift=displacement_shift,
            displacement_density=displacement_density,
            displacement_font_ratio=displacement_font_ratio,
            displacement_mode=displacement_mode,
            displacement_seed=displacement_seed,
            displacement_shadow=_bool(displacement_shadow),
            displacement_shadow_strength=displacement_shadow_strength,
            displacement_anchor_x=displacement_anchor_x,
            displacement_anchor_y=displacement_anchor_y,
            face_emboss_enabled=main_face_emboss_enabled,
            face_emboss_text=face_emboss_text,
            face_emboss_copies=face_emboss_copies,
            face_emboss_seed=face_emboss_seed,
            face_emboss_patch_ratio=face_emboss_patch_ratio,
            face_emboss_shift=face_emboss_shift,
            face_emboss_opacity=face_emboss_opacity,
            jw_footer_preview=_bool(jw_footer_preview),
            jw_footer_artist=jw_footer_artist,
            jw_creation=jw_creation,
            jw_restrictions=restriction_ids,
            stealth_surface=preview_stealth_surface,
            max_side=preview_max_side,
            halftone_enabled=_bool(halftone_enabled),
            halftone_style=halftone_style,
            halftone_text=halftone_text,
            halftone_size=halftone_size,
            halftone_density=halftone_density,
            halftone_visibility=halftone_visibility,
            halftone_anchor_x=_ht_ax,
            halftone_anchor_y=_ht_ay,
            halftone_signature=halftone_signature,
            halftone_signature_size=halftone_signature_size,
            halftone_dot_texture=halftone_dot_texture,
            halftone_background_chain=halftone_background_chain,
            halftone_contour_warp=halftone_contour_warp,
            halftone_credit_faint=_ascii_faint,
            logo_rgba=preview_logo,
            logo_opacity=logo_opacity,
            logo_scale=logo_scale,
            logo_position=logo_position,
            logo_anchor_x=logo_anchor_x,
            logo_anchor_y=logo_anchor_y,
            logo_tint=logo_tint,
            logo_shift_px=logo_shift_px,
        )

        from core.visible_preview import downscale_for_preview

        preview_work, _ = downscale_for_preview(image_array, preview_max_side)

        erase_mask_arr, add_blur_arr = await _read_visible_edit_masks(
            preview_work, visible_erase_mask, visible_add_blur_mask,
        )
        add_placements: list[dict] = _ht_placements
        if not add_placements and visible_add_points.strip():
            from core.visible_edit import parse_add_placements

            add_placements = parse_add_placements(visible_add_points)

        preview = _apply_visible_edits_to_frame(
            preview_work,
            preview,
            erase_mask_arr=erase_mask_arr,
            add_placements=add_placements,
            add_blur_arr=add_blur_arr,
            displacement_enabled=_bool(displacement_enabled),
            displacement_text=displacement_text,
            displacement_shift=displacement_shift,
            displacement_font_ratio=displacement_font_ratio,
            displacement_seed=displacement_seed,
            displacement_shadow=_bool(displacement_shadow),
            displacement_shadow_strength=displacement_shadow_strength,
            blur_bar_enabled=_bool(blur_bar_enabled),
            blur_bar_text=blur_bar_text,
            blur_bar_sigma=blur_bar_sigma,
            emboss_enabled=_bool(emboss_enabled),
            emboss_pattern=emboss_pattern,
            emboss_strength=emboss_strength,
            emboss_text=emboss_text,
            emboss_text_density=emboss_text_density,
            face_emboss_enabled=_bool(face_emboss_enabled),
            face_emboss_text=face_emboss_text,
            face_emboss_shift=face_emboss_shift,
            face_emboss_opacity=face_emboss_opacity,
            face_emboss_seed=face_emboss_seed,
        )

        _track_id = _resolve_track_artist(
            track_artist=track_artist,
            artist=artist,
            dwt_payload=(dwt_payload or "").strip(),
            watermark_text=(watermark_text or "").strip(),
            signature_text=(signature_text or "").strip(),
            halftone_text=(halftone_text or "").strip(),
        )
        if _bool(track_enabled) and _track_id:
            from core.jw_anchor import anchor_size_ok, embed_anchor_signature

            if anchor_size_ok(preview):
                when = int(time.time()) if _bool(auto_timestamp) else 0
                preview = embed_anchor_signature(
                    np.ascontiguousarray(preview), _track_id, when, region="full",
                )

        buf = io.BytesIO()
        from core.color_profile import srgb_icc_bytes

        save_kw: dict = {"quality": 98 if _halftone_on else 95, "optimize": True}
        icc = srgb_icc_bytes()
        if icc:
            save_kw["icc_profile"] = icc
        Image.fromarray(preview).save(buf, format="JPEG", **save_kw)
        img_b64 = base64.b64encode(buf.getvalue()).decode()
        return JSONResponse({"ok": True, "preview": f"data:image/jpeg;base64,{img_b64}"})
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse(
            {
                "ok": False,
                "error_code": PREVIEW_FAILED,
                "error": f"预览失败：{exc}",
            },
            status_code=500,
        )


@router.post("/protect/holo-clip")
async def protect_holo_clip(
    request: Request,
    image: UploadFile = File(...),
) -> Response:
    """Record the real HoloCard CSS on a protected still and return an MP4."""
    check_rate_limit(request, "protect", rate_limit_protect_per_min())
    try:
        image_array, _ = _read_upload(image)
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    check_image_pixels(image_array)
    try:
        _validate_image(image_array)
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    try:
        mp4 = export_holo_mp4_from_image(image_array)
    except HoloCaptureError as exc:
        return JSONResponse(
            {
                "ok": False,
                "error_code": HOLO_CAPTURE_UNAVAILABLE,
                "error": str(exc),
            },
            status_code=503,
        )
    except Exception as exc:
        return JSONResponse(
            {
                "ok": False,
                "error_code": HOLO_CAPTURE_FAILED,
                "error": f"闪卡录制失败：{exc}",
            },
            status_code=500,
        )
    stem = Path(image.filename or "").stem.strip() or "jingwei"
    disposition = "attachment; filename*=UTF-8''" + quote(f"{stem}_holo.mp4")
    return Response(
        content=mp4,
        media_type="video/mp4",
        headers={"Content-Disposition": disposition},
    )
