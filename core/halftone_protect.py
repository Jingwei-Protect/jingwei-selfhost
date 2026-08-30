"""产品化半调/字符防盗层：将 ProtectPage UI 参数映射为 ``apply_ascii_watermark`` kwargs。"""



from __future__ import annotations



from typing import Literal



import numpy as np



from core.ascii_watermark import apply_ascii_watermark



HalftoneStyle = Literal["ascii_chars", "halftone_dots"]

DotPreset = Literal["author_dots", "fine_full"]



# 与 evaluation PRIMARY preset 对齐的基准常量（author_text 运行时注入）

_HT_V2 = dict(

    lum_mask="lum_ramp",

    mask_full_below=198.0,

    mask_fade_end=248.0,

    mask_bright_floor=0.14,

    grid_passes=1,

    dark_contrast_boost=0.78,

    dark_alpha_boost=0.30,

    use_halftone_ramp=True,

    dither="bayer",

    dither_strength=0.72,

    render_font_size=15,

    halftone_gate=False,

)





def _lerp_ui(value: int, lo: float, hi: float) -> float:

    """将 UI 滑块 0–100 线性映射到 ``[lo, hi]``。"""

    t = float(np.clip(value, 0, 100)) / 100.0

    return lo + t * (hi - lo)





def _lerp_ui_int(value: int, lo: int, hi: int) -> int:

    return int(round(_lerp_ui(value, float(lo), float(hi))))





def _lerp_ui_int_inv(value: int, lo: int, hi: int) -> int:

    """密度类滑块：值越大 → 输出越小（更密）。"""

    return int(round(_lerp_ui(value, float(hi), float(lo))))





HALFTONE_REF_LONG_SIDE = 1280
_HALFTONE_REF_LONG_SIDE = HALFTONE_REF_LONG_SIDE

# 半调字符：产品固定开启（与内部标准导出一致，不可通过 UI 关闭）
_ASCII_BACKGROUND_CHAIN = 78
_ASCII_CONTOUR_WARP = 70


def halftone_resolution_scale(h: int, w: int) -> float:
    """UI 滑块按 ``_HALFTONE_REF_LONG_SIDE`` 标定；大图按比例放大网格，保证预览≈成图。"""
    return max(int(h), int(w), 1) / float(_HALFTONE_REF_LONG_SIDE)


def _scale_halftone_kwargs_for_resolution(kwargs: dict, h: int, w: int) -> dict:
    """将 cell/字号/点半径等按长边相对 1280px 缩放，使不同分辨率下视觉比例一致。

    ``halftone_size`` 为相对 cell 的无量纲倍率，不参与缩放（cell 已缩放）。
    """
    scale = halftone_resolution_scale(h, w)
    if abs(scale - 1.0) < 0.02:
        return kwargs
    out = dict(kwargs)
    if "cell_size" in out:
        out["cell_size"] = max(8, int(round(int(out["cell_size"]) * scale)))
    if "render_font_size" in out:
        out["render_font_size"] = max(8, int(round(int(out["render_font_size"]) * scale)))
    if "author_fine_step" in out:
        out["author_fine_step"] = max(2, int(round(int(out["author_fine_step"]) * scale)))
    if "author_dot_radius" in out:
        out["author_dot_radius"] = max(1, int(round(int(out["author_dot_radius"]) * scale)))
    return out


def _ascii_render_font_size(cell_size: int, size: int) -> int:
    """字符大小：50 = 1.0×cell（默认）；0 ≈ 0.55×；100 ≈ 2.0×。

    以 50 为基准向两端拉伸，避免 50→100 仅 ~55% 增幅导致预览几乎无感。
    """
    cell = max(8, int(cell_size))
    sz = float(np.clip(size, 0, 100))
    if sz <= 50.0:
        frac = 0.55 + (sz / 50.0) * (1.0 - 0.55)
    else:
        frac = 1.0 + ((sz - 50.0) / 50.0) * (2.0 - 1.0)
    return max(8, int(round(cell * frac)))


def _visibility_params(visibility: int) -> dict[str, float]:

    """可见度：联动 local_contrast 与 opacity（字符款）。"""

    return {

        "local_contrast": _lerp_ui(visibility, 0.17, 0.32),

        "opacity": _lerp_ui(visibility, 0.91, 0.98),

    }


