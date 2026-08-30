"""ASCII 可见水印 — 亮度映射字符网格叠加。

参考小红书类 ASCII 工具的效果要点：
1. **一格一字符**，格子足够大，字符清晰可辨；
2. **亮度 → 字符**（``? . : + - =`` 等），而非整段名字平铺（避免 c/l/i 竖笔连成黑条）；
3. 字符/点色取 cell 平均色并**轻微明度偏移**（``local_contrast``），贴近底色又可辨认；
4. 作者名嵌入：把名字字母**插入**亮度字符集，而非只用名字字母。

本模块仅依赖 numpy、Pillow。
"""

from __future__ import annotations

import math
from typing import Literal

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from core.text_fonts import get_text_font

LuminanceMode = Literal["luminance", "repeat_text", "fixed_char", "author_luminance"]
ColorMode = Literal["fixed", "local", "local_gradient"]
LayoutMode = Literal["grid", "particle", "halftone", "tile_grid"]
GlyphMode = Literal["ascii", "dot"]
MaskMode = Literal["none", "dark_fade", "lum_ramp"]
DitherMode = Literal["none", "bayer"]
AuthorMaskMode = Literal["none", "boost", "spell", "fine_dots", "fine_stealth", "fine_full"]
AuthorMaskPosition = Literal[
    "corner_br", "corner_bl", "bottom_center", "center_low",
    "tile_faint", "side_lc", "side_rc", "custom",
]
TileFadeMode = Literal[
    "none",
    "horizontal_lr",
    "horizontal_rl",
    "horizontal_center",
    "vertical_tb",
    "vertical_bt",
    "diagonal_tl_br",
    "diagonal_tr_bl",
    "radial_center",
]

_DEFAULT_CHARSET = ".,:;!?+-=~<>[]()/@#"
_FIXED_CHAR_DEFAULT = "?"
# 半调字符 ramp：暗→亮，视觉重量递减（参考 neethanwu/ascii-art HALFTONE_RAMP）
_HALFTONE_RAMP_BASE = "@O0o·. "
# 视觉密度：浅 → 深；优先选横笔画符号，减少竖条伪影
_DENSITY_CHARS = " .,:;!?+-=~<>[]()/@#\\|iIlL1tfrxnsz2uU345kho9$MWBDOQ&%G@#"

# 4×4 Bayer 有序抖动矩阵（参考 neethanwu/ascii-art dither.bayer）
_BAYER_4 = np.array([
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
], dtype=np.float64) / 16.0

# 多层错开：(x 比例, y 比例, 透明度系数) — 大格子 + 多 pass 兼顾字号与密度
_GRID_PASS_SPECS: tuple[tuple[float, float, float], ...] = (
    (0.0, 0.0, 1.00),
    (0.5, 0.5, 0.93),
    (0.33, 0.67, 0.88),
    (0.67, 0.33, 0.84),
)

_MONO_FONT_PATHS = [
    "C:/Windows/Fonts/consolab.ttf",
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/cour.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Courier.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]


def _char_density_score(ch: str) -> int:
    try:
        return _DENSITY_CHARS.index(ch)
    except ValueError:
        return len(_DENSITY_CHARS) // 2


def build_author_letters(author: str) -> str:
    """作者名字符池（用于随机注入）。"""
    raw = "".join(c for c in author.strip() if not c.isspace())
    return raw if raw else "JW"


