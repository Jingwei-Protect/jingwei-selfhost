"""Adapter for guofei9987/blind_watermark (DWT-DCT-SVD).

MIT License — https://github.com/guofei9987/blind_watermark

Provides stronger robustness than the built-in DWT-only watermark:
- Survives JPEG compression, rotation up to 45°, random cropping, masking
- Supports Chinese text
- Uses DWT + DCT + SVD triple-domain embedding

Trade-off: slower than the built-in DWT (~2-5× depending on image size).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import cv2
import numpy as np
from blind_watermark import WaterMark


_DEFAULT_PASSWORD = 1234


def embed_blind_watermark(
    image: np.ndarray,
    text: str,
    *,
    password: int = _DEFAULT_PASSWORD,
) -> tuple[np.ndarray, int]:
    """Embed a blind watermark using DWT-DCT-SVD.

    Parameters
    ----------
    image : np.ndarray
        uint8 RGB, shape (H, W, 3).
    text : str
        Text to embed (supports Chinese, English, symbols).
    password : int
        Numeric password for embed/extract. Must match during extraction.

    Returns
    -------
    tuple[np.ndarray, int]
        (watermarked_image, wm_bit_length)
        wm_bit_length is needed for extraction — store it with the image.
    """
    if not text.strip():
        return image.copy(), 0

    tmp_in = Path(tempfile.mktemp(suffix=".png"))
    tmp_out = Path(tempfile.mktemp(suffix=".png"))

    try:
        cv2.imwrite(str(tmp_in), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

        bwm = WaterMark(password_img=password, password_wm=password)
        bwm.read_img(str(tmp_in))
        bwm.read_wm(text, mode='str')
        bwm.embed(str(tmp_out))
        wm_len = len(bwm.wm_bit)

        result_bgr = cv2.imread(str(tmp_out))
        result = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
        return result, wm_len
    finally:
        tmp_in.unlink(missing_ok=True)
        tmp_out.unlink(missing_ok=True)


def extract_blind_watermark(
    image: np.ndarray,
    wm_bit_length: int,
    *,
    password: int = _DEFAULT_PASSWORD,
) -> str:
    """Extract a blind watermark from a (possibly degraded) image.

    Parameters
    ----------
    image : np.ndarray
        uint8 RGB, shape (H, W, 3).
    wm_bit_length : int
        The bit length returned by embed_blind_watermark.
    password : int
        Must match the password used during embedding.

    Returns
    -------
    str
        Extracted text. May be garbled if image was too heavily modified.

    Raises
    ------
    ValueError
        If wm_bit_length <= 0.
    """
    if wm_bit_length <= 0:
        raise ValueError("wm_bit_length must be > 0")

    tmp_in = Path(tempfile.mktemp(suffix=".png"))

    try:
        cv2.imwrite(str(tmp_in), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

        bwm = WaterMark(password_img=password, password_wm=password)
        result = bwm.extract(str(tmp_in), wm_shape=wm_bit_length, mode='str')
        return result
    finally:
        tmp_in.unlink(missing_ok=True)
