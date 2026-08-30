"""Live 反光帧生成：镭射闪卡（全息光栅 + 锐利扫光带）动效。

算法原理（无深度学习）：
1. 多层细周期光栅模拟镭射衍射条纹，色相随空间相位变化呈彩虹色；
2. 窄条扫光带沿对角线滑过，扫过区域叠加强烈高光；
3. 对画面内容灌注迷幻镭射箔纹理（多层干涉光栅 + soft-light 烙入像素），像整张图覆镭射膜；
4. 全帧保留低强度底纹 + 稀疏星芒，确保首尾及任意单帧都不会退回「完全无镭射」原图；
5. 加法混合 + 硬边遮罩，避免 screen 柔光造成的雾蒙蒙观感。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

Intensity = Literal["light", "medium", "strong"]

_INTENSITY_PRESETS: dict[Intensity, dict[str, float]] = {
    "light": {
        "band_width": 0.11,
        "sweep_gain": 0.48,
        "grating_gain": 0.45,
        "baseline_grating_gain": 0.11,
        "sparkle_gain": 0.40,
        "baseline_sparkle_gain": 0.18,
        "content_holo_gain": 0.48,
        "n_gratings": 2,
        "n_sparkles": 45,
    },
    "medium": {
        "band_width": 0.15,
        "sweep_gain": 0.62,
        "grating_gain": 0.58,
        "baseline_grating_gain": 0.15,
        "sparkle_gain": 0.52,
        "baseline_sparkle_gain": 0.22,
        "content_holo_gain": 0.65,
        "n_gratings": 3,
        "n_sparkles": 70,
    },
    "strong": {
        "band_width": 0.19,
        "sweep_gain": 0.78,
        "grating_gain": 0.72,
        "baseline_grating_gain": 0.19,
        "sparkle_gain": 0.68,
        "baseline_sparkle_gain": 0.28,
        "content_holo_gain": 0.82,
        "n_gratings": 4,
        "n_sparkles": 95,
    },
}


@dataclass(frozen=True)
class LiveGlareResult:
    """反光帧序列及帧挑选结果。"""

    frames: list[np.ndarray]
    key_index: int
    worst_index: int
    affected_ratios: list[float]
    duration_s: float
    fps: int
    intensity: Intensity
    seed: int


def _validate_rgb(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError("image must be uint8.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Expected HxWx3 RGB, got shape {image.shape}.")
    h, w = image.shape[:2]
    if h < 8 or w < 8:
        raise ValueError(f"Image must be at least 8x8, got {h}x{w}.")


def _smooth_path(
    rng: np.random.Generator,
    n_frames: int,
    *,
    low: float,
    high: float,
) -> np.ndarray:
    """生成非周期平滑路径：随机控制点 + 线性插值。"""
    n_ctrl = max(4, n_frames // 3)
    ctrl_t = np.linspace(0.0, 1.0, n_ctrl)
    ctrl_v = rng.uniform(low, high, size=n_ctrl)
    frame_t = np.linspace(0.0, 1.0, n_frames)
    return np.interp(frame_t, ctrl_t, ctrl_v)


def _hsv_to_rgb(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> np.ndarray:
    """向量化 HSV→RGB，h∈[0,1]。"""
    h6 = (h % 1.0) * 6.0
    i = np.floor(h6).astype(np.int32) % 6
    f = h6 - np.floor(h6)
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))

    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1)


def _projection_grid(h: int, w: int, angle_deg: float) -> np.ndarray:
    """沿 angle 方向的坐标投影（用于光栅与扫光）。"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rad = np.deg2rad(angle_deg)
    cos_a, sin_a = float(np.cos(rad)), float(np.sin(rad))
    return xx * cos_a + yy * sin_a


def _rgb_to_hsv(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """RGB [0,1] → HSV，h∈[0,1]。"""
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]
    maxc = np.max(rgb, axis=-1)
    minc = np.min(rgb, axis=-1)
    v = maxc
    delta = maxc - minc
    s = np.where(maxc > 1e-6, delta / maxc, 0.0)

    safe_delta = np.where(delta > 1e-6, delta, 1.0)
    rc = (maxc - r) / safe_delta
    gc = (maxc - g) / safe_delta
    bc = (maxc - b) / safe_delta

    h = np.zeros_like(maxc)
    h = np.where(delta > 1e-6, np.where(maxc == r, (bc - gc) % 6.0, h), h)
    h = np.where((delta > 1e-6) & (maxc == g), (rc - bc) + 2.0, h)
    h = np.where((delta > 1e-6) & (maxc == b), (gc - rc) + 4.0, h)
    h = (h / 6.0) % 1.0
    return h.astype(np.float32), s.astype(np.float32), v.astype(np.float32)


