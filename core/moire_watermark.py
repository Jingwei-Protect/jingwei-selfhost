"""可见摩尔纹水印 — 双光栅干涉 + 坐标扭曲。

与 ``jumping_moire`` / ``texture_pollution`` 的隐形扰动不同，本模块生成
**肉眼可见** 的干涉波纹（参考小红书类摩尔纹截图），用于 ASCII 实验 preset。

仅依赖 numpy、Pillow；复用 ``ascii_watermark`` 的署名细点绘制。
"""

from __future__ import annotations

import math
from typing import Literal

import numpy as np
from PIL import Image, ImageDraw

from core.ascii_watermark import (
    AuthorMaskPosition,
    _build_author_dot_mask,
    _paint_author_fine_dots,
)

MoireMode = Literal["swirl", "wave"]


def _validate_input(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    h, w = image.shape[:2]
    if h < 32 or w < 32:
        raise ValueError(f"Image must be at least 32×32, got {h}×{w}.")


def _warp_swirl(
    xx: np.ndarray,
    yy: np.ndarray,
    img_w: int,
    img_h: int,
    strength: float,
) -> tuple[np.ndarray, np.ndarray]:
    """径向扭曲 + 螺旋，模拟截图中的漩涡摩尔纹。"""
    cx = img_w * 0.5
    cy = img_h * 0.5
    dx = (xx - cx) / max(img_w, 1)
    dy = (yy - cy) / max(img_h, 1)
    r = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(dy, dx)
    s = float(np.clip(strength, 0.2, 3.0))
    twist = s * (1.15 - np.clip(r * 1.6, 0.0, 1.05))
    ripple = 0.035 * s * np.sin(r * 22.0 + theta * 4.0)
    r_w = np.clip(r + ripple, 0.0, 1.35)
    scale = max(img_w, img_h)
    xx_w = cx + r_w * scale * np.cos(theta + twist * 0.38)
    yy_w = cy + r_w * scale * np.sin(theta + twist * 0.38)
    return xx_w.astype(np.float32), yy_w.astype(np.float32)


def _warp_wave(
    xx: np.ndarray,
    yy: np.ndarray,
    amplitude: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """正弦流场扭曲，模拟木纹式流动摩尔纹。"""
    amp = float(np.clip(amplitude, 2.0, 40.0))
    f1 = 0.020 + float(rng.uniform(-0.004, 0.004))
    f2 = 0.016 + float(rng.uniform(-0.004, 0.004))
    xx_w = xx + amp * np.sin(yy * f1 + float(rng.uniform(0, math.tau)))
    yy_w = yy + amp * 0.72 * np.sin(xx * f2 + 1.1)
    return xx_w.astype(np.float32), yy_w.astype(np.float32)


def _generate_visible_moire_field(
    img_h: int,
    img_w: int,
    *,
    mode: MoireMode,
    frequency: float,
    swirl_strength: float,
    wave_amplitude: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """生成 [-1, 1] 干涉场。

    ``swirl``：双光栅 × 环形分量，偏圆形漩涡（截图 B）。
    ``wave``：双光栅 + 流场扭曲，偏流动波纹（截图 A）。
    """
    freq_norm = 0.06 + float(np.clip(frequency, 0.0, 1.0)) * 0.20
    k = freq_norm * 2.0 * math.pi

    yy, xx = np.meshgrid(
        np.arange(img_h, dtype=np.float32),
        np.arange(img_w, dtype=np.float32),
        indexing="ij",
    )

    if mode == "swirl":
        xx_w, yy_w = _warp_swirl(xx, yy, img_w, img_h, swirl_strength)
    else:
        xx_w, yy_w = _warp_wave(xx, yy, wave_amplitude, rng)

    theta1 = float(rng.uniform(0.0, math.pi))
    theta2 = theta1 + float(rng.uniform(0.12, 0.32 if mode == "swirl" else 0.20))
    phase1 = float(rng.uniform(0.0, math.tau))
    phase2 = float(rng.uniform(0.0, math.tau))
    phase3 = float(rng.uniform(0.0, math.tau))

    g1 = np.sin(k * (xx_w * math.cos(theta1) + yy_w * math.sin(theta1)) + phase1)
    g2 = np.sin(k * (xx_w * math.cos(theta2) + yy_w * math.sin(theta2)) + phase2)

    if mode == "swirl":
        cx, cy = img_w * 0.5, img_h * 0.5
        r = np.sqrt((xx_w - cx) ** 2 + (yy_w - cy) ** 2)
        g3 = np.sin(k * 0.75 * r * 0.045 + phase3)
        pattern = 0.42 * g1 * g2 + 0.58 * g3
    else:
        g3 = np.sin(k * 0.65 * xx_w * 0.014 + k * 0.35 * yy_w * 0.011 + phase3)
        pattern = 0.55 * g1 * g2 + 0.45 * g3

    pmax = float(np.max(np.abs(pattern)))
    if pmax > 1e-6:
        pattern = pattern / pmax
    return pattern.astype(np.float32)


def _apply_moire_modulation(
    image: np.ndarray,
    pattern: np.ndarray,
    *,
    opacity: float,
    local_contrast: float,
) -> np.ndarray:
    """按干涉场调制亮度，保留底色色相。"""
    op = float(np.clip(opacity, 0.0, 0.45))
    lc = float(np.clip(local_contrast, 0.0, 0.55))
    amp = op * (22.0 + lc * 90.0)
    shift = pattern * amp

    img_f = image.astype(np.float32)
    lum = (
        img_f[..., 0] * 0.299
        + img_f[..., 1] * 0.587
        + img_f[..., 2] * 0.114
    )
    new_lum = np.clip(lum - shift, 0.0, 255.0)
    ratio = np.where(lum > 1.5, new_lum / lum, 1.0)
    out = np.clip(img_f * ratio[..., np.newaxis], 0.0, 255.0)
    return out.astype(np.uint8)


def apply_moire_watermark(
    image: np.ndarray,
    *,
    mode: MoireMode = "swirl",
    opacity: float = 0.16,
    frequency: float = 0.52,
    swirl_strength: float = 1.5,
    wave_amplitude: float = 14.0,
    local_contrast: float = 0.24,
    author_text: str = "",
    author_mask_position: AuthorMaskPosition = "center_low",
    author_mask_scale: float = 0.95,
    author_fine_step: int = 3,
    author_dot_radius: int = 2,
    author_name_contrast: float = 0.52,
    seed: int = 42,
) -> np.ndarray:
    """叠加可见摩尔纹；``author_text`` 非空时绘制居中署名细点。"""
    _validate_input(image)
    if opacity <= 0.0:
        return image.copy()

    h, w = image.shape[:2]
    rng = np.random.default_rng(seed)
    pattern = _generate_visible_moire_field(
        h, w,
        mode=mode,
        frequency=frequency,
        swirl_strength=swirl_strength,
        wave_amplitude=wave_amplitude,
        rng=rng,
    )
    out = _apply_moire_modulation(
        image, pattern, opacity=opacity, local_contrast=local_contrast,
    )

    author = author_text.strip()
    if not author:
        return out

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    cell = max(12, int(min(h, w) * 0.018))
    _, pixel_mask, bbox = _build_author_dot_mask(
        author,
        img_w=w,
        img_h=h,
        cell_w=cell,
        cell_h=cell,
        position=author_mask_position,
        mask_scale=author_mask_scale,
    )
    sign_alpha = int(np.clip(opacity, 0.0, 1.0) * 255 * 0.96)
    _paint_author_fine_dots(
        draw,
        out,
        pixel_mask,
        bbox,
        fine_step=author_fine_step,
        dot_radius=author_dot_radius,
        alpha_byte=sign_alpha,
        name_contrast=author_name_contrast,
        color_mode="local",
        fixed_color=(40, 40, 40),
        img_w=w,
        img_h=h,
    )
    base = Image.fromarray(out).convert("RGBA")
    composed = Image.alpha_composite(base, overlay)
    return np.array(composed.convert("RGB"), dtype=np.uint8)
