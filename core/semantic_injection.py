"""Semantic injection patch for adversarial VLM poisoning.

Renders large, perspective-distorted, semi-transparent "semantic poison" keywords
across the entire image.  The keywords (e.g. "Blurry", "Low Resolution") are
intended to be picked up by VLM captioning / CLIP vision encoders, causing the
model to misclassify or misdescribe the image content.

Visual impact is HIGH by design -- this mode is opt-in when the user accepts
visible damage in exchange for stronger adversarial disruption.

No deep-learning dependencies.  Uses only Pillow and numpy.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from core.text_fonts import get_text_font as _get_font

POISON_KEYWORDS_EN = [
    "Blurry", "Black and White", "Low Resolution",
    "Sketch", "Corrupted", "Error", "Distorted", "Noise",
]
POISON_KEYWORDS_ZH = ["模糊", "黑白", "低解析度", "草稿", "損壞", "錯誤"]


def _find_perspective_coeffs(
    src_points: list[tuple[float, float]],
    dst_points: list[tuple[float, float]],
) -> list[float]:
    """Compute 8 perspective transform coefficients from 4 point pairs.

    Solves the system  A @ h = b  where h are the 8 unknowns used by
    ``PIL.Image.transform(PERSPECTIVE, ...)``.
    """
    A: list[list[float]] = []
    b: list[float] = []
    for (sx, sy), (dx, dy) in zip(src_points, dst_points):
        A.append([dx, dy, 1, 0, 0, 0, -sx * dx, -sx * dy])
        A.append([0, 0, 0, dx, dy, 1, -sy * dx, -sy * dy])
        b.append(sx)
        b.append(sy)
    Am = np.array(A, dtype=np.float64)
    bm = np.array(b, dtype=np.float64)
    h = np.linalg.solve(Am, bm)
    return h.tolist()


def apply_semantic_injection(
    image: np.ndarray,
    *,
    keywords: list[str] | None = None,
    opacity: float = 0.25,
    patch_count: int = 12,
    seed: int = 42,
) -> np.ndarray:
    """Scatter large, perspective-warped keyword patches across *image*.

    Parameters
    ----------
    image : np.ndarray
        RGB uint8, shape ``(H, W, 3)``.
    keywords : list[str] | None
        Keyword strings to render.  ``None`` uses built-in EN+ZH list.
    opacity : float
        Alpha blend strength, clamped to ``[0.15, 0.40]``.
    patch_count : int
        Number of keyword patches to place (8-20 recommended).
    seed : int
        Random seed for deterministic output.

    Returns
    -------
    np.ndarray
        RGB uint8, same shape as input.
    """
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Input must be uint8 RGB with shape (H, W, 3).")

    kw_list = keywords if keywords else POISON_KEYWORDS_EN + POISON_KEYWORDS_ZH
    opacity = float(np.clip(opacity, 0.15, 0.40))

    h, w = image.shape[:2]
    rng = np.random.RandomState(seed)

    base = Image.fromarray(image).convert("RGBA")

    for i in range(patch_count):
        kw = kw_list[i % len(kw_list)]
        font_size = rng.randint(48, 121)
        font = _get_font(font_size, kw)

        dummy = Image.new("RGBA", (1, 1))
        bbox = ImageDraw.Draw(dummy).textbbox((0, 0), kw, font=font)
        tw = bbox[2] - bbox[0] + font_size
        th = bbox[3] - bbox[1] + font_size

        tile = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        ImageDraw.Draw(tile).text(
            (font_size // 2, font_size // 2),
            kw,
            font=font,
            fill=(255, 255, 255, 255),
        )

        angle = rng.uniform(0, 360)
        tile = tile.rotate(angle, expand=True, resample=Image.BICUBIC)
        tw2, th2 = tile.size

        max_disp = max(tw2, th2) * 0.05
        src = [(0, 0), (tw2, 0), (tw2, th2), (0, th2)]
        dst = [
            (s[0] + rng.uniform(-max_disp, max_disp),
             s[1] + rng.uniform(-max_disp, max_disp))
            for s in src
        ]
        try:
            coeffs = _find_perspective_coeffs(src, dst)
            tile = tile.transform(
                (tw2, th2), Image.PERSPECTIVE, coeffs,
                resample=Image.BICUBIC,
            )
        except np.linalg.LinAlgError:
            pass

        arr = np.array(tile, dtype=np.float32)
        arr[:, :, 3] = (arr[:, :, 3] * opacity).clip(0, 255)
        tile = Image.fromarray(arr.astype(np.uint8))

        px = rng.randint(-tw2 // 2, max(w - tw2 // 2, 1))
        py = rng.randint(-th2 // 2, max(h - th2 // 2, 1))

        paste_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        paste_layer.paste(tile, (px, py), tile)
        base = Image.alpha_composite(base, paste_layer)

    return np.array(base.convert("RGB"), dtype=np.uint8)
