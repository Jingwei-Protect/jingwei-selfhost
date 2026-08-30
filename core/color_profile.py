"""sRGB ICC for protect/export — consistent display on mobile vs desktop.

Uploads are converted to sRGB RGB before watermarking; outputs are tagged sRGB.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image

_SRGB_ICC: bytes | None = None


def srgb_icc_bytes() -> bytes | None:
    """Return cached sRGB ICC profile bytes for PIL ``icc_profile=`` save kwarg."""
    global _SRGB_ICC
    if _SRGB_ICC is not None:
        return _SRGB_ICC
    try:
        from PIL import ImageCms

        profile = ImageCms.createProfile("sRGB")
        _SRGB_ICC = ImageCms.ImageCmsProfile(profile).tobytes()
    except Exception:
        _SRGB_ICC = None
    return _SRGB_ICC


def decode_upload_pil(img: Image.Image) -> tuple[np.ndarray, np.ndarray | None]:
    """Decode an open PIL image to sRGB uint8 RGB (+ optional alpha).

    Uses embedded ICC when present so wide-gamut uploads map to sRGB once,
    matching tagged protect outputs.
    """
    work = img
    try:
        from PIL import ImageCms

        icc_bytes = work.info.get("icc_profile")
        if icc_bytes:
            src = ImageCms.ImageCmsProfile(io.BytesIO(icc_bytes))
            dst = ImageCms.createProfile("sRGB")
            mode = work.mode
            if mode not in ("RGB", "RGBA", "L"):
                work = work.convert("RGBA" if "A" in mode else "RGB")
                mode = work.mode
            out_mode = "RGB" if mode == "L" else mode
            work = ImageCms.profileToProfile(
                work, src, dst, outputMode=out_mode, renderingIntent=0,
            )
    except Exception:
        pass

    if work.mode == "RGBA":
        arr = np.array(work, dtype=np.uint8)
        return arr[:, :, :3].copy(), arr[:, :, 3].copy()
    if work.mode == "L":
        gray = np.array(work, dtype=np.uint8)
        rgb = np.stack([gray, gray, gray], axis=-1)
        return rgb, None
    return np.array(work.convert("RGB"), dtype=np.uint8), None