def _soft_light_rgb(base: np.ndarray, blend: np.ndarray) -> np.ndarray:
    """Soft-light 混合，base/blend ∈ [0,1]。"""
    out = np.where(
        blend <= 0.5,
        base - (1.0 - 2.0 * blend) * base * (1.0 - base),
        base + (2.0 * blend - 1.0) * (np.sqrt(np.clip(base, 0, 1)) - base),
    )
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def _image_luminance(image: np.ndarray) -> np.ndarray:
    """归一化亮度 [0,1]。"""
    gray = (
        image[..., 0].astype(np.float32) * 0.299
        + image[..., 1].astype(np.float32) * 0.587
        + image[..., 2].astype(np.float32) * 0.114
    )
    return np.clip(gray / 255.0, 0.0, 1.0).astype(np.float32)


def _build_psychedelic_foil_texture(
    h: int,
    w: int,
    *,
    phase: float,
    diag: float,
    foil_angles: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """生成迷幻镭射箔纹理：交叉微光栅 + 干涉彩虹色斑。

    Returns
    -------
    tex_rgb:
        float32 H×W×3，彩虹纹理色。
    tex_strength:
        float32 H×W，纹理可见度。
    """
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    inv_diag = 1.0 / max(diag, 1.0)

    f_fine = 2.0 * np.pi / max(diag * 0.014, 2.0)
    f_mid = 2.0 * np.pi / max(diag * 0.028, 2.0)
    f_coarse = 2.0 * np.pi / max(diag * 0.055, 2.0)

    a1, a2, a3 = float(foil_angles[0]), float(foil_angles[1]), float(foil_angles[2])
    u1 = xx * np.cos(a1) + yy * np.sin(a1)
    u2 = xx * np.cos(a2) + yy * np.sin(a2)
    u3 = xx * np.cos(a3) + yy * np.sin(a3)

    line1 = np.sin(u1 * f_fine + phase)
    line2 = np.sin(u2 * f_fine * 1.08 - phase * 0.78)
    line3 = np.sin(u3 * f_mid + phase * 1.12)
    diamond = np.sin(u1 * f_mid * 0.55 + phase * 0.4) * np.sin(u2 * f_mid * 0.55 - phase * 0.35)

    swirl = np.sin(xx * inv_diag * 7.5 + phase) * np.sin(yy * inv_diag * 8.2 - phase * 0.9)
    warp = np.sin((xx + yy * 0.7) * inv_diag * 5.5 + phase * 1.15)
    ripple = np.sin(np.hypot(xx - w * 0.5, yy - h * 0.5) * f_coarse * 0.35 + phase * 0.6)

    interference = (
        line1 * line2 * 0.38
        + line3 * 0.22
        + diamond * 0.42
        + swirl * 0.34
        + warp * 0.28
        + ripple * 0.24
    )
    field = (interference + 1.0) * 0.5

    micro = (
        np.abs(np.sin(u1 * f_fine * 2.8 + phase)) ** 2.8
        + np.abs(np.sin(u2 * f_fine * 2.6 - phase * 1.05)) ** 2.8
        + np.abs(np.sin(u3 * f_mid * 2.2 + phase * 0.85)) ** 2.2
    )
    micro = np.clip(micro / 3.0, 0.0, 1.0)

    hue = (
        field * 0.92
        + micro * 0.48
        + xx * inv_diag * 0.22
        + yy * inv_diag * 0.18
        + phase * 0.09
    ) % 1.0
    sat = np.clip(0.88 + 0.12 * np.sin(field * np.pi * 6.0 + phase * 1.4), 0.82, 1.0)
    val = np.clip(0.38 + 0.62 * (micro * 0.65 + field * 0.35), 0.3, 1.0)
    tex_rgb = _hsv_to_rgb(hue, sat, val)

    strength = np.clip(0.38 + 0.62 * (micro * 0.58 + np.abs(line1 * line2) * 0.42), 0.35, 1.0)
    return tex_rgb.astype(np.float32), strength.astype(np.float32)


def _infuse_psychedelic_foil(
    image: np.ndarray,
    *,
    tex_rgb: np.ndarray,
    tex_strength: np.ndarray,
    image_lum: np.ndarray,
    gain: float,
    sweep_boost: np.ndarray,
) -> np.ndarray:
    """将迷幻镭射箔纹理烙入画面像素（非漂浮叠加层）。"""
    base = image.astype(np.float32) / 255.0

    # 全图保底纹理 + 扫光区加强；暗部也保留箔感（镭射膜特性）
    lum_factor = 0.55 + 0.45 * image_lum
    opacity = np.clip(
        tex_strength * gain * lum_factor * (0.55 + 0.45 * sweep_boost),
        0.30,
        0.94,
    )

    soft = _soft_light_rgb(base, tex_rgb)

    h0, s0, v0 = _rgb_to_hsv(base)
    th, ts, _ = _rgb_to_hsv(tex_rgb)
    h_blend = (h0 * (1.0 - opacity) + th * opacity) % 1.0
    s_blend = np.clip(s0 + ts * opacity * 0.85, 0.0, 1.0)
    v_blend = np.clip(v0 + opacity * 0.10, 0.0, 1.0)
    hsv_out = _hsv_to_rgb(h_blend, s_blend, v_blend)

    op = opacity[..., None]
    fused = base * (1.0 - op) + (soft * 0.55 + hsv_out * 0.45) * op

    # 微光栅明暗起伏：让纹理「看得见」
    grain = tex_strength * opacity * 0.18
    fused = np.clip(fused + (grain - 0.08)[..., None] * 0.12, 0.0, 1.0)

    return np.clip(fused * 255.0, 0, 255).astype(np.uint8)


def _holographic_grating(
    proj: np.ndarray,
    *,
    wavelength: float,
    phase: float,
    sharpness: float = 7.0,
    hue_scale: float = 0.55,
) -> tuple[np.ndarray, np.ndarray]:
    """细周期镭射光栅：返回 (条纹强度 0–1, RGB 彩虹层 0–255)。"""
    wl = max(wavelength, 1.0)
    wave = np.sin(2.0 * np.pi * proj / wl + phase)
    # 叠加二次谐波，条纹层次更丰富、更「炫」
    wave2 = np.sin(4.0 * np.pi * proj / wl + phase * 1.3)
    mixed = wave * 0.72 + wave2 * 0.28
    bands = np.clip((mixed + 1.0) * 0.5, 0.0, 1.0) ** sharpness

    hue = (proj / wl * hue_scale + phase * 0.42) % 1.0
    sat = np.full_like(hue, 1.0, dtype=np.float32)
    val = np.clip(bands * 1.25, 0.0, 1.0)
    rgb = _hsv_to_rgb(hue, sat, val) * 255.0
    return bands.astype(np.float32), rgb.astype(np.float32)


def _sweep_band_mask(
    proj: np.ndarray,
    center: float,
    band_width: float,
) -> np.ndarray:
    """窄条扫光带：高斯型锐利亮带，非大面积雾化。"""
    sigma = max(band_width / 3.8, 1.0)
    dist = np.abs(proj - center)
    core = np.exp(-(dist ** 2) / (2.0 * sigma ** 2))
    # 略柔边缘，让宽扫光带仍有渐变层次
    return np.clip(core ** 1.25, 0.0, 1.0).astype(np.float32)


def _sparkle_layer(
    h: int,
    w: int,
    rng: np.random.Generator,
    n_sparkles: int,
    gain: float,
) -> tuple[np.ndarray, np.ndarray]:
    """稀疏星芒点：小范围高亮，模拟闪卡反光颗粒。"""
    mask = np.zeros((h, w), dtype=np.float32)
    rgb = np.zeros((h, w, 3), dtype=np.float32)
    if n_sparkles <= 0:
        return mask, rgb

    ys = rng.integers(0, h, size=n_sparkles)
    xs = rng.integers(0, w, size=n_sparkles)
    hues = rng.uniform(0.0, 1.0, size=n_sparkles)
    for y, x, hue in zip(ys, xs, hues):
        y0, y1 = max(0, y - 1), min(h, y + 2)
        x0, x1 = max(0, x - 1), min(w, x + 2)
        spot = gain * rng.uniform(0.6, 1.0)
        mask[y0:y1, x0:x1] = np.maximum(mask[y0:y1, x0:x1], spot)
        color = _hsv_to_rgb(
            np.array([hue], dtype=np.float32),
            np.array([0.95], dtype=np.float32),
            np.array([1.0], dtype=np.float32),
        )[0] * 255.0
        rgb[y0:y1, x0:x1] = np.maximum(rgb[y0:y1, x0:x1], color * spot)
    return mask, rgb


def _additive_blend(
    base: np.ndarray,
    overlay: np.ndarray,
    mask: np.ndarray,
) -> np.ndarray:
    """局部加法混合，只在 mask>0 区域提亮。"""
    m = mask[..., None].astype(np.float32)
    out = base.astype(np.float32) + overlay.astype(np.float32) * m
    return np.clip(out, 0, 255).astype(np.uint8)


def _affected_ratio(original: np.ndarray, frame: np.ndarray, threshold: int = 8) -> float:
    """统计与原图差异超过阈值的像素比例。"""
    diff = np.max(np.abs(original.astype(np.int16) - frame.astype(np.int16)), axis=2)
    return float(np.mean(diff > threshold))


def _pick_key_and_worst(ratios: list[float]) -> tuple[int, int]:
    """关键帧取中等反光；最差帧取遮挡最重。"""
    if not ratios:
        return 0, 0
    arr = np.asarray(ratios, dtype=np.float64)
    worst_index = int(np.argmax(arr))
    target = float(np.median(arr))
    candidates = [i for i in range(len(arr)) if i != worst_index]
    if not candidates:
        return 0, 0
    key_index = int(min(candidates, key=lambda i: abs(arr[i] - target)))
    if key_index == worst_index:
        key_index = int(min(range(len(arr)), key=lambda i: abs(arr[i] - target)))
    return key_index, worst_index


def generate_live_glare_frames(
    image: np.ndarray,
    *,
    duration_s: float = 2.4,
    fps: int = 10,
    intensity: Intensity = "medium",
    seed: int = 42,
) -> LiveGlareResult:
    """在静态 RGB 图上生成短 Live 镭射闪卡帧序列。

    Parameters
    ----------
    image:
        uint8 H×W×3 原图（底图）。
    duration_s:
        动画时长（秒）。
    fps:
        帧率。
    intensity:
        反光强度：``light`` / ``medium`` / ``strong``。
    seed:
        随机种子，保证可复现。

    Returns
    -------
    LiveGlareResult
        帧序列、关键帧/最差帧索引及元数据。
    """
    _validate_rgb(image)
    if duration_s <= 0:
        raise ValueError("duration_s must be positive.")
    if fps < 1:
        raise ValueError("fps must be >= 1.")

    preset = _INTENSITY_PRESETS[intensity]
    n_frames = max(2, int(round(duration_s * fps)))
    h, w = image.shape[:2]
    rng = np.random.default_rng(seed)

    diag = float(np.hypot(w, h))
    band_width = preset["band_width"] * diag

    # 主扫光方向（闪卡常见斜向镭射带）
    sweep_angle = float(rng.uniform(22.0, 52.0))
    sweep_proj = _projection_grid(h, w, sweep_angle)
    proj_min = float(sweep_proj.min())
    proj_max = float(sweep_proj.max())

    sweep_path = np.linspace(
        proj_min + band_width * 0.35,
        proj_max - band_width * 0.35,
        n_frames,
        dtype=np.float64,
    )

    grating_angles = rng.uniform(10.0, 80.0, size=int(preset["n_gratings"]))
    wavelengths = rng.uniform(diag * 0.008, diag * 0.028, size=int(preset["n_gratings"]))
    grating_phases = rng.uniform(0.0, 2.0 * np.pi, size=int(preset["n_gratings"]))

    grating_projs = [_projection_grid(h, w, float(a)) for a in grating_angles]

    # 迷幻镭射箔：多层交叉光栅角度（固定种子，逐帧只滚相位）
    foil_angles = np.deg2rad(rng.uniform(12.0, 78.0, size=3))
    image_lum = _image_luminance(image)
    content_holo_gain = float(preset["content_holo_gain"])

    baseline_grating = float(preset["baseline_grating_gain"])
    baseline_sparkle = float(preset["baseline_sparkle_gain"])

    frames: list[np.ndarray] = []
    ratios: list[float] = []

    for fi in range(n_frames):
        sweep_center = float(sweep_path[fi])
        sweep_mask = _sweep_band_mask(sweep_proj, sweep_center, band_width)

        # --- 镭射彩虹光栅 ---
        grating_rgb = np.zeros((h, w, 3), dtype=np.float32)
        grating_mask = np.zeros((h, w), dtype=np.float32)
        phase_shift = fi * 0.18

        # --- 画面本体：迷幻镭射箔纹理烙入 ---
        foil_rgb, foil_strength = _build_psychedelic_foil_texture(
            h, w, phase=phase_shift * 1.6, diag=diag, foil_angles=foil_angles
        )
        content_base = _infuse_psychedelic_foil(
            image,
            tex_rgb=foil_rgb,
            tex_strength=foil_strength,
            image_lum=image_lum,
            gain=content_holo_gain,
            sweep_boost=sweep_mask,
        )

        for gi, gproj in enumerate(grating_projs):
            bands, rgb = _holographic_grating(
                gproj,
                wavelength=float(wavelengths[gi]),
                phase=float(grating_phases[gi]) + phase_shift,
                sharpness=7.0,
                hue_scale=0.58,
            )
            # 全帧底纹：保证首尾及任意单帧都不会是「完全无镭射」的原图
            base_local = bands * baseline_grating
            grating_mask = np.maximum(grating_mask, base_local)
            grating_rgb = np.maximum(grating_rgb, rgb * base_local[..., None])

            # 扫光带内加强条纹
            sweep_local = bands * sweep_mask * float(preset["grating_gain"])
            grating_mask = np.maximum(grating_mask, sweep_local)
            grating_rgb = np.maximum(grating_rgb, rgb * sweep_local[..., None])

        # --- 扫光核心：彩虹为主、少量白高光 ---
        sweep_hue = (fi * 0.05 + float(rng.uniform(0, 1))) % 1.0
        sweep_color = _hsv_to_rgb(
            np.array([sweep_hue], dtype=np.float32),
            np.array([0.92], dtype=np.float32),
            np.array([1.0], dtype=np.float32),
        )[0] * 255.0
        white_core = np.array([255.0, 255.0, 255.0], dtype=np.float32)
        sweep_rgb = sweep_mask[..., None] * (
            white_core * 0.25 + sweep_color * 0.75
        ) * float(preset["sweep_gain"])

        # --- 星芒点：扫光带内强、全图弱底纹 ---
        sparkle_mask, sparkle_rgb = _sparkle_layer(
            h, w, rng, int(preset["n_sparkles"]), float(preset["sparkle_gain"])
        )
        sparkle_mask = sparkle_mask * sweep_mask
        sparkle_rgb = sparkle_rgb * sweep_mask[..., None]

        n_base_sparks = max(12, int(preset["n_sparkles"]) // 5)
        base_mask, base_rgb = _sparkle_layer(
            h, w,
            np.random.default_rng(seed + fi * 9973),
            n_base_sparks,
            baseline_sparkle,
        )
        sparkle_mask = np.maximum(sparkle_mask, base_mask)
        sparkle_rgb = np.maximum(sparkle_rgb, base_rgb)

        combined_rgb = grating_rgb + sweep_rgb + sparkle_rgb
        combined_mask = np.clip(
            grating_mask + sweep_mask * float(preset["sweep_gain"]) * 0.85 + sparkle_mask * 0.5,
            0.0,
            1.0,
        )

        frame = _additive_blend(content_base, combined_rgb, combined_mask)
        frames.append(frame)
        ratios.append(_affected_ratio(image, frame))

    key_index, worst_index = _pick_key_and_worst(ratios)

    return LiveGlareResult(
        frames=frames,
        key_index=key_index,
        worst_index=worst_index,
        affected_ratios=ratios,
        duration_s=duration_s,
        fps=fps,
        intensity=intensity,
        seed=seed,
    )