def _visibility_params_halftone_dots(visibility: int) -> dict[str, float]:
    """波点款明度：可压低肉眼可见度，但保留最小像素扰动以防「除署名外零防御」。

    波点本身无字形信息；若 local_contrast / screen_mix 过低，AI 复原几乎不受影响。
    因此明度下限高于字符款，且联动 halftone_screen_mix 与暗部 boost。
    """
    vis = int(np.clip(visibility, 0, 100))
    return {
        "local_contrast": _lerp_ui(vis, 0.26, 0.34),
        "opacity": _lerp_ui(vis, 0.92, 0.98),
        "halftone_screen_mix": _lerp_ui(vis, 0.15, 0.22),
        "dark_contrast_boost": _lerp_ui(vis, 0.74, 0.86),
        "dark_alpha_boost": _lerp_ui(vis, 0.30, 0.42),
    }





def _signature_size_params(signature_size: int) -> dict[str, float | int]:
    """署名物理大小：mask 缩放与细点半径，不影响背景网格。"""
    sz = int(np.clip(signature_size, 0, 100))
    return {
        "author_mask_scale": _lerp_ui(sz, 0.55, 1.35),
        "author_dot_radius": _lerp_ui_int(sz, 1, 3),
    }


def _signature_visibility_params(signature: int, *, preset: DotPreset | None) -> dict[str, float]:

    """署名明显度：仅对比/透明度/字母占比，不改署名物理尺寸。"""

    sig = int(np.clip(signature, 0, 100))

    if preset is None:

        # ascii_chars — 仅署名区顺序链；背景链由 _background_chain_params 单独控制

        return {

            "author_name_contrast": _lerp_ui(sig, 0.28, 0.62),

            "author_sequence_rate": _lerp_ui(sig, 0.10, 0.48),

            "author_inject_rate": _lerp_ui(sig, 0.03, 0.14),

        }

    if preset == "author_dots":

        return {

            "author_name_contrast": _lerp_ui(sig, 0.32, 0.68),

            "author_mask_opacity": _lerp_ui(sig, 0.88, 0.99),

        }

    return {

        "author_name_contrast": _lerp_ui(sig, 0.32, 0.68),

        "fine_dot_name_boost": _lerp_ui(sig, 0.10, 0.32),

    }





def _background_chain_params(background_chain: int) -> dict[str, float | int]:
    """背景作者顺序链：随机注入 + 固定步长确定性拼名。"""
    bc = int(np.clip(background_chain, 0, 100))
    if bc <= 0:
        return {
            "author_background_sequence_rate": 0.0,
            "author_background_inject_rate": 0.0,
            "author_background_chain_stride": 0,
        }
    stride = max(4, int(round(_lerp_ui(bc, 20, 5))))
    return {
        "author_background_sequence_rate": _lerp_ui(bc, 0.10, 0.45),
        "author_background_inject_rate": _lerp_ui(bc, 0.03, 0.12),
        "author_background_chain_stride": stride,
    }


def _contour_warp_params(contour_warp: int) -> dict[str, float]:
    """边缘感知网格错位强度（0=规则竖排，100=沿轮廓最大错位）。"""
    cw = int(np.clip(contour_warp, 0, 100))
    return {"contour_warp_strength": _lerp_ui(cw, 0.0, 1.0)}





def normalize_halftone_style(style: str, dot_texture: int = 0) -> tuple[HalftoneStyle | str, int]:

    """兼容旧 API ``author_dots`` / ``fine_full``，统一为 ``halftone_dots`` + 纹理滑块。"""

    if style == "author_dots":

        return "halftone_dots", 0

    if style == "fine_full":

        return "halftone_dots", 100

    if style == "halftone_dots":

        return "halftone_dots", int(np.clip(dot_texture, 0, 100))

    return style, dot_texture





def dot_preset_from_texture(dot_texture: int) -> DotPreset:

    """纹理 0=局部署名粒子，100=全页细点底纹。"""

    return "fine_full" if int(np.clip(dot_texture, 0, 100)) >= 50 else "author_dots"





def _anchor_params(
    style: str,
    anchor_x: float,
    anchor_y: float,
) -> dict[str, float | str]:
    """半调/字符风格均支持自定义署名锚点；未指定时 center_low。"""
    _ = style
    if anchor_x >= 0.0 and anchor_y >= 0.0:
        return {
            "author_mask_position": "custom",
            "author_anchor_x": float(np.clip(anchor_x, 0.0, 1.0)),
            "author_anchor_y": float(np.clip(anchor_y, 0.0, 1.0)),
        }
    return {"author_mask_position": "center_low"}


