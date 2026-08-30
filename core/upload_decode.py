"""Shared upload bytes → PIL decode for API routes (protect, inspect, verify)."""

from __future__ import annotations

import io

from PIL import Image, ImageFile, UnidentifiedImageError

ImageFile.LOAD_TRUNCATED_IMAGES = True


def open_upload_image(data: bytes) -> Image.Image:
    """Open uploaded image bytes; raise ValueError with Chinese hint on failure."""
    if len(data) < 12:
        raise ValueError("文件过短或已损坏，请重新导出 JPG/PNG 后上传。")
    head = data[:12]
    if head[:2] == b"\xff\xd8":
        pass
    elif head[:8] == b"\x89PNG\r\n\x1a\n":
        pass
    elif head[4:12] in (b"ftypheic", b"ftypheix", b"ftypmif1", b"ftypavif"):
        raise ValueError(
            "疑似 HEIC/HEIF/AVIF，当前流程请先在相册中另存为 JPG 或 PNG 后再上传。"
        )
    else:
        raise ValueError(
            "无法识别图片格式，请上传 JPG、PNG 或 WebP 原图（避免仅改扩展名的文件）。"
        )
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except UnidentifiedImageError as exc:
        raise ValueError(
            "图片无法解码，可能已损坏、被平台转码，或扩展名与实际格式不符。"
            "请换用相册导出的 JPG/PNG 原图重试。"
        ) from exc
    except Exception as exc:
        raise ValueError(
            f"图片无法解码：{exc}。请换用 JPG/PNG 原图重试。"
        ) from exc
    return img
