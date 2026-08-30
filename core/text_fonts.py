"""Cross-platform font resolution for visible text watermarks.

Latin-only fonts (DejaVu, Arial) load before CJK-capable fonts on Linux Docker
images and silently fail to render Chinese — always prefer CJK paths when the
text requires it, and verify glyph metrics before accepting a font.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_ASSETS_DIR = Path(__file__).resolve().parent / "assets"

FONT_CJK_PATHS = [
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

FONT_LATIN_PATHS = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    str(_ASSETS_DIR / "DejaVuSans-Bold.ttf"),
]


def text_needs_cjk(text: str) -> bool:
    return any(ord(ch) > 127 for ch in text)


def font_renders_text(
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    text: str,
    size: int,
) -> bool:
    sample = text.strip()[:8] or "A"
    dummy = Image.new("L", (max(size * max(len(sample), 1), size * 2), size * 2))
    bbox = ImageDraw.Draw(dummy).textbbox((0, 0), sample, font=font)
    return (bbox[2] - bbox[0]) >= max(4, size // 4) and (bbox[3] - bbox[1]) >= max(4, size // 4)


def get_text_font(
    size: int,
    text: str = "",
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    needs_cjk = text_needs_cjk(text)
    paths = (
        FONT_CJK_PATHS + FONT_LATIN_PATHS
        if needs_cjk
        else FONT_LATIN_PATHS + FONT_CJK_PATHS
    )
    for path in paths:
        try:
            font = ImageFont.truetype(path, size)
            if not needs_cjk or font_renders_text(font, text, size):
                return font
        except (OSError, IOError):
            continue
    return ImageFont.load_default()