def resolve_halftone_anchor_from_placements(
    placements: list[dict] | None,
    *,
    anchor_x: float = -1.0,
    anchor_y: float = -1.0,
) -> tuple[float, float]:
    """解析半调署名锚点。

    优先 ``halftone_anchor_x/y`` 表单字段（前端 ``resolveHalftoneAnchor`` 写入），
    其次 ``visible_add_points`` 中的 ``halftone_signature``。

    表单优先是为避免 ``visible_add_points`` 仍带默认中心 (0.5, 0.54) 时，
    把用户已拖放到其它位置的署名又渲染回画面正中。
    """
    if anchor_x >= 0.0 and anchor_y >= 0.0:
        return (
            float(np.clip(anchor_x, 0.0, 1.0)),
            float(np.clip(anchor_y, 0.0, 1.0)),
        )
    for p in placements or []:
        if str(p.get("layer", "")) == "halftone_signature":
            return (
                float(np.clip(float(p["x"]), 0.0, 1.0)),
                float(np.clip(float(p["y"]), 0.0, 1.0)),
            )
    return -1.0, -1.0





def _base_ascii_chars(author_text: str) -> dict:

    return dict(

        cell_size=14,

        opacity=0.96,

        color_mode="local",

        local_contrast=0.26,

        stroke_width=0,

        mode="author_luminance",

        author_text=author_text,

        seed=42,

        layout="grid",

        random_scale=0.0,

        author_inject_rate=0.08,

        author_sequence_rate=0.32,

        author_background_sequence_rate=0.08,

        author_background_inject_rate=0.03,

        author_background_chain_stride=8,

        contour_warp_strength=0.55,

        density_jitter=0,

        author_mask_mode="fine_dots",

        author_mask_position="center_low",

        author_mask_scale=0.95,

        author_mask_opacity=0.98,

        author_fine_step=3,

        author_dot_radius=2,

        author_name_contrast=0.52,

        author_tile_contrast=0.088,

        author_tile_alpha_scale=0.45,

        author_mask_tile_spacing=0.35,

        **_HT_V2,

    )





def _base_author_dots(author_text: str) -> dict:

    return dict(

        cell_size=16,

        opacity=0.96,

        color_mode="local",

        local_contrast=0.26,

        stroke_width=0,

        mode="luminance",

        author_text=author_text,

        seed=17,

        layout="halftone",

        halftone_size=1.0,

        halftone_screen_mix=0.18,

        halftone_radius_cap=0.88,

        halftone_min_radius=0.28,

        grid_passes=1,

        lum_mask="lum_ramp",

        mask_full_below=198.0,

        mask_fade_end=248.0,

        mask_bright_floor=0.14,

        dark_contrast_boost=0.78,

        dark_alpha_boost=0.35,

        author_mask_mode="fine_stealth",

        author_mask_scale=0.95,

        author_mask_opacity=0.98,

        author_fine_step=3,

        author_dot_radius=2,

        author_name_contrast=0.52,

        author_tile_contrast=0.088,

        author_tile_alpha_scale=0.45,

        author_zone_mask_floor=0.65,

        author_zone_pad_cells=5.0,

        author_bbox_halftone_pad=5.0,

    )





def _base_fine_full(author_text: str) -> dict:

    return dict(

        cell_size=16,

        opacity=0.96,

        color_mode="local",

        local_contrast=0.24,

        stroke_width=0,

        mode="luminance",

        author_text=author_text,

        seed=41,

        layout="halftone",

        grid_passes=1,

        lum_mask="lum_ramp",

        mask_full_below=198.0,

        mask_fade_end=248.0,

        mask_bright_floor=0.14,

        author_mask_mode="fine_full",

        author_mask_scale=0.95,

        author_mask_opacity=0.98,

        author_fine_step=3,

        author_dot_radius=2,

        fine_dot_base_contrast=0.12,

        fine_dot_name_boost=0.22,

        author_zone_mask_floor=0.65,

        author_zone_pad_cells=5.0,

        author_bbox_halftone_pad=5.0,

    )