def build_author_charset(author: str, *, min_len: int = 10) -> str:
    """构建参考图风格字符集：通用 ASCII 符号 + 作者名字母（浅→深）。

    名字字母插入到对应密度档位，保证图像由多种可辨字符拼成，而非竖条。
    """
    raw = "".join(c for c in author.strip() if not c.isspace())
    base = list(_DEFAULT_CHARSET)
    if not raw:
        return _DEFAULT_CHARSET

    unique = sorted(set(raw), key=_char_density_score)
    n = len(base)
    for i, ch in enumerate(unique):
        if ch in base:
            continue
        slot = min(n - 1, max(1, (i + 1) * n // (len(unique) + 1)))
        base.insert(slot, ch)

    out = "".join(dict.fromkeys(base))
    while len(out) < min_len:
        for ch in unique:
            if ch not in out:
                out += ch
            if len(out) >= min_len:
                break
        else:
            break
    return out


def build_halftone_ramp_charset(author: str) -> str:
    """构建半调 ramp 字符集：``@O0o·.`` + 作者名字母注入中间档。

    暗部用大字符 ``@``，亮部用 ``·`` / ``.`` / 空格（空格格不绘制，自然留隙）。
    参考 neethanwu/ascii-art ``halftone_style`` 的 HALFTONE_RAMP。
    """
    base = list(_HALFTONE_RAMP_BASE)
    raw = build_author_letters(author)
    if not raw:
        return _HALFTONE_RAMP_BASE

    unique = sorted(set(raw), key=_char_density_score)
    for i, ch in enumerate(unique):
        if ch in base:
            continue
        # 插入中密度档（O/0/o 附近），保留首尾 @ 与空格
        slot = min(len(base) - 2, max(1, 2 + i))
        base.insert(slot, ch)
    return "".join(dict.fromkeys(base))


def _bayer_adjust_lum(
    lum: float,
    gx: int,
    gy: int,
    *,
    levels: int,
    strength: float,
) -> float:
    """对单 cell 亮度做 4×4 Bayer 有序抖动偏移。

    亮部也能稳定映射到非空格字符，避免「白区一片空白」。
    """
    step = 255.0 / max(levels - 1, 1)
    threshold = float(_BAYER_4[gy % 4, gx % 4])
    offset = (threshold - 0.5) * step * float(np.clip(strength, 0.0, 1.0))
    return float(np.clip(lum + offset, 0.0, 255.0))


def _try_pick_author_char(
    *,
    author_name: str,
    author_letters: str,
    author_sequence_rate: float,
    author_inject_rate: float,
    author_seq_idx: list[int],
    rng: np.random.Generator,
) -> str | None:
    """按概率返回作者名字符：优先顺序拼写，其次随机字母；否则 ``None``。"""
    seq_r = float(np.clip(author_sequence_rate, 0.0, 1.0))
    inj_r = float(np.clip(author_inject_rate, 0.0, 1.0))
    roll = rng.random()
    if seq_r > 0.0 and author_name and roll < seq_r:
        n = len(author_name)
        for _ in range(n):
            idx = author_seq_idx[0] % n
            author_seq_idx[0] += 1
            ch = author_name[idx]
            if not ch.isspace():
                return ch
        return None
    if inj_r > 0.0 and author_letters and roll < seq_r + inj_r:
        return author_letters[int(rng.integers(0, len(author_letters)))]
    return None


def _deterministic_background_letter(
    gx: int,
    gy: int,
    n_cols: int,
    author_name: str,
    stride: int,
    phase: int = 0,
) -> str | None:
    """背景网格按固定步长顺序拼作者名，形成可辨认的断续字母链。

    与随机 ``author_sequence_rate`` 互补：每隔 ``stride`` 格强制写入
    作者名下一字母，读图时可沿网格扫到 ``COCOMANGO…`` 循环。
    """
    text = author_name.strip()
    if stride <= 0 or not text or n_cols <= 0:
        return None
    linear = gx + gy * n_cols
    if (linear + phase) % stride != 0:
        return None
    letter_i = (linear // stride) % len(text)
    ch = text[letter_i]
    return None if ch.isspace() else ch


def _pick_halftone_ramp_char(
    lum: float,
    charset: str,
    *,
    gx: int,
    gy: int,
    author_name: str = "",
    author_letters: str = "",
    author_sequence_rate: float = 0.0,
    author_inject_rate: float = 0.0,
    author_seq_idx: list[int] | None = None,
    dither: DitherMode,
    dither_strength: float,
    rng: np.random.Generator,
) -> str:
    """半调 ramp 选字：亮度→字符档，可选 Bayer 抖动，空格表示跳过。"""
    seq_idx = author_seq_idx if author_seq_idx is not None else [0]
    injected = _try_pick_author_char(
        author_name=author_name,
        author_letters=author_letters,
        author_sequence_rate=author_sequence_rate,
        author_inject_rate=author_inject_rate,
        author_seq_idx=seq_idx,
        rng=rng,
    )
    if injected is not None:
        return injected
    levels = max(2, len(charset))
    eff_lum = lum
    if dither == "bayer":
        eff_lum = _bayer_adjust_lum(
            lum, gx, gy, levels=levels, strength=dither_strength,
        )
    idx = int(eff_lum / 255.0 * (levels - 1) + 0.5)
    idx = max(0, min(levels - 1, idx))
    return charset[idx]


def _validate_input(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    h, w = image.shape[:2]
    if h < 16 or w < 16:
        raise ValueError(f"Image must be at least 16×16, got {h}×{w}.")


def _get_mono_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _MONO_FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return get_text_font(size, "A")



def _rgb_to_hsv(r: float, g: float, b: float) -> tuple[float, float, float]:
    mx = max(r, g, b)
    mn = min(r, g, b)
    diff = mx - mn
    if diff < 1e-6:
        h = 0.0
    elif mx == r:
        h = ((g - b) / diff) % 6.0
    elif mx == g:
        h = (b - r) / diff + 2.0
    else:
        h = (r - g) / diff + 4.0
    h /= 6.0
    s = 0.0 if mx < 1e-6 else diff / mx
    return h, s, mx


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[float, float, float]:
    h6 = (h % 1.0) * 6.0
    i = int(h6) % 6
    f = h6 - int(h6)
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return r, g, b


def _pick_char(
    lum: float,
    charset: str,
    *,
    author_name: str = "",
    author_letters: str = "",
    author_sequence_rate: float = 0.0,
    author_inject_rate: float = 0.0,
    author_seq_idx: list[int] | None = None,
    density_jitter: int,
    rng: np.random.Generator,
    skip_space: bool,
) -> str:
    """亮度映射 + 顺序/随机作者字母注入 + 密度索引抖动。"""
    seq_idx = author_seq_idx if author_seq_idx is not None else [0]
    injected = _try_pick_author_char(
        author_name=author_name,
        author_letters=author_letters,
        author_sequence_rate=author_sequence_rate,
        author_inject_rate=author_inject_rate,
        author_seq_idx=seq_idx,
        rng=rng,
    )
    if injected is not None:
        return injected

    if not charset:
        return "?"
    idx = int(lum / 255.0 * (len(charset) - 1) + 0.5)
    if density_jitter > 0:
        idx += int(rng.integers(-density_jitter, density_jitter + 1))
    idx = max(0, min(len(charset) - 1, idx))
    ch = charset[idx]
    if skip_space and ch.isspace():
        ch = charset[0] if not charset[0].isspace() else charset[min(1, len(charset) - 1)]
    return ch


def _char_from_luminance(lum: float, charset: str, *, skip_space: bool = True) -> str:
    return _pick_char(
        lum, charset,
        author_letters="",
        author_inject_rate=0.0,
        density_jitter=0,
        rng=np.random.default_rng(0),
        skip_space=skip_space,
    )


MaskMode = Literal["none", "dark_fade", "lum_ramp"]


def _smoothstep(t: float) -> float:
    t = float(np.clip(t, 0.0, 1.0))
    return t * t * (3.0 - 2.0 * t)


def _lum_mask_factor(
    lum: float,
    *,
    full_below: float,
    fade_end: float,
) -> float:
    """暗部=1，亮部=0，中间 smoothstep 渐变。"""
    if lum >= fade_end:
        return 0.0
    if lum <= full_below:
        return 1.0
    t = (lum - full_below) / max(1e-6, fade_end - full_below)
    return 1.0 - _smoothstep(t)


def _lum_ramp_mask(
    lum: float,
    *,
    full_below: float,
    fade_end: float,
    bright_floor: float,
) -> float:
    """参考图式全图分级：暗/中调满强度，仅最亮区淡出至 ``bright_floor``。"""
    floor = float(np.clip(bright_floor, 0.0, 1.0))
    if lum <= full_below:
        return 1.0
    if lum >= fade_end:
        return floor
    t = (lum - full_below) / max(1e-6, fade_end - full_below)
    return 1.0 - _smoothstep(t) * (1.0 - floor)


def _compute_lum_mask(
    lum_mask: MaskMode,
    lum: float,
    *,
    full_below: float,
    fade_end: float,
    bright_floor: float,
) -> tuple[float, float]:
    """返回 (alpha 系数, bright_t) 供渐变着色。"""
    if lum_mask == "none":
        return 1.0, 0.0
    if lum_mask == "dark_fade":
        mask_f = _lum_mask_factor(lum, full_below=full_below, fade_end=fade_end)
    else:
        mask_f = _lum_ramp_mask(
            lum, full_below=full_below, fade_end=fade_end, bright_floor=bright_floor,
        )
    bright_t = 0.0
    if lum > full_below:
        bright_t = float(np.clip(
            (lum - full_below) / max(1e-6, fade_end - full_below),
            0.0, 1.0,
        ))
    return mask_f, bright_t


def _dark_adaptive_scale(lum: float, boost: float, *, pivot: float = 130.0) -> float:
    """暗部增益：lum 越低系数越高（1.0 → 1+boost）。"""
    if boost <= 0.0:
        return 1.0
    t = float(np.clip((pivot - lum) / max(1e-6, pivot), 0.0, 1.0))
    return 1.0 + boost * t


def _sample_patch(
    image: np.ndarray,
    x0: int,
    y0: int,
    cw: int,
    ch: int,
) -> tuple[float, np.ndarray] | None:
    h, w = image.shape[:2]
    x1 = min(w, x0 + cw)
    y1 = min(h, y0 + ch)
    if x1 <= x0 or y1 <= y0:
        return None
    patch = image[y0:y1, x0:x1].astype(np.float32)
    rgb = patch.mean(axis=(0, 1))
    lum = float(np.dot(rgb, [0.299, 0.587, 0.114]))
    return lum, rgb


def _paint_faint_anti_crop_field(
    draw: ImageDraw.ImageDraw,
    image: np.ndarray,
    *,
    fine_step: int,
    dot_radius: int,
    alpha_byte: int,
    base_contrast: float,
    color_mode: ColorMode,
    fixed_color: tuple[int, int, int],
    img_w: int,
    img_h: int,
    lum_mask: MaskMode = "none",
    mask_full_below: float = 198.0,
    mask_fade_end: float = 248.0,
    mask_bright_floor: float = 0.10,
) -> None:
    """全页均匀细点底纹：不重复可读完整署名，避免画面中心出现第二块署名。"""
    _paint_fine_dot_field(
        draw,
        image,
        author_pixel_mask=None,
        fine_step=max(2, int(fine_step)),
        dot_radius=dot_radius,
        alpha_byte=alpha_byte,
        base_contrast=base_contrast,
        name_contrast_boost=0.0,
        color_mode=color_mode,
        fixed_color=fixed_color,
        img_w=img_w,
        img_h=img_h,
        lum_mask=lum_mask,
        mask_full_below=mask_full_below,
        mask_fade_end=mask_fade_end,
        mask_bright_floor=mask_bright_floor,
        restrict_to_mask=False,
        bbox=None,
    )


def _build_contour_warp_maps(
    image: np.ndarray,
    *,
    cell_w: int,
    cell_h: int,
    n_rows: int,
    n_cols: int,
    img_w: int,
    img_h: int,
    strength: float,
    max_offset_ratio: float = 0.42,
    max_angle_deg: float = 32.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """由 Sobel 边缘切向场生成每格位移与旋转，使字符沿主体轮廓错位。

    梯度垂直于边缘；切向 ``(-gy, gx)`` 沿轮廓方向。边缘越强，错位与旋转越大，
    打破规则竖排网格，提高 AI 整块去除难度。
    """
    import cv2

    strength_f = float(np.clip(strength, 0.0, 1.0))
    off_x = np.zeros((n_rows, n_cols), dtype=np.float32)
    off_y = np.zeros((n_rows, n_cols), dtype=np.float32)
    ang = np.zeros((n_rows, n_cols), dtype=np.float32)
    if strength_f <= 0.001:
        return off_x, off_y, ang

    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gray = cv2.GaussianBlur(gray, (0, 0), sigmaX=1.2, sigmaY=1.2)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy)
    p95 = float(np.percentile(mag, 98)) if mag.size else 1.0
    scale = max(p95, 1e-3)

    cw = max(8, int(cell_w))
    ch = max(8, int(cell_h))
    max_off = max(cw, ch) * float(max_offset_ratio) * strength_f
    half_w = max(1, cw // 2)
    half_h = max(1, ch // 2)

    for gy_i in range(n_rows):
        for gx_i in range(n_cols):
            cx = min(img_w - 1, gx_i * cw + cw // 2)
            cy = min(img_h - 1, gy_i * ch + ch // 2)
            x0, x1 = max(0, cx - half_w), min(img_w, cx + half_w)
            y0, y1 = max(0, cy - half_h), min(img_h, cy + half_h)
            patch_mag = mag[y0:y1, x0:x1]
            if patch_mag.size == 0:
                continue
            py, px = np.unravel_index(int(np.argmax(patch_mag)), patch_mag.shape)
            gxv = float(gx[y0 + py, x0 + px])
            gyv = float(gy[y0 + py, x0 + px])
            m = float(patch_mag[py, px]) / scale
            if m < 0.06:
                continue
            tx, ty = -gyv, gxv
            norm = math.hypot(tx, ty)
            if norm < 1e-6:
                continue
            tx /= norm
            ty /= norm
            nx, ny = gxv / norm, gyv / norm
            w = min(1.0, m) * strength_f
            ripple = math.sin(gx_i * 0.65 + gy_i * 0.41) * 0.18 * max_off * w
            off_x[gy_i, gx_i] = tx * max_off * w * 0.85 + nx * ripple
            off_y[gy_i, gx_i] = ty * max_off * w * 0.85 + ny * ripple
            ang[gy_i, gx_i] = math.degrees(math.atan2(ty, tx)) * w * (
                max_angle_deg / 32.0
            )

    return off_x, off_y, ang


def _paste_rotated_glyph(
    overlay: Image.Image,
    cx: int,
    cy: int,
    ch: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill_rgba: tuple[int, int, int, int],
    angle_deg: float,
) -> None:
    """在 overlay 上以 (cx, cy) 为中心绘制可选旋转的单字。"""
    pad = 3
    bbox = ImageDraw.Draw(Image.new("L", (4, 4))).textbbox((0, 0), ch, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    size = max(tw, th) + pad * 2
    tmp = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(tmp)
    tdraw.text((pad - bbox[0], pad - bbox[1]), ch, font=font, fill=fill_rgba)
    if abs(angle_deg) >= 0.5:
        tmp = tmp.rotate(
            -angle_deg,
            resample=Image.Resampling.BILINEAR,
            expand=True,
        )
    ox = cx - tmp.width // 2
    oy = cy - tmp.height // 2
    overlay.paste(tmp, (ox, oy), tmp)


def _paint_ascii_grid(
    draw: ImageDraw.ImageDraw,
    image: np.ndarray,
    *,
    cell_w: int,
    cell_h: int,
    offset_x: int,
    offset_y: int,
    alpha_byte: int,
    draw_mode: LuminanceMode,
    charset: str,
    repeat: str,
    fill_char: str,
    color_mode: ColorMode,
    fixed_color: tuple[int, int, int],
    local_contrast: float,
    bg_filter: float,
    random_scale: float,
    stroke_width: int,
    font_size: int,
    base_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    rng: np.random.Generator,
    author_letters: str = "",
    author_name: str = "",
    author_sequence_rate: float = 0.0,
    author_inject_rate: float = 0.0,
    author_background_sequence_rate: float = 0.0,
    author_background_inject_rate: float = 0.0,
    author_background_chain_stride: int = 0,
    author_background_chain_phase: int = 0,
    author_seq_idx: list[int] | None = None,
    density_jitter: int = 0,
    gradient_strength: float = 0.30,
    img_w: int = 1,
    img_h: int = 1,
    lum_mask: MaskMode = "none",
    mask_full_below: float = 120.0,
    mask_fade_end: float = 215.0,
    mask_bright_floor: float = 0.10,
    dark_contrast_boost: float = 0.0,
    dark_alpha_boost: float = 0.0,
    halftone_gate: bool = False,
    halftone_screen_mix: float = 0.18,
    halftone_font_fill: float = 1.0,
    halftone_min_level_scale: float = 1.0,
    use_halftone_ramp: bool = False,
    dither: DitherMode = "none",
    dither_strength: float = 0.75,
    char_idx_start: int = 0,
    skip_space: bool = True,
    author_pixel_bbox: tuple[int, int, int, int] | None = None,
    author_zone_pad_cells: float = 4.5,
    grid_n_cols: int = 1,
    overlay: Image.Image | None = None,
    contour_off_x: np.ndarray | None = None,
    contour_off_y: np.ndarray | None = None,
    contour_ang: np.ndarray | None = None,
) -> int:
    """在 overlay 上绘制一层网格，返回更新后的 char_idx。"""
    h, w = image.shape[:2]
    char_idx = char_idx_start

    gy = 0
    y = offset_y
    while y < h:
        gx = 0
        x = offset_x
        while x < w:
            sampled = _sample_patch(image, x, y, cell_w, cell_h)
            if sampled is not None:
                lum, rgb = sampled
                if bg_filter <= 0.0 or (bg_filter * 255.0 <= lum <= (1.0 - bg_filter) * 255.0):
                    mask_f, bright_t = _compute_lum_mask(
                        lum_mask, lum,
                        full_below=mask_full_below,
                        fade_end=mask_fade_end,
                        bright_floor=mask_bright_floor,
                    )
                    if lum_mask == "dark_fade" and mask_f <= 0.01:
                        x += cell_w
                        continue
                    if mask_f <= 0.001:
                        x += cell_w
                        continue

                    chain_letter = False
                    draw_cx = x + cell_w // 2
                    draw_cy = y + cell_h // 2
                    rot_deg = 0.0

                    if draw_mode == "luminance":
                        draw_cx = min(img_w - 1, x + cell_w // 2)
                        draw_cy = min(img_h - 1, y + cell_h // 2)
                        if (
                            contour_off_x is not None
                            and contour_off_y is not None
                            and contour_ang is not None
                            and gy < contour_off_x.shape[0]
                            and gx < contour_off_x.shape[1]
                        ):
                            draw_cx = int(np.clip(
                                draw_cx + float(contour_off_x[gy, gx]), 0, img_w - 1,
                            ))
                            draw_cy = int(np.clip(
                                draw_cy + float(contour_off_y[gy, gx]), 0, img_h - 1,
                            ))
                            rot_deg = float(contour_ang[gy, gx])
                        pad = int(max(cell_w, cell_h) * float(author_zone_pad_cells))
                        near_author = (
                            author_pixel_bbox is not None
                            and _cell_in_pixel_bbox(
                                draw_cx, draw_cy, author_pixel_bbox, pad=pad,
                            )
                        )
                        if near_author:
                            seq_r = author_sequence_rate
                            inj_r = author_inject_rate
                        else:
                            seq_r = author_background_sequence_rate
                            inj_r = author_background_inject_rate
                        sample_x = max(0, min(x, img_w - max(4, cell_w)))
                        sample_y = max(0, min(y, img_h - max(4, cell_h)))
                        if draw_cx != x + cell_w // 2 or draw_cy != y + cell_h // 2:
                            sample_x = max(
                                0, min(draw_cx - cell_w // 2, img_w - max(4, cell_w)),
                            )
                            sample_y = max(
                                0, min(draw_cy - cell_h // 2, img_h - max(4, cell_h)),
                            )
                        resampled = _sample_patch(
                            image, sample_x, sample_y, cell_w, cell_h,
                        )
                        if resampled is not None:
                            lum, rgb = resampled
                        ch = None
                        if (
                            not near_author
                            and author_background_chain_stride > 0
                            and author_name
                        ):
                            ch = _deterministic_background_letter(
                                gx,
                                gy,
                                grid_n_cols,
                                author_name,
                                author_background_chain_stride,
                                author_background_chain_phase,
                            )
                            chain_letter = ch is not None
                        if ch is None:
                            if use_halftone_ramp:
                                ch = _pick_halftone_ramp_char(
                                    lum, charset,
                                    gx=gx, gy=gy,
                                    author_name=author_name,
                                    author_letters=author_letters,
                                    author_sequence_rate=seq_r,
                                    author_inject_rate=inj_r,
                                    author_seq_idx=author_seq_idx,
                                    dither=dither,
                                    dither_strength=dither_strength,
                                    rng=rng,
                                )
                                if ch.isspace():
                                    gx += 1
                                    x += cell_w
                                    continue
                            else:
                                ch = _pick_char(
                                    lum, charset,
                                    author_name=author_name,
                                    author_letters=author_letters,
                                    author_sequence_rate=seq_r,
                                    author_inject_rate=inj_r,
                                    author_seq_idx=author_seq_idx,
                                    density_jitter=density_jitter,
                                    rng=rng,
                                    skip_space=skip_space,
                                )
                    elif draw_mode == "repeat_text":
                        ch = repeat[char_idx % len(repeat)]
                        char_idx += 1
                    else:
                        ch = fill_char

                    # 亮部：提高渐变权重 + 降低 alpha，自然「渐变过去」
                    use_gradient = color_mode == "local_gradient" or (
                        lum_mask in ("dark_fade", "lum_ramp") and bright_t > 0.05
                    )
                    eff_mode: ColorMode = "local_gradient" if use_gradient else (
                        "local" if color_mode != "fixed" else "fixed"
                    )
                    eff_gs = gradient_strength
                    if lum_mask in ("dark_fade", "lum_ramp") and bright_t > 0.0:
                        eff_gs = max(gradient_strength, 0.15 + 0.55 * bright_t)

                    eff_contrast = min(
                        0.55,
                        local_contrast * _dark_adaptive_scale(lum, dark_contrast_boost),
                    )
                    eff_mask = min(
                        1.0,
                        mask_f * _dark_adaptive_scale(lum, dark_alpha_boost, pivot=120.0),
                    )
                    if chain_letter:
                        eff_contrast = min(0.82, eff_contrast * 1.65)
                        eff_mask = min(1.0, eff_mask * 1.42)
                    halftone_fs_scale = 1.0
                    if halftone_gate and not use_halftone_ramp:
                        dot_level = _halftone_dot_level(
                            lum, gx, gy, screen_mix=halftone_screen_mix,
                        )
                        # 与粒子半调一致：仅过小「等价半径」时跳过，alpha 由 lum_ramp 管
                        if halftone_min_level_scale > 0.0:
                            min_level = (
                                0.35 / max(0.1, min(cell_w, cell_h) * 0.5)
                                * halftone_min_level_scale
                            )
                            if dot_level < min_level:
                                gx += 1
                                x += cell_w
                                continue
                        halftone_fs_scale = 0.78 + 0.17 * dot_level

                    fill_rgb = _resolve_glyph_color(
                        rgb, lum,
                        color_mode=eff_mode,
                        fixed_color=fixed_color,
                        local_contrast=eff_contrast,
                        x=x, y=y,
                        img_w=img_w, img_h=img_h,
                        gradient_strength=eff_gs,
                    )
                    cell_alpha = int(np.clip(alpha_byte * eff_mask, 0, 255))
                    if cell_alpha < 4:
                        gx += 1
                        x += cell_w
                        continue
                    fill_rgba = (*fill_rgb, cell_alpha)

                    fs = font_size
                    if halftone_gate and not use_halftone_ramp:
                        fill = max(0.5, halftone_font_fill)
                        fs = max(8, int(cell_w * fill * halftone_fs_scale))
                    elif random_scale > 0.0:
                        jitter = rng.uniform(-random_scale, random_scale)
                        fs = max(5, int(font_size * (1.0 + jitter)))
                    font = base_font if fs == font_size else _get_mono_font(fs)

                    bbox = draw.textbbox((0, 0), ch, font=font)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]
                    if halftone_gate:
                        draw_cx = x + cell_w // 2
                        draw_cy = y + cell_h // 2
                        tx = draw_cx - tw // 2 - bbox[0]
                        ty = draw_cy - th // 2 - bbox[1]
                    else:
                        tx = draw_cx - tw // 2 - bbox[0]
                        ty = draw_cy - th // 2 - bbox[1]

                    use_rotated = (
                        overlay is not None
                        and abs(rot_deg) >= 0.5
                        and stroke_width == 0
                        and not halftone_gate
                    )
                    if use_rotated:
                        _paste_rotated_glyph(
                            overlay, draw_cx, draw_cy, ch, font, fill_rgba, rot_deg,
                        )
                    elif stroke_width > 0 and color_mode in ("local", "local_gradient"):
                        stroke_rgb = _resolve_glyph_color(
                            rgb, lum,
                            color_mode="local" if color_mode == "local_gradient" else color_mode,
                            fixed_color=fixed_color,
                            local_contrast=min(0.55, local_contrast * 1.4) if local_contrast > 0 else 0.0,
                            x=x, y=y, img_w=img_w, img_h=img_h,
                            gradient_strength=0.0,
                        )
                        draw.text(
                            (tx, ty), ch, font=font, fill=fill_rgba,
                            stroke_width=stroke_width,
                            stroke_fill=(*stroke_rgb, cell_alpha),
                        )
                    else:
                        draw.text((tx, ty), ch, font=font, fill=fill_rgba)
            gx += 1
            x += cell_w
        gy += 1
        y += cell_h
    return char_idx


def _particle_size_ratio(
    rng: np.random.Generator,
    lum: float,
    *,
    size_min: float,
    size_max: float,
    lum_size: bool,
) -> float:
    """粒子字号比例：随机 + 可选暗部偏大（类似 Aniso 有机密度感）。"""
    lo = min(size_min, size_max)
    hi = max(size_min, size_max)
    base = float(rng.uniform(lo, hi))
    if not lum_size:
        return base
    dark_t = float(np.clip((150.0 - lum) / 150.0, 0.0, 1.0))
    return float(np.clip(base * (0.82 + 0.38 * dark_t), lo * 0.75, hi * 1.15))


def _paint_scatter(
    draw: ImageDraw.ImageDraw,
    image: np.ndarray,
    *,
    cell_w: int,
    cell_h: int,
    offset_x: int,
    offset_y: int,
    alpha_byte: int,
    draw_mode: LuminanceMode,
    charset: str,
    repeat: str,
    fill_char: str,
    color_mode: ColorMode,
    fixed_color: tuple[int, int, int],
    local_contrast: float,
    bg_filter: float,
    random_scale: float,
    stroke_width: int,
    font_size: int,
    base_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    rng: np.random.Generator,
    author_letters: str = "",
    author_name: str = "",
    author_sequence_rate: float = 0.0,
    author_inject_rate: float = 0.0,
    author_seq_idx: list[int] | None = None,
    density_jitter: int = 0,
    gradient_strength: float = 0.30,
    img_w: int = 1,
    img_h: int = 1,
    lum_mask: MaskMode = "none",
    mask_full_below: float = 120.0,
    mask_fade_end: float = 215.0,
    mask_bright_floor: float = 0.10,
    dark_contrast_boost: float = 0.0,
    dark_alpha_boost: float = 0.0,
    char_idx_start: int = 0,
    skip_space: bool = True,
    glyph_mode: GlyphMode = "ascii",
    particle_jitter: float = 0.55,
    particle_size_min: float = 0.52,
    particle_size_max: float = 1.48,
    particle_lum_size: bool = True,
    particle_skip_rate: float = 0.0,
    particle_dot_scale: float = 0.16,
) -> int:
    """散布布局：抖动位置 + 变尺寸 ASCII 或纯圆点粒子。"""
    h, w = image.shape[:2]
    char_idx = char_idx_start
    step_x = max(8, cell_w)
    step_y = max(8, cell_h)

    y = offset_y
    while y < h:
        x = offset_x
        while x < w:
            if particle_skip_rate > 0.0 and rng.random() < particle_skip_rate:
                x += step_x
                continue

            jx = int(np.clip(
                x + rng.uniform(-particle_jitter, particle_jitter) * step_x,
                0, w - 1,
            ))
            jy = int(np.clip(
                y + rng.uniform(-particle_jitter, particle_jitter) * step_y,
                0, h - 1,
            ))
            sample_w = max(6, int(step_x * 0.85))
            sample_h = max(6, int(step_y * 0.85))
            sx = max(0, min(jx, w - sample_w))
            sy = max(0, min(jy, h - sample_h))

            sampled = _sample_patch(image, sx, sy, sample_w, sample_h)
            if sampled is not None:
                lum, rgb = sampled
                if bg_filter <= 0.0 or (bg_filter * 255.0 <= lum <= (1.0 - bg_filter) * 255.0):
                    mask_f, bright_t = _compute_lum_mask(
                        lum_mask, lum,
                        full_below=mask_full_below,
                        fade_end=mask_fade_end,
                        bright_floor=mask_bright_floor,
                    )
                    if lum_mask == "dark_fade" and mask_f <= 0.01:
                        x += step_x
                        continue
                    if mask_f <= 0.001:
                        x += step_x
                        continue

                    if mask_f <= 0.001:
                        x += step_x
                        continue

                    use_gradient = color_mode == "local_gradient" or (
                        lum_mask in ("dark_fade", "lum_ramp") and bright_t > 0.05
                    )
                    eff_mode: ColorMode = "local_gradient" if use_gradient else (
                        "local" if color_mode != "fixed" else "fixed"
                    )
                    eff_gs = gradient_strength
                    if lum_mask in ("dark_fade", "lum_ramp") and bright_t > 0.0:
                        eff_gs = max(gradient_strength, 0.15 + 0.55 * bright_t)

                    eff_contrast = min(
                        0.55,
                        local_contrast * _dark_adaptive_scale(lum, dark_contrast_boost),
                    )
                    eff_mask = min(
                        1.0,
                        mask_f * _dark_adaptive_scale(lum, dark_alpha_boost, pivot=120.0),
                    )

                    fill_rgb = _resolve_glyph_color(
                        rgb, lum,
                        color_mode=eff_mode,
                        fixed_color=fixed_color,
                        local_contrast=eff_contrast,
                        x=jx, y=jy,
                        img_w=img_w, img_h=img_h,
                        gradient_strength=eff_gs,
                    )
                    cell_alpha = int(np.clip(alpha_byte * eff_mask, 0, 255))
                    if cell_alpha < 4:
                        x += step_x
                        continue
                    fill_rgba = (*fill_rgb, cell_alpha)

                    size_ratio = _particle_size_ratio(
                        rng, lum,
                        size_min=particle_size_min,
                        size_max=particle_size_max,
                        lum_size=particle_lum_size,
                    )
                    if random_scale > 0.0:
                        size_ratio *= 1.0 + rng.uniform(-random_scale, random_scale)

                    if glyph_mode == "dot":
                        radius = max(1, int(cell_w * particle_dot_scale * size_ratio))
                        draw.ellipse(
                            (jx - radius, jy - radius, jx + radius, jy + radius),
                            fill=fill_rgba,
                        )
                    else:
                        if draw_mode == "luminance":
                            ch = _pick_char(
                                lum, charset,
                                author_name=author_name,
                                author_letters=author_letters,
                                author_sequence_rate=author_sequence_rate,
                                author_inject_rate=author_inject_rate,
                                author_seq_idx=author_seq_idx,
                                density_jitter=density_jitter,
                                rng=rng,
                                skip_space=skip_space,
                            )
                        elif draw_mode == "repeat_text":
                            ch = repeat[char_idx % len(repeat)]
                            char_idx += 1
                        else:
                            ch = fill_char

                        fs = max(6, int(font_size * size_ratio))
                        font = base_font if fs == font_size else _get_mono_font(fs)

                        bbox = draw.textbbox((0, 0), ch, font=font)
                        tw = bbox[2] - bbox[0]
                        th = bbox[3] - bbox[1]
                        tx = jx - tw // 2 - bbox[0]
                        ty = jy - th // 2 - bbox[1]

                        if stroke_width > 0 and color_mode in ("local", "local_gradient"):
                            stroke_rgb = _resolve_glyph_color(
                                rgb, lum,
                                color_mode="local" if color_mode == "local_gradient" else color_mode,
                                fixed_color=fixed_color,
                                local_contrast=min(0.55, local_contrast * 1.4) if local_contrast > 0 else 0.0,
                                x=jx, y=jy, img_w=img_w, img_h=img_h,
                                gradient_strength=0.0,
                            )
                            draw.text(
                                (tx, ty), ch, font=font, fill=fill_rgba,
                                stroke_width=stroke_width,
                                stroke_fill=(*stroke_rgb, cell_alpha),
                            )
                        else:
                            draw.text((tx, ty), ch, font=font, fill=fill_rgba)
            x += step_x
        y += step_y
    return char_idx


def _halftone_dot_level(lum: float, gx: int, gy: int, *, screen_mix: float) -> float:
    """Glyph 半调：暗部大点 + 确定性网屏纹理（非 random）。"""
    darkness = float(np.clip(1.0 - lum / 255.0, 0.0, 1.0))
    mix = float(np.clip(screen_mix, 0.0, 0.5))
    screen = (
        math.sin((gx * 0.82 + gy * 0.33) * 1.55)
        + math.cos((gx * 0.27 - gy * 0.94) * 1.25)
        + 2.0
    ) * 0.25
    return float(np.clip(darkness ** 0.92 * (1.0 - mix) + screen * mix, 0.0, 1.0))


def _author_mask_font_ratio(mask_scale: float) -> float:
    """``author_mask_scale``（0.55–1.35）→ 短边字号比例，与位移水印 ``font_ratio`` 同思路。

    默认（≈50）约 8.5% 短边，略小于位移默认 15%，避免细点署名区过大。
    """
    scale = float(np.clip(mask_scale, 0.4, 2.5))
    t = (scale - 0.55) / (1.35 - 0.55)
    return 0.050 + float(np.clip(t, 0.0, 1.0)) * (0.120 - 0.050)


def _author_mask_font_size(
    cell_w: int,
    mask_scale: float,
    *,
    tiled: bool,
    img_w: int = 0,
    img_h: int = 0,
) -> int:
    """署名点阵字号：平铺模式仍跟 cell；锚点署名跟图幅短边 × 比例（不跟网格 cell 缩放）。"""
    scale = float(np.clip(mask_scale, 0.4, 2.5))
    if tiled:
        return max(12, int(cell_w * scale * 2.8))
    short_side = (
        max(12, min(int(img_w), int(img_h)))
        if img_w > 0 and img_h > 0
        else max(12, int(cell_w) * 8)
    )
    return max(12, int(short_side * _author_mask_font_ratio(scale)))


def _build_author_dot_mask(
    author: str,
    *,
    img_w: int,
    img_h: int,
    cell_w: int,
    cell_h: int,
    position: AuthorMaskPosition,
    mask_scale: float = 1.0,
    tile_spacing: float = 0.35,
    anchor_x: float = 0.5,
    anchor_y: float = 0.54,
) -> tuple[np.ndarray, np.ndarray, tuple[int, int, int, int] | None]:
    """将作者名栅格化为像素级 mask 与半调 grid mask。

    返回 ``(grid_mask[gy,gx], pixel_mask[h,w], pixel_bbox)``。
    ``pixel_mask`` 为 True 表示该像素落在字形笔画上（用于细点署名）。
    """
    text = author.strip()
    n_cols = max(1, (img_w + cell_w - 1) // cell_w)
    n_rows = max(1, (img_h + cell_h - 1) // cell_h)
    if not text:
        empty_g = np.zeros((n_rows, n_cols), dtype=bool)
        empty_p = np.zeros((img_h, img_w), dtype=bool)
        return empty_g, empty_p, None

    mask_img = Image.new("L", (img_w, img_h), 0)
    draw = ImageDraw.Draw(mask_img)
    tiled = position == "tile_faint"
    font_px = _author_mask_font_size(
        cell_w, mask_scale, tiled=tiled, img_w=img_w, img_h=img_h,
    )
    # 字号不得超过图幅，否则 custom 锚点会被 margin clamp 挤到同一位置。
    font_px = min(font_px, max(12, int(min(img_w, img_h) * 0.42)))
    font = _get_mono_font(font_px)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    for _ in range(10):
        if tw <= img_w * 0.82 and th <= img_h * 0.38:
            break
        font_px = max(10, int(font_px * 0.88))
        font = _get_mono_font(font_px)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

    margin = max(cell_w, int(cell_w * 1.5))
    pixel_bbox: tuple[int, int, int, int] | None = None

    if position == "corner_br":
        tx = img_w - tw - margin - bbox[0]
        ty = img_h - th - margin - bbox[1]
        draw.text((tx, ty), text, font=font, fill=255)
        pixel_bbox = (tx + bbox[0], ty + bbox[1], tx + bbox[2], ty + bbox[3])
    elif position == "corner_bl":
        tx = margin - bbox[0]
        ty = img_h - th - margin - bbox[1]
        draw.text((tx, ty), text, font=font, fill=255)
        pixel_bbox = (tx + bbox[0], ty + bbox[1], tx + bbox[2], ty + bbox[3])
    elif position == "bottom_center":
        tx = (img_w - tw) // 2 - bbox[0]
        ty = img_h - th - margin - bbox[1]
        draw.text((tx, ty), text, font=font, fill=255)
        pixel_bbox = (tx + bbox[0], ty + bbox[1], tx + bbox[2], ty + bbox[3])
    elif position == "center_low":
        # 横排：水平居中，垂直约 54% 高度（居中略偏下）
        tx = (img_w - tw) // 2 - bbox[0]
        ty = int(img_h * 0.54) - th // 2 - bbox[1]
        ty = max(margin, min(img_h - th - margin, ty))
        draw.text((tx, ty), text, font=font, fill=255)
        pixel_bbox = (tx + bbox[0], ty + bbox[1], tx + bbox[2], ty + bbox[3])
    elif position == "custom":
        # 横排：以归一化锚点 (anchor_x, anchor_y) 为署名中心
        cx = int(float(np.clip(anchor_x, 0.0, 1.0)) * img_w)
        cy = int(float(np.clip(anchor_y, 0.0, 1.0)) * img_h)
        tx = cx - tw // 2 - bbox[0]
        ty = cy - th // 2 - bbox[1]
        tx = max(margin - bbox[0], min(img_w - tw - margin - bbox[0], tx))
        ty = max(margin - bbox[1], min(img_h - th - margin - bbox[1], ty))
        draw.text((tx, ty), text, font=font, fill=255)
        pixel_bbox = (tx + bbox[0], ty + bbox[1], tx + bbox[2], ty + bbox[3])
    elif position == "tile_faint":
        step_x = max(cell_w * 4, int(img_w * float(np.clip(tile_spacing, 0.15, 0.85))))
        step_y = max(cell_h * 4, int(img_h * float(np.clip(tile_spacing, 0.15, 0.85))))
        for ty in range(step_y // 2, img_h, step_y):
            for tx in range(step_x // 2, img_w, step_x):
                draw.text((tx, ty), text, font=font, fill=255)
    elif position in ("side_lc", "side_rc"):
        # 左右侧竖排：垂直方向约居中偏下（~54% 高度锚点）
        pad = 2
        tmp = Image.new("L", (tw + pad * 2, th + pad * 2), 0)
        tdraw = ImageDraw.Draw(tmp)
        tdraw.text((pad, pad), text, font=font, fill=255)
        vert = tmp.rotate(90, expand=True)
        vw, vh = vert.size
        anchor_y = int(img_h * 0.54) - vh // 2
        anchor_y = max(margin, min(img_h - vh - margin, anchor_y))
        if position == "side_lc":
            px = margin
        else:
            px = max(margin, img_w - vw - margin)
        mask_img.paste(vert, (px, anchor_y))
        pixel_bbox = (px, anchor_y, px + vw, anchor_y + vh)
    else:
        draw.text((margin, img_h - th - margin), text, font=font, fill=255)

    mask_arr = np.array(mask_img)
    pixel_mask = mask_arr > 128
    grid_mask = np.zeros((n_rows, n_cols), dtype=bool)
    for gy in range(n_rows):
        for gx in range(n_cols):
            cx = min(img_w - 1, gx * cell_w + cell_w // 2)
            cy = min(img_h - 1, gy * cell_h + cell_h // 2)
            grid_mask[gy, gx] = pixel_mask[cy, cx]
    return grid_mask, pixel_mask, pixel_bbox


def _draw_fine_dot(
    draw: ImageDraw.ImageDraw,
    image: np.ndarray,
    px: int,
    py: int,
    *,
    dot_radius: int,
    alpha_byte: int,
    contrast: float,
    color_mode: ColorMode,
    fixed_color: tuple[int, int, int],
    img_w: int,
    img_h: int,
) -> None:
    """在单点绘制与底色同色相的细点。"""
    sampled = _sample_patch(image, px, py, 1, 1)
    if sampled is None:
        return
    lum, rgb = sampled
    fill_rgb = _resolve_glyph_color(
        rgb, lum,
        color_mode="local" if color_mode != "fixed" else "fixed",
        fixed_color=fixed_color,
        local_contrast=float(np.clip(contrast, 0.04, 0.65)),
        x=px, y=py,
        img_w=img_w, img_h=img_h,
        gradient_strength=0.0,
    )
    cell_alpha = int(np.clip(alpha_byte, 0, 255))
    if cell_alpha < 4:
        return
    r = max(1, int(dot_radius))
    draw.ellipse(
        (px - r, py - r, px + r, py + r),
        fill=(*fill_rgb, cell_alpha),
    )


def _boost_mask_in_author_zone(
    mask_f: float,
    x: int,
    y: int,
    bbox: tuple[int, int, int, int] | None,
    *,
    cell_size: int,
    pad_cells: float,
    floor: float,
) -> float:
    """署名 bbox 邻域内抬高 lum_mask，避免亮部把波点/细点淡没。"""
    if bbox is None or floor <= 0.0:
        return mask_f
    pad = int(max(8, cell_size) * max(0.5, pad_cells))
    if _cell_in_pixel_bbox(x, y, bbox, pad=pad):
        return max(mask_f, float(np.clip(floor, 0.0, 1.0)))
    return mask_f


def _paint_fine_dot_field(
    draw: ImageDraw.ImageDraw,
    image: np.ndarray,
    *,
    author_pixel_mask: np.ndarray | None,
    fine_step: int,
    dot_radius: int,
    alpha_byte: int,
    base_contrast: float,
    name_contrast_boost: float,
    color_mode: ColorMode,
    fixed_color: tuple[int, int, int],
    img_w: int,
    img_h: int,
    lum_mask: MaskMode = "none",
    mask_full_below: float = 198.0,
    mask_fade_end: float = 248.0,
    mask_bright_floor: float = 0.10,
    restrict_to_mask: bool = False,
    bbox: tuple[int, int, int, int] | None = None,
    author_zone_bbox: tuple[int, int, int, int] | None = None,
    author_zone_pad_cells: float = 4.0,
    author_zone_mask_floor: float = 0.0,
) -> None:
    """全图或 mask 区域铺同色细点；作者笔画处对比度略高。

    ``restrict_to_mask=True`` 时仅在 ``author_pixel_mask`` 为 True 处绘制（平铺淡署名）。
    """
    step = max(2, int(fine_step))
    h = image.shape[0]
    base_c = float(np.clip(base_contrast, 0.04, 0.40))
    boost = float(np.clip(name_contrast_boost, 0.0, 0.25))

    if bbox is None:
        x0, y0, x1, y1 = 0, 0, img_w, img_h
    else:
        pad = step * 2
        x0 = max(0, bbox[0] - pad)
        y0 = max(0, bbox[1] - pad)
        x1 = min(img_w, bbox[2] + pad)
        y1 = min(img_h, bbox[3] + pad)

    has_mask = author_pixel_mask is not None and author_pixel_mask.size > 0

    for py in range(y0, y1, step):
        if py >= h:
            break
        for px in range(x0, x1, step):
            if px >= img_w:
                break
            on_name = bool(has_mask and author_pixel_mask[py, px])
            if restrict_to_mask and not on_name:
                continue
            if not restrict_to_mask and has_mask and bbox is not None and not on_name:
                # full field 模式：bbox 外仍铺底纹，bbox 内非笔画也铺
                pass

            sampled = _sample_patch(image, px, py, max(2, step), max(2, step))
            if sampled is None:
                continue
            lum, _ = sampled
            mask_f, _ = _compute_lum_mask(
                lum_mask, lum,
                full_below=mask_full_below,
                fade_end=mask_fade_end,
                bright_floor=mask_bright_floor,
            )
            mask_f = _boost_mask_in_author_zone(
                mask_f, px, py, author_zone_bbox or bbox,
                cell_size=step,
                pad_cells=author_zone_pad_cells,
                floor=author_zone_mask_floor,
            )
            if lum_mask != "none" and mask_f <= 0.001:
                continue

            contrast = base_c + (boost if on_name else 0.0)
            eff_alpha = int(alpha_byte * (mask_f if lum_mask != "none" else 1.0))
            if on_name:
                eff_alpha = min(255, int(eff_alpha * 1.28))
            _draw_fine_dot(
                draw, image, px, py,
                dot_radius=dot_radius,
                alpha_byte=eff_alpha,
                contrast=contrast,
                color_mode=color_mode,
                fixed_color=fixed_color,
                img_w=img_w, img_h=img_h,
            )


def _paint_author_fine_dots(
    draw: ImageDraw.ImageDraw,
    image: np.ndarray,
    pixel_mask: np.ndarray,
    bbox: tuple[int, int, int, int] | None,
    *,
    fine_step: int = 3,
    dot_radius: int = 1,
    alpha_byte: int,
    name_contrast: float = 0.42,
    color_mode: ColorMode,
    fixed_color: tuple[int, int, int],
    img_w: int,
    img_h: int,
    bold_pass: bool = True,
) -> None:
    """用细小圆点沿字形笔画拼出作者名；署名笔画不受 lum_ramp 淡化。"""
    if not pixel_mask.any():
        return
    sign_kw = dict(
        author_pixel_mask=pixel_mask,
        fine_step=fine_step,
        dot_radius=dot_radius,
        alpha_byte=alpha_byte,
        base_contrast=name_contrast,
        name_contrast_boost=0.0,
        color_mode=color_mode,
        fixed_color=fixed_color,
        img_w=img_w,
        img_h=img_h,
        lum_mask="none",
        restrict_to_mask=True,
        bbox=bbox,
    )
    _paint_fine_dot_field(draw, image, **sign_kw)
    if bold_pass and dot_radius >= 1:
        _paint_fine_dot_field(
            draw, image,
            fine_step=max(2, fine_step - 1),
            dot_radius=dot_radius + 1,
            alpha_byte=min(255, int(alpha_byte * 0.72)),
            base_contrast=min(0.65, name_contrast * 1.12),
            **{k: v for k, v in sign_kw.items() if k not in (
                "fine_step", "dot_radius", "alpha_byte", "base_contrast",
            )},
        )


def _cell_in_pixel_bbox(
    cx: int,
    cy: int,
    bbox: tuple[int, int, int, int] | None,
    *,
    pad: int = 0,
) -> bool:
    if bbox is None:
        return False
    x0, y0, x1, y1 = bbox
    return (x0 - pad) <= cx <= (x1 + pad) and (y0 - pad) <= cy <= (y1 + pad)


def _paint_halftone(
    draw: ImageDraw.ImageDraw,
    image: np.ndarray,
    *,
    cell_w: int,
    cell_h: int,
    offset_x: int,
    offset_y: int,
    alpha_byte: int,
    color_mode: ColorMode,
    fixed_color: tuple[int, int, int],
    local_contrast: float,
    bg_filter: float,
    gradient_strength: float = 0.30,
    img_w: int = 1,
    img_h: int = 1,
    lum_mask: MaskMode = "none",
    mask_full_below: float = 120.0,
    mask_fade_end: float = 215.0,
    mask_bright_floor: float = 0.10,
    dark_contrast_boost: float = 0.0,
    dark_alpha_boost: float = 0.0,
    halftone_size: float = 1.0,
    halftone_screen_mix: float = 0.18,
    halftone_radius_cap: float = 1.0,
    halftone_min_radius: float = 0.35,
    author_grid_mask: np.ndarray | None = None,
    author_pixel_bbox: tuple[int, int, int, int] | None = None,
    author_mask_mode: AuthorMaskMode = "none",
    author_mask_opacity: float = 1.0,
    author_mask_radius_boost: float = 1.35,
    author_mask_alpha_boost: float = 1.25,
    author_bbox_halftone_pad: float = 2.5,
    author_zone_mask_floor: float = 0.0,
    author_zone_pad_cells: float = 4.0,
    **_: object,
) -> int:
    """规则网格半调圆点：格心对齐，半径随局部亮度变化。

    ``author_mask_mode='spell'``：署名 bbox 内仅笔画格绘制强化粒子，拼成点阵字；
    ``boost``：全图半调 + 笔画格点半径/透明度增强。
    """
    h, w = image.shape[:2]
    size_scale = float(np.clip(halftone_size, 0.4, 2.2))
    max_radius_base = max(0.1, min(cell_w, cell_h) * 0.5)
    use_author = (
        author_mask_mode != "none"
        and author_grid_mask is not None
        and author_grid_mask.size > 0
    )
    mask_opacity = float(np.clip(author_mask_opacity, 0.1, 1.0))
    radius_boost = float(np.clip(author_mask_radius_boost, 1.0, 2.5))
    alpha_boost = float(np.clip(author_mask_alpha_boost, 1.0, 2.0))
    bbox_pad = max(cell_w, cell_h)

    gy = 0
    y = offset_y
    while y < h:
        gx = 0
        x = offset_x
        while x < w:
            cx = x + cell_w // 2
            cy = y + cell_h // 2
            on_stroke = False
            in_zone = False
            if use_author and gy < author_grid_mask.shape[0] and gx < author_grid_mask.shape[1]:
                on_stroke = bool(author_grid_mask[gy, gx])
                if author_mask_mode == "spell":
                    in_zone = _cell_in_pixel_bbox(
                        cx, cy, author_pixel_bbox, pad=bbox_pad,
                    )

            sample_w = max(4, cell_w)
            sample_h = max(4, cell_h)
            sx = max(0, min(x, w - sample_w))
            sy = max(0, min(y, h - sample_h))

            sampled = _sample_patch(image, sx, sy, sample_w, sample_h)
            if sampled is not None:
                lum, rgb = sampled
                if bg_filter <= 0.0 or (bg_filter * 255.0 <= lum <= (1.0 - bg_filter) * 255.0):
                    mask_f, bright_t = _compute_lum_mask(
                        lum_mask, lum,
                        full_below=mask_full_below,
                        fade_end=mask_fade_end,
                        bright_floor=mask_bright_floor,
                    )
                    if lum_mask == "dark_fade" and mask_f <= 0.01:
                        gx += 1
                        x += cell_w
                        continue
                    if mask_f <= 0.001:
                        gx += 1
                        x += cell_w
                        continue

                    near_author = (
                        author_pixel_bbox is not None
                        and _cell_in_pixel_bbox(
                            cx, cy, author_pixel_bbox,
                            pad=int(max(cell_w, cell_h) * author_bbox_halftone_pad),
                        )
                    )
                    if near_author and author_zone_mask_floor > 0.0:
                        mask_f = max(mask_f, author_zone_mask_floor)

                    # fine_stealth / fine_full：不挖空署名区，避免 AI 轻松定位矩形
                    if use_author and author_mask_mode == "spell" and in_zone and not on_stroke:
                        gx += 1
                        x += cell_w
                        continue

                    dot_level = _halftone_dot_level(
                        lum, gx, gy, screen_mix=halftone_screen_mix,
                    )
                    if near_author:
                        dot_level = max(dot_level, 0.62)
                    cap = float(np.clip(halftone_radius_cap, 0.25, 1.0))
                    if cap < 1.0:
                        dot_level = min(dot_level, cap)
                    if use_author and on_stroke:
                        dot_level = max(dot_level, 0.82)

                    radius = max_radius_base * dot_level * size_scale
                    if use_author and on_stroke:
                        radius *= radius_boost

                    min_r = float(max(0.15, halftone_min_radius))
                    if radius < min_r and not (use_author and on_stroke):
                        if near_author:
                            radius = max(min_r, max_radius_base * 0.55)
                        else:
                            gx += 1
                            x += cell_w
                            continue

                    use_gradient = color_mode == "local_gradient" or (
                        lum_mask in ("dark_fade", "lum_ramp") and bright_t > 0.05
                    )
                    eff_mode: ColorMode = "local_gradient" if use_gradient else (
                        "local" if color_mode != "fixed" else "fixed"
                    )
                    eff_gs = gradient_strength
                    if lum_mask in ("dark_fade", "lum_ramp") and bright_t > 0.0:
                        eff_gs = max(gradient_strength, 0.15 + 0.55 * bright_t)

                    eff_contrast = min(
                        0.55,
                        local_contrast * _dark_adaptive_scale(lum, dark_contrast_boost),
                    )
                    if use_author and on_stroke:
                        eff_contrast = min(0.55, eff_contrast * 1.35)

                    eff_mask = min(
                        1.0,
                        mask_f * _dark_adaptive_scale(lum, dark_alpha_boost, pivot=120.0),
                    )
                    if use_author and on_stroke:
                        eff_mask = min(1.0, eff_mask * alpha_boost * mask_opacity)

                    fill_rgb = _resolve_glyph_color(
                        rgb, lum,
                        color_mode=eff_mode,
                        fixed_color=fixed_color,
                        local_contrast=eff_contrast,
                        x=cx, y=cy,
                        img_w=img_w, img_h=img_h,
                        gradient_strength=eff_gs,
                    )
                    cell_alpha = int(np.clip(alpha_byte * eff_mask, 0, 255))
                    if cell_alpha >= 4:
                        fill_rgba = (*fill_rgb, cell_alpha)
                        r = max(1, int(radius))
                        draw.ellipse(
                            (cx - r, cy - r, cx + r, cy + r),
                            fill=fill_rgba,
                        )
            gx += 1
            x += cell_w
        gy += 1
        y += cell_h
    return 0


def _build_tile_fade_map(
    img_h: int,
    img_w: int,
    *,
    mode: TileFadeMode,
    fade_start: float,
    fade_end: float,
) -> np.ndarray:
    """空间渐变权重图 ``[0,1]``：0=清晰无格，1=满格/磨砂。

    ``radial_center``：画面中心最清晰，向四边渐变为磨砂。
    ``diagonal_tl_br``：左上清晰 → 右下磨砂（单方向对角线）。
    ``diagonal_tr_bl``：右上清晰 → 左下磨砂。
    """
    if mode == "none":
        return np.ones((img_h, img_w), dtype=np.float32)

    fs = float(np.clip(fade_start, 0.0, 0.98))
    fe = float(np.clip(fade_end, fs + 0.02, 1.0))
    span = max(1e-6, fe - fs)

    yy, xx = np.meshgrid(
        np.linspace(0.0, 1.0, img_h, dtype=np.float32),
        np.linspace(0.0, 1.0, img_w, dtype=np.float32),
        indexing="ij",
    )

    if mode == "horizontal_lr":
        raw = (xx - fs) / span
    elif mode == "horizontal_rl":
        raw = ((1.0 - xx) - fs) / span
    elif mode == "horizontal_center":
        dist = np.abs(xx - 0.5) * 2.0
        raw = (dist - fs) / span
    elif mode == "vertical_tb":
        raw = (yy - fs) / span
    elif mode == "vertical_bt":
        raw = ((1.0 - yy) - fs) / span
    elif mode == "diagonal_tl_br":
        dist = (xx + yy) * 0.5
        raw = (dist - fs) / span
    elif mode == "diagonal_tr_bl":
        dist = ((1.0 - xx) + yy) * 0.5
        raw = (dist - fs) / span
    elif mode == "radial_center":
        dist = np.sqrt((yy - 0.5) ** 2 + (xx - 0.5) ** 2) / 0.7071
        raw = (dist - fs) / span
    else:
        raw = (xx - fs) / span

    t = np.clip(raw, 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _apply_tile_subject_protect(
    fade_map: np.ndarray,
    *,
    strength: float,
    protect_radius: float,
    img_w: int = 0,
    img_h: int = 0,
) -> np.ndarray:
    """压低画面中心主体区域的 fade，避免对角线渐变把主体糊掉。

    内圈（``protect_radius`` 内）在 ``strength→1`` 时 fade 归零；外圈缓出到边角。
    横图时使用椭圆距离，横向保护范围更宽。
    """
    s = float(np.clip(strength, 0.0, 1.0))
    if s <= 0.001:
        return fade_map

    h, w = fade_map.shape
    pr = float(np.clip(protect_radius, 0.08, 0.92))
    yy, xx = np.meshgrid(
        np.linspace(-1.0, 1.0, h, dtype=np.float32),
        np.linspace(-1.0, 1.0, w, dtype=np.float32),
        indexing="ij",
    )
    iw = max(img_w, w, 1)
    ih = max(img_h, h, 1)
    ax = iw / max(iw, ih)
    ay = ih / max(iw, ih)
    dist = np.sqrt((xx / max(ax, 0.45)) ** 2 + (yy / max(ay, 0.45)) ** 2)
    dist /= np.sqrt(2.0)

    # 内圈硬保护；strength 越高 core 越大、过渡越窄
    core = pr * (0.88 + 0.10 * s)
    feather = (1.0 - pr) * (0.14 + 0.06 * (1.0 - s))
    fall = min(0.98, core + feather)

    t = np.clip((dist - core) / max(1e-6, fall - core), 0.0, 1.0)
    t = t * t * (3.0 - 2.0 * t)
    edge_scale = t ** (1.0 + s * 5.0)
    scale = (1.0 - s) + s * edge_scale
    return (fade_map * scale).astype(np.float32)


def _blur_image_rgb(image: np.ndarray, radius: float) -> np.ndarray:
    """高斯模糊（Pillow，无深度学习）。"""
    r = max(0.1, float(radius))
    pil = Image.fromarray(image)
    return np.array(pil.filter(ImageFilter.GaussianBlur(radius=r)), dtype=np.uint8)


def _apply_tile_fade_blur(
    image: np.ndarray,
    fade_map: np.ndarray,
    blur_radius: float,
) -> np.ndarray:
    """按渐变权重混合原图与模糊图，实现「模糊→清晰」过渡。"""
    if blur_radius <= 0.01:
        return image.copy()
    blurred = _blur_image_rgb(image, blur_radius)
    w = fade_map[:, :, np.newaxis]
    out = image.astype(np.float32) * (1.0 - w) + blurred.astype(np.float32) * w
    return np.clip(out, 0, 255).astype(np.uint8)


def _paint_rounded_tile_grid(
    draw: ImageDraw.ImageDraw,
    image: np.ndarray,
    fade_map: np.ndarray,
    *,
    tile_size: int,
    tile_gap: int,
    corner_radius: int,
    alpha_byte: int,
    tile_frost: float,
    local_contrast: float,
    color_mode: ColorMode,
    fixed_color: tuple[int, int, int],
    img_w: int,
    img_h: int,
) -> None:
    """圆角方格网格：仅在 ``fade_map`` 足够大的区域绘制，越淡越稀疏/透明。

    高 fade 区格块略偏白（磨砂感），低 fade 区接近底色。
    """
    ts = max(6, int(tile_size))
    gap = max(1, int(tile_gap))
    step = ts + gap
    cr = max(1, min(ts // 2, int(corner_radius)))
    frost = float(np.clip(tile_frost, 0.0, 1.0))
    h = image.shape[0]

    for y in range(0, h, step):
        for x in range(0, img_w, step):
            cx = min(img_w - 1, x + ts // 2)
            cy = min(h - 1, y + ts // 2)
            fade = float(fade_map[cy, cx])
            if fade < 0.035:
                continue

            sampled = _sample_patch(image, cx, cy, max(2, ts // 2), max(2, ts // 2))
            if sampled is None:
                continue
            lum, rgb = sampled
            fill_rgb = _resolve_glyph_color(
                rgb, lum,
                color_mode="local" if color_mode != "fixed" else "fixed",
                fixed_color=fixed_color,
                local_contrast=min(0.55, local_contrast * (0.6 + 0.4 * fade)),
                x=cx, y=cy,
                img_w=img_w, img_h=img_h,
                gradient_strength=0.0,
            )
            if frost > 0.0:
                mix = frost * fade
                fill_rgb = tuple(
                    int(np.clip(c * (1.0 - mix) + 255.0 * mix, 0, 255))
                    for c in fill_rgb
                )
            cell_alpha = int(np.clip(alpha_byte * fade, 0, 255))
            if cell_alpha < 4:
                continue
            x1 = x + gap // 2
            y1 = y + gap // 2
            x2 = min(img_w, x1 + ts)
            y2 = min(h, y1 + ts)
            if x2 <= x1 or y2 <= y1:
                continue
            draw.rounded_rectangle(
                (x1, y1, x2, y2),
                radius=cr,
                fill=(*fill_rgb, cell_alpha),
            )


def _resolve_glyph_color(
    rgb: np.ndarray,
    lum: float,
    *,
    color_mode: ColorMode,
    fixed_color: tuple[int, int, int],
    local_contrast: float,
    x: int = 0,
    y: int = 0,
    img_w: int = 1,
    img_h: int = 1,
    gradient_strength: float = 0.30,
) -> tuple[int, int, int]:
    """local / local_gradient：贴近 cell 底色，仅轻微明度偏移以便辨认。

    在线性 RGB 中按亮度方向微调节，再与采样色混合，避免 HSV 去饱和导致
    全图字符/点呈现统一灰色调。
    """
    if color_mode == "fixed":
        return fixed_color

    base = rgb.astype(np.float32)
    shift = float(np.clip(local_contrast, 0.0, 0.55))
    if shift <= 1e-6 and color_mode != "local_gradient":
        return int(base[0]), int(base[1]), int(base[2])

    lum_f = float(lum) / 255.0
    adapt = 0.55 + 0.45 * min(1.0, abs(lum_f - 0.5) * 2.0)
    delta = shift * 0.55 * adapt
    if lum >= 128.0:
        factor = 1.0 - delta
    else:
        factor = 1.0 + delta
    shifted = np.clip(base * factor, 0.0, 255.0)

    blend = float(np.clip(0.48 + shift * 1.25, 0.40, 0.78))
    out = base * (1.0 - blend) + shifted * blend

    base_lum = float(np.dot(base, [0.299, 0.587, 0.114]))
    out_lum = float(np.dot(out, [0.299, 0.587, 0.114]))
    min_sep = shift * 34.0
    if min_sep > 0.5:
        if lum >= 128.0 and base_lum - out_lum < min_sep:
            ratio = max(0.0, (base_lum - min_sep) / max(1e-6, out_lum))
            out = np.clip(out * ratio, 0.0, 255.0)
        elif lum < 128.0 and out_lum - base_lum < min_sep:
            ratio = (base_lum + min_sep) / max(1e-6, out_lum)
            out = np.clip(out * ratio, 0.0, 255.0)

    if color_mode == "local_gradient" and gradient_strength > 0.0:
        t = (x / max(1, img_w - 1)) * 0.62 + (y / max(1, img_h - 1)) * 0.38
        gs = float(np.clip(gradient_strength, 0.0, 1.0))
        tint = 1.0 + gs * 0.06 * (t - 0.5)
        out = np.clip(out * tint, 0.0, 255.0)

    return int(out[0]), int(out[1]), int(out[2])


def apply_ascii_watermark(
    image: np.ndarray,
    *,
    text: str = "",
    author_text: str = "",
    charset: str = _DEFAULT_CHARSET,
    cell_size: int = 18,
    opacity: float = 0.96,
    color: tuple[int, int, int] = (40, 40, 40),
    color_mode: ColorMode = "local",
    local_contrast: float = 0.10,
    stroke_width: int = 0,
    mode: LuminanceMode = "luminance",
    fixed_char: str = _FIXED_CHAR_DEFAULT,
    bg_filter: float = 0.0,
    random_scale: float = 0.0,
    author_inject_rate: float = 0.0,
    author_sequence_rate: float = 0.0,
    author_background_sequence_rate: float = 0.0,
    author_background_inject_rate: float = 0.0,
    author_background_chain_stride: int = 0,
    author_background_chain_phase: int = 0,
    contour_warp_strength: float = 0.0,
    density_jitter: int = 0,
    gradient_strength: float = 0.30,
    lum_mask: MaskMode = "none",
    mask_full_below: float = 120.0,
    mask_fade_end: float = 215.0,
    mask_bright_floor: float = 0.10,
    dark_contrast_boost: float = 0.0,
    dark_alpha_boost: float = 0.0,
    layout: LayoutMode = "grid",
    glyph_mode: GlyphMode = "ascii",
    particle_jitter: float = 0.55,
    particle_size_min: float = 0.52,
    particle_size_max: float = 1.48,
    particle_lum_size: bool = True,
    particle_skip_rate: float = 0.0,
    particle_dot_scale: float = 0.16,
    halftone_size: float = 1.0,
    halftone_screen_mix: float = 0.18,
    halftone_radius_cap: float = 1.0,
    halftone_min_radius: float = 0.35,
    halftone_gate: bool = False,
    halftone_font_fill: float = 1.0,
    halftone_min_level_scale: float = 1.0,
    use_halftone_ramp: bool = False,
    dither: DitherMode = "none",
    dither_strength: float = 0.75,
    render_font_size: int | None = None,
    author_mask_mode: AuthorMaskMode = "none",
    author_mask_position: AuthorMaskPosition = "corner_br",
    author_anchor_x: float = -1.0,
    author_anchor_y: float = -1.0,
    author_mask_scale: float = 1.0,
    author_mask_opacity: float = 1.0,
    author_mask_radius_boost: float = 1.35,
    author_mask_alpha_boost: float = 1.25,
    author_mask_tile_spacing: float = 0.35,
    author_fine_step: int = 3,
    author_dot_radius: int = 1,
    author_name_contrast: float = 0.42,
    fine_dot_base_contrast: float = 0.09,
    fine_dot_name_boost: float = 0.07,
    author_tile_contrast: float = 0.06,
    author_tile_alpha_scale: float = 0.38,
    author_zone_mask_floor: float = 0.62,
    author_zone_pad_cells: float = 4.5,
    author_bbox_halftone_pad: float = 4.5,
    tile_size: int = 10,
    tile_gap: int = 2,
    tile_corner_radius: int = 3,
    tile_fade_mode: TileFadeMode = "diagonal_tl_br",
    tile_fade_start: float = 0.30,
    tile_fade_end: float = 0.98,
    tile_blur_radius: float = 5.0,
    tile_frost: float = 0.45,
    tile_center_protect: float = 0.0,
    tile_center_protect_radius: float = 0.40,
    grid_passes: int = 1,
    double_grid: bool | None = None,
    skip_space_chars: bool = True,
    seed: int = 42,
) -> np.ndarray:
    """叠加 ASCII 网格、半调圆点或散布粒子。

    ``layout='halftone'``：规则网格半调（Glyph 式），格心圆点、半径随亮度。
    ``glyph_mode='dot'`` + ``layout='particle'``：随机散布圆点（旧实验）。
    ``layout='particle'`` + ``glyph_mode='ascii'``：变尺寸 ASCII 字符。

    ``lum_mask``:
    - ``dark_fade`` — 仅暗/中暗部，亮部完全无字；
    - ``lum_ramp`` — 全图分级，暗/中调满强度，最亮区淡出至 ``mask_bright_floor``。

    ``use_halftone_ramp`` + ``dither='bayer'``：半调字符 ramp（``@O0o·.``），
    字号由 ``render_font_size`` 控制，与网格密度解耦。

    半调粒子署名：
    - ``fine_stealth``：粗半调防盗 + 小字淡点署名 + 全图极淡平铺（难抠除）；
    - ``fine_full``：全页同色细点，仅名字略明显；
    - ``fine_dots``：仅角落细点署名。

    ``layout='tile_grid'``：圆角方格 + 空间渐变（默认对角线）；``tile_center_protect`` 可保护中心主体少糊。
    """
    _validate_input(image)
    if opacity <= 0.0:
        return image.copy()

    author = author_text.strip()
    repeat = author or text.strip() or "JW"
    author_letters = build_author_letters(author)

    if mode == "author_luminance":
        charset = (
            build_halftone_ramp_charset(author or repeat)
            if use_halftone_ramp
            else build_author_charset(author or repeat)
        )
        draw_mode: LuminanceMode = "luminance"
    else:
        draw_mode = mode
        if draw_mode == "luminance" and not charset:
            charset = _DEFAULT_CHARSET
        if draw_mode == "repeat_text" and author:
            repeat = author

    h, w = image.shape[:2]
    cell_w = max(8, int(cell_size))
    cell_h = max(cell_w, int(round(cell_w * 1.0)))
    font_ratio = 0.96 if halftone_gate else 0.92
    font_size = max(8, int(render_font_size if render_font_size else min(cell_w, cell_h) * font_ratio))

    passes = int(np.clip(grid_passes, 1, len(_GRID_PASS_SPECS)))
    if layout in ("halftone", "tile_grid"):
        passes = 1
    if double_grid is not None:
        passes = 2 if double_grid else 1

    rng = np.random.default_rng(seed)
    fill_char = fixed_char[:1] if fixed_char else "?"

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    base_font = _get_mono_font(font_size)

    work_image = image
    tile_fade_map: np.ndarray | None = None
    if layout == "tile_grid":
        tile_fade_map = _build_tile_fade_map(
            h, w,
            mode=tile_fade_mode,
            fade_start=tile_fade_start,
            fade_end=tile_fade_end,
        )
        tile_fade_map = _apply_tile_subject_protect(
            tile_fade_map,
            strength=tile_center_protect,
            protect_radius=tile_center_protect_radius,
            img_w=w,
            img_h=h,
        )
        work_image = _apply_tile_fade_blur(
            image, tile_fade_map, tile_blur_radius,
        )

    author_seq_idx = [0]
    n_cols = max(1, (w + cell_w - 1) // cell_w)
    n_rows = max(1, (h + cell_h - 1) // cell_h)
    bg_phase = int(author_background_chain_phase)
    if bg_phase <= 0 and author_background_chain_stride > 0:
        bg_phase = int(seed) % author_background_chain_stride
    contour_off_x: np.ndarray | None = None
    contour_off_y: np.ndarray | None = None
    contour_ang: np.ndarray | None = None
    if layout == "grid" and contour_warp_strength > 0.001:
        contour_off_x, contour_off_y, contour_ang = _build_contour_warp_maps(
            image,
            cell_w=cell_w,
            cell_h=cell_h,
            n_rows=n_rows,
            n_cols=n_cols,
            img_w=w,
            img_h=h,
            strength=contour_warp_strength,
        )
    paint_kw = dict(
        cell_w=cell_w,
        cell_h=cell_h,
        draw_mode=draw_mode,
        charset=charset,
        repeat=repeat,
        fill_char=fill_char,
        color_mode=color_mode,
        fixed_color=color,
        local_contrast=local_contrast,
        bg_filter=bg_filter,
        random_scale=random_scale,
        stroke_width=stroke_width,
        font_size=font_size,
        base_font=base_font,
        rng=rng,
        skip_space=skip_space_chars,
        author_letters=author_letters,
        author_name=author,
        author_sequence_rate=author_sequence_rate,
        author_inject_rate=author_inject_rate,
        author_seq_idx=author_seq_idx,
        density_jitter=density_jitter,
        gradient_strength=gradient_strength,
        img_w=w,
        img_h=h,
        lum_mask=lum_mask,
        mask_full_below=mask_full_below,
        mask_fade_end=mask_fade_end,
        mask_bright_floor=mask_bright_floor,
        dark_contrast_boost=dark_contrast_boost,
        dark_alpha_boost=dark_alpha_boost,
    )
    author_pixel_mask: np.ndarray | None = None
    author_pixel_bbox: tuple[int, int, int, int] | None = None
    author_tile_mask: np.ndarray | None = None
    author_grid_mask: np.ndarray | None = None
    grid_extra_kw = dict(
        halftone_gate=halftone_gate,
        halftone_screen_mix=halftone_screen_mix,
        halftone_font_fill=halftone_font_fill,
        halftone_min_level_scale=halftone_min_level_scale,
        use_halftone_ramp=use_halftone_ramp,
        dither=dither,
        dither_strength=dither_strength,
        author_pixel_bbox=author_pixel_bbox,
        author_zone_pad_cells=author_zone_pad_cells,
        author_background_sequence_rate=author_background_sequence_rate,
        author_background_inject_rate=author_background_inject_rate,
        author_background_chain_stride=author_background_chain_stride,
        author_background_chain_phase=bg_phase,
        overlay=overlay,
        grid_n_cols=n_cols,
        contour_off_x=contour_off_x,
        contour_off_y=contour_off_y,
        contour_ang=contour_ang,
    )
    particle_kw = dict(
        glyph_mode=glyph_mode,
        particle_jitter=particle_jitter,
        particle_size_min=particle_size_min,
        particle_size_max=particle_size_max,
        particle_lum_size=particle_lum_size,
        particle_skip_rate=particle_skip_rate,
        particle_dot_scale=particle_dot_scale,
    )

    halftone_kw = dict(
        halftone_size=halftone_size,
        halftone_screen_mix=halftone_screen_mix,
        halftone_radius_cap=halftone_radius_cap,
        halftone_min_radius=halftone_min_radius,
    )
    skip_coarse_halftone = False
    zone_kw = dict(
        author_zone_bbox=author_pixel_bbox,
        author_zone_pad_cells=author_zone_pad_cells,
        author_zone_mask_floor=author_zone_mask_floor,
    )

    if author and author_mask_mode != "none" and layout in ("halftone", "grid"):
        _ax = author_anchor_x if author_anchor_x >= 0.0 else 0.5
        _ay = author_anchor_y if author_anchor_y >= 0.0 else 0.54
        author_grid_mask, author_pixel_mask, author_pixel_bbox = _build_author_dot_mask(
            author,
            img_w=w,
            img_h=h,
            cell_w=cell_w,
            cell_h=cell_h,
            position=author_mask_position,
            mask_scale=author_mask_scale,
            tile_spacing=author_mask_tile_spacing,
            anchor_x=_ax,
            anchor_y=_ay,
        )
        zone_kw["author_zone_bbox"] = author_pixel_bbox
        grid_extra_kw["author_pixel_bbox"] = author_pixel_bbox
        if layout == "halftone":
            if author_mask_mode == "fine_stealth":
                pass  # 全页底纹在下方用均匀细点绘制，不用 tile_faint 重复完整署名
            halftone_kw.update(
                author_grid_mask=author_grid_mask,
                author_pixel_bbox=author_pixel_bbox,
                author_mask_mode=author_mask_mode,
                author_mask_opacity=author_mask_opacity,
                author_mask_radius_boost=author_mask_radius_boost,
                author_mask_alpha_boost=author_mask_alpha_boost,
                author_bbox_halftone_pad=author_bbox_halftone_pad,
                author_zone_mask_floor=author_zone_mask_floor,
                author_zone_pad_cells=author_zone_pad_cells,
            )

    if layout == "tile_grid":
        paint_fn = None  # type: ignore[assignment]
        use_scatter = False
    elif layout == "halftone":
        paint_fn = _paint_halftone
        use_scatter = False
    else:
        use_scatter = layout == "particle" or glyph_mode == "dot"
        paint_fn = _paint_scatter if use_scatter else _paint_ascii_grid

    char_idx = 0
    if layout == "tile_grid" and tile_fade_map is not None:
        tile_alpha = int(np.clip(opacity, 0.0, 1.0) * 255)
        _paint_rounded_tile_grid(
            draw,
            work_image,
            tile_fade_map,
            tile_size=tile_size,
            tile_gap=tile_gap,
            corner_radius=tile_corner_radius,
            alpha_byte=tile_alpha,
            tile_frost=tile_frost,
            local_contrast=local_contrast,
            color_mode=color_mode,
            fixed_color=color,
            img_w=w,
            img_h=h,
        )
    elif not skip_coarse_halftone:
        for pass_i in range(passes):
            ox_f, oy_f, alpha_scale = _GRID_PASS_SPECS[pass_i]
            alpha_byte = int(np.clip(opacity * alpha_scale, 0.0, 1.0) * 255)
            if layout == "halftone":
                pass_kw = {**paint_kw, **halftone_kw}
            elif use_scatter:
                pass_kw = {**paint_kw, **particle_kw}
            else:
                pass_kw = {**paint_kw, **grid_extra_kw}
            char_idx = paint_fn(
                draw,
                image,
                offset_x=int(cell_w * ox_f),
                offset_y=int(cell_h * oy_f),
                alpha_byte=alpha_byte,
                char_idx_start=char_idx,
                **pass_kw,
            )

    fine_alpha = int(np.clip(opacity * author_mask_opacity, 0.0, 1.0) * 255)

    if layout == "halftone" and author and author_mask_mode == "fine_full":
        _paint_fine_dot_field(
            draw, image,
            author_pixel_mask=author_pixel_mask,
            fine_step=author_fine_step,
            dot_radius=author_dot_radius,
            alpha_byte=fine_alpha,
            base_contrast=fine_dot_base_contrast,
            name_contrast_boost=fine_dot_name_boost,
            color_mode=color_mode,
            fixed_color=color,
            img_w=w, img_h=h,
            lum_mask=lum_mask,
            mask_full_below=mask_full_below,
            mask_fade_end=mask_fade_end,
            mask_bright_floor=mask_bright_floor,
            **zone_kw,
        )
    elif (
        layout == "halftone"
        and author
        and author_mask_mode == "fine_stealth"
        and author_pixel_mask is not None
    ):
        if author_tile_contrast > 0.0 and author_tile_alpha_scale > 0.0:
            tile_alpha = int(fine_alpha * float(np.clip(author_tile_alpha_scale, 0.1, 1.0)))
            _paint_faint_anti_crop_field(
                draw, image,
                fine_step=author_fine_step + 1,
                dot_radius=author_dot_radius,
                alpha_byte=tile_alpha,
                base_contrast=author_tile_contrast,
                color_mode=color_mode,
                fixed_color=color,
                img_w=w, img_h=h,
                lum_mask=lum_mask,
                mask_full_below=mask_full_below,
                mask_fade_end=mask_fade_end,
                mask_bright_floor=mask_bright_floor,
            )
        _paint_author_fine_dots(
            draw, image,
            author_pixel_mask,
            author_pixel_bbox,
            fine_step=author_fine_step,
            dot_radius=author_dot_radius,
            alpha_byte=fine_alpha,
            name_contrast=author_name_contrast,
            color_mode=color_mode,
            fixed_color=color,
            img_w=w, img_h=h,
        )
    elif (
        author
        and author_mask_mode == "fine_dots"
        and author_pixel_mask is not None
        and layout in ("halftone", "grid")
    ):
        if (
            layout == "grid"
            and author_tile_contrast > 0.0
            and author_tile_alpha_scale > 0.0
        ):
            tile_alpha = int(fine_alpha * float(np.clip(author_tile_alpha_scale, 0.1, 1.0)))
            _paint_faint_anti_crop_field(
                draw, image,
                fine_step=author_fine_step + 2,
                dot_radius=max(1, author_dot_radius - 1),
                alpha_byte=tile_alpha,
                base_contrast=author_tile_contrast,
                color_mode=color_mode,
                fixed_color=color,
                img_w=w, img_h=h,
                lum_mask=lum_mask,
                mask_full_below=mask_full_below,
                mask_fade_end=mask_fade_end,
                mask_bright_floor=mask_bright_floor,
            )
        _paint_author_fine_dots(
            draw,
            image,
            author_pixel_mask,
            author_pixel_bbox,
            fine_step=author_fine_step,
            dot_radius=author_dot_radius,
            alpha_byte=fine_alpha,
            name_contrast=author_name_contrast,
            color_mode=color_mode,
            fixed_color=color,
            img_w=w,
            img_h=h,
        )

    base = Image.fromarray(work_image).convert("RGBA")
    out = Image.alpha_composite(base, overlay)
    return np.array(out.convert("RGB"), dtype=np.uint8)