def resolve_halftone_kwargs(

    style: str,

    *,

    author_text: str,

    size: int = 50,

    density: int = 50,

    visibility: int = 50,

    anchor_x: float = -1.0,

    anchor_y: float = -1.0,

    signature: int = 50,

    signature_size: int = 50,

    dot_texture: int = 0,

    advanced: int | None = None,

    background_chain: int = 78,

    contour_warp: int = 70,

    credit_faint: bool = False,

    image: np.ndarray | None = None,

) -> dict:

    """将 ProtectPage UI 参数解析为 ``apply_ascii_watermark`` 关键字参数。



    ``size`` / ``density`` 仅控制字符或波点网格，不含署名尺寸。

    ``signature_size`` 仅调节署名区域物理大小，不含背景网格。

    ``signature`` 仅调节署名明显度（对比/透明度/字母占比），不改物理大小。

    ``dot_texture`` 仅对 ``halftone_dots`` 有效：0=局部署名，100=全页细点。

    """

    text = author_text.strip()

    if not text:

        raise ValueError("halftone_text required when halftone layer is enabled")



    sig = signature if advanced is None else advanced

    norm_style, texture = normalize_halftone_style(style, dot_texture)



    if norm_style == "ascii_chars":

        kwargs = _base_ascii_chars(text)

        cell = _lerp_ui_int(density, 8, 28)

        kwargs["cell_size"] = cell

        kwargs["render_font_size"] = _ascii_render_font_size(cell, size)

        kwargs.update(_signature_visibility_params(sig, preset=None))

    elif norm_style == "halftone_dots":

        preset = dot_preset_from_texture(texture)

        if preset == "author_dots":

            kwargs = _base_author_dots(text)

            kwargs["halftone_size"] = _lerp_ui(size, 0.32, 2.55)

            kwargs["halftone_min_radius"] = _lerp_ui(size, 0.42, 0.16)

            kwargs["halftone_radius_cap"] = _lerp_ui(size, 0.74, 1.0)

            kwargs["cell_size"] = _lerp_ui_int_inv(density, 10, 30)

            kwargs.update(_signature_visibility_params(sig, preset="author_dots"))

        else:

            kwargs = _base_fine_full(text)

            kwargs["cell_size"] = _lerp_ui_int(size, 8, 34)

            kwargs["author_fine_step"] = _lerp_ui_int(density, 2, 8)

            kwargs["fine_dot_base_contrast"] = _lerp_ui(density, 0.06, 0.16)

            kwargs.update(_signature_visibility_params(sig, preset="fine_full"))

    else:

        raise ValueError(f"unknown halftone style: {style!r}")



    if norm_style == "halftone_dots":
        kwargs.update(_visibility_params_halftone_dots(visibility))
    else:
        kwargs.update(_visibility_params(visibility))

    kwargs.update(_signature_size_params(signature_size))

    kwargs.update(_anchor_params(norm_style, anchor_x, anchor_y))

    if norm_style == "ascii_chars":
        kwargs.update(_background_chain_params(_ASCII_BACKGROUND_CHAIN))
        kwargs.update(_contour_warp_params(_ASCII_CONTOUR_WARP))
        if credit_faint:
            from core.credit_mode import resolve_credit_ascii_faint_kwargs

            kwargs.update(resolve_credit_ascii_faint_kwargs(image, text))
            # Faint recipe pins the default name to center_low; re-apply so a
            # user corner / drag still wins.
            kwargs.update(_anchor_params(norm_style, anchor_x, anchor_y))

    return kwargs





def apply_halftone_protect(

    image: np.ndarray,

    *,

    style: str = "ascii_chars",

    author_text: str = "",

    size: int = 50,

    density: int = 50,

    visibility: int = 50,

    anchor_x: float = -1.0,

    anchor_y: float = -1.0,

    signature: int = 50,

    signature_size: int = 50,

    dot_texture: int = 0,

    advanced: int | None = None,

    background_chain: int = 78,

    contour_warp: int = 70,

    render_long_side: int | None = None,

    credit_faint: bool = False,

) -> np.ndarray:

    """在 RGB 图像上叠加所选半调/字符防盗层。

    长边超过 ``render_long_side`` 时先在参考分辨率渲染再放大，与预览帧一致。
    """

    import cv2

    kwargs = resolve_halftone_kwargs(

        style,

        author_text=author_text,

        size=size,

        density=density,

        visibility=visibility,

        anchor_x=anchor_x,

        anchor_y=anchor_y,

        signature=signature,

        signature_size=signature_size,

        dot_texture=dot_texture,

        advanced=advanced,

        background_chain=background_chain,

        contour_warp=contour_warp,

        credit_faint=credit_faint,

        image=image,

    )

    h, w = image.shape[:2]
    ref = max(64, int(render_long_side or HALFTONE_REF_LONG_SIDE))
    long_side = max(h, w)

    if long_side > ref * 1.05:
        sc = ref / float(long_side)
        dw = max(64, int(round(w * sc)))
        dh = max(64, int(round(h * sc)))
        work = cv2.resize(image, (dw, dh), interpolation=cv2.INTER_AREA)
        wh, ww = work.shape[:2]
        work_kw = _scale_halftone_kwargs_for_resolution(kwargs, wh, ww)
        rendered = apply_ascii_watermark(work, **work_kw)
        return cv2.resize(rendered, (w, h), interpolation=cv2.INTER_CUBIC)

    kwargs = _scale_halftone_kwargs_for_resolution(kwargs, h, w)

    return apply_ascii_watermark(image, **kwargs)

