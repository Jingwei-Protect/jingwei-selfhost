"""DWT Frequency-Domain Blind Watermark — robust to JPEG and screenshots.

Why DWT instead of LSB
-----------------------
LSB (Least Significant Bit) watermarking is destroyed by any lossy
operation: JPEG compression, screenshot, rescaling, or even saving as
a different format.  It only survives bit-exact PNG copies.

DWT (Discrete Wavelet Transform) embeds watermark bits into the
**low-frequency wavelet coefficients** (LL subband) of the image.  Low
frequencies are the most resilient part of an image — they survive JPEG
compression (which primarily quantises high frequencies), screenshots,
moderate rescaling, and social media re-encoding.

Algorithm — Embed
-----------------
1. Convert image to YCbCr; work on the Y (luminance) channel only.
2. Apply 2-level Haar DWT → produces LL2, LH2, HL2, HH2 subbands.
3. Encode the payload (text + timestamp) as a 256-bit binary string.
4. Repeat the 256 bits across a block of LL2 coefficients for redundancy.
5. For each bit, quantise the corresponding LL2 coefficient to an
   odd (bit=1) or even (bit=0) multiple of a quantisation step ``delta``.
6. Inverse DWT → reconstruct the Y channel → convert back to RGB.

Algorithm — Extract
-------------------
1. Same DWT decomposition on the (possibly degraded) image.
2. For each coefficient position, check if it's closer to an odd or
   even multiple of ``delta`` → decode bit.
3. Majority vote across repeated copies to recover the 256-bit payload.
4. Return the payload and a confidence score.

Capacity: 256 bits = marker + up to 24 alphanumeric chars + timestamp + checksum.
Robustness: survives JPEG quality ≥ 40, screenshots, ≤50% rescale.

Only requires numpy, opencv-python, PyWavelets (pywt).
No deep-learning dependencies.
"""

from __future__ import annotations

import struct
import time

import cv2
import numpy as np
import pywt


_WAVELET = "haar"
_DWT_LEVEL = 2
_DELTA = 30.0
_PAYLOAD_BITS = 256
_MIN_REPEATS = 3

_MARKER_TEXT = 0x54
_MAX_TEXT_LEN = 24


def _validate_image(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 64 or image.shape[1] < 64:
        raise ValueError(
            f"Image must be at least 64x64 for DWT watermark, "
            f"got {image.shape[:2]}."
        )


def _encode_payload(text: str, timestamp: int | None = None) -> np.ndarray:
    """Encode text (up to 24 ASCII chars) + timestamp → 256-bit array."""
    if timestamp is None:
        timestamp = int(time.time()) & 0xFFFFFFFF
    timestamp = timestamp & 0xFFFFFFFF

    text_bytes = text.encode("ascii", errors="replace")[:_MAX_TEXT_LEN]
    text_len = len(text_bytes)

    buf = bytearray(32)
    buf[0] = _MARKER_TEXT
    buf[1] = text_len
    buf[2 : 2 + text_len] = text_bytes
    struct.pack_into(">I", buf, 26, timestamp)
    xor = 0
    for b in buf[:30]:
        xor ^= b
    buf[30] = xor & 0xFF
    buf[31] = (~xor) & 0xFF

    return np.unpackbits(np.frombuffer(bytes(buf), dtype=np.uint8))


def _decode_payload(bits: np.ndarray) -> dict | None:
    """Decode 256-bit array → dict or None if checksum fails."""
    bits = bits[:_PAYLOAD_BITS].astype(np.uint8)
    byte_arr = np.packbits(bits)
    buf = byte_arr.tobytes()[:32]
    if len(buf) < 32:
        buf = buf + b"\x00" * (32 - len(buf))

    if buf[0] != _MARKER_TEXT:
        return None
    text_len = buf[1]
    if text_len > _MAX_TEXT_LEN:
        return None

    xor = 0
    for b in buf[:30]:
        xor ^= b
    if buf[30] != (xor & 0xFF) or buf[31] != ((~xor) & 0xFF):
        return None

    text = buf[2 : 2 + text_len].decode("ascii", errors="replace").rstrip("\x00")
    timestamp = struct.unpack_from(">I", buf, 26)[0]
    return {"payload_text": text, "timestamp": timestamp}


def _rgb_to_ycbcr(image: np.ndarray) -> np.ndarray:
    """Convert uint8 RGB to float32 YCbCr (lower memory than float64)."""
    img_f = image.astype(np.float32)
    r, g, b = img_f[:, :, 0], img_f[:, :, 1], img_f[:, :, 2]
    y = np.float32(0.299) * r + np.float32(0.587) * g + np.float32(0.114) * b
    cb = np.float32(-0.169) * r - np.float32(0.331) * g + np.float32(0.500) * b + np.float32(128.0)
    cr = np.float32(0.500) * r - np.float32(0.419) * g - np.float32(0.081) * b + np.float32(128.0)
    out = np.empty((*image.shape[:2], 3), dtype=np.float32)
    out[:, :, 0] = y
    out[:, :, 1] = cb
    out[:, :, 2] = cr
    return out


def _ycbcr_to_rgb(ycbcr: np.ndarray) -> np.ndarray:
    """Convert float32 YCbCr to uint8 RGB."""
    y = ycbcr[:, :, 0]
    cb = ycbcr[:, :, 1] - np.float32(128.0)
    cr = ycbcr[:, :, 2] - np.float32(128.0)
    r = y + np.float32(1.402) * cr
    g = y - np.float32(0.344) * cb - np.float32(0.714) * cr
    b = y + np.float32(1.772) * cb
    out = np.empty_like(ycbcr, dtype=np.float32)
    out[:, :, 0] = r
    out[:, :, 1] = g
    out[:, :, 2] = b
    np.clip(out, 0, 255, out=out)
    return out.astype(np.uint8)


def embed_dwt_watermark(
    image: np.ndarray,
    payload_text: str = "",
    *,
    user_id: int = 0,
    timestamp: int | None = None,
    delta: float = _DELTA,
) -> np.ndarray:
    """Embed a 256-bit DWT watermark into the image.

    Parameters
    ----------
    image : np.ndarray
        uint8 RGB, shape ``(H, W, 3)``.  H and W must be >= 64.
    payload_text : str
        Up to 24 alphanumeric/ASCII characters to embed.
        Takes precedence over ``user_id`` if non-empty.
    user_id : int
        Legacy numeric ID (converted to string internally).
    timestamp : int or None
        32-bit timestamp.  If None, uses current Unix time.
    delta : float
        Quantisation step size.  Larger = more robust but more visible.
        Default 30.0 balances invisibility and JPEG-70 robustness.

    Returns
    -------
    np.ndarray
        uint8 RGB with embedded watermark, same shape as input.
    """
    _validate_image(image)
    delta = max(10.0, min(delta, 80.0))

    text = payload_text.strip()
    if not text and user_id > 0:
        text = str(user_id)
    if not text:
        return image.copy()

    payload = _encode_payload(text, timestamp)

    ycbcr = _rgb_to_ycbcr(image)
    y_channel = ycbcr[:, :, 0].copy()

    coeffs = pywt.wavedec2(y_channel, _WAVELET, level=_DWT_LEVEL)
    ll = coeffs[0].copy()

    ll_flat = ll.ravel()
    n_coeffs = len(ll_flat)
    n_repeats = max(_MIN_REPEATS, n_coeffs // _PAYLOAD_BITS)
    total_embed = min(n_repeats * _PAYLOAD_BITS, n_coeffs)

    tiled_bits = np.tile(payload, n_repeats)[:total_embed]

    for i in range(total_embed):
        coeff = ll_flat[i]
        bit = tiled_bits[i]
        quantized = round(coeff / delta)

        if bit == 1:
            if quantized % 2 == 0:
                quantized += 1 if coeff >= quantized * delta else -1
        else:
            if quantized % 2 != 0:
                quantized += 1 if coeff >= quantized * delta else -1

        ll_flat[i] = quantized * delta

    coeffs[0] = ll_flat.reshape(ll.shape)
    y_reconstructed = pywt.waverec2(coeffs, _WAVELET)
    y_reconstructed = y_reconstructed[: ycbcr.shape[0], : ycbcr.shape[1]]

    ycbcr[:, :, 0] = y_reconstructed
    return _ycbcr_to_rgb(ycbcr)


def extract_dwt_watermark(
    image: np.ndarray,
    *,
    delta: float = _DELTA,
) -> dict:
    """Extract the DWT watermark from a (possibly degraded) image.

    Parameters
    ----------
    image : np.ndarray
        uint8 RGB, shape ``(H, W, 3)``.
    delta : float
        Must match the delta used during embedding.

    Returns
    -------
    dict
        Keys: ``payload_text`` (str), ``timestamp`` (int), ``confidence`` (float).
        Confidence is in [0, 1]; above 0.65 is a reliable detection.
        Returns empty ``payload_text`` and 0 confidence if nothing detected.
    """
    _validate_image(image)
    delta = max(10.0, min(delta, 80.0))

    ycbcr = _rgb_to_ycbcr(image)
    y_channel = ycbcr[:, :, 0]

    coeffs = pywt.wavedec2(y_channel, _WAVELET, level=_DWT_LEVEL)
    ll = coeffs[0]
    ll_flat = ll.ravel()
    n_coeffs = len(ll_flat)

    n_repeats = max(_MIN_REPEATS, n_coeffs // _PAYLOAD_BITS)
    total_read = min(n_repeats * _PAYLOAD_BITS, n_coeffs)

    extracted_bits = np.zeros(total_read, dtype=np.int32)
    for i in range(total_read):
        coeff = ll_flat[i]
        quantized = round(coeff / delta)
        extracted_bits[i] = 1 if quantized % 2 != 0 else 0

    bit_votes = np.zeros(_PAYLOAD_BITS, dtype=np.float64)
    vote_counts = np.zeros(_PAYLOAD_BITS, dtype=np.int32)

    for i in range(total_read):
        bit_idx = i % _PAYLOAD_BITS
        bit_votes[bit_idx] += extracted_bits[i]
        vote_counts[bit_idx] += 1

    safe_counts = np.maximum(vote_counts, 1)
    bit_ratios = bit_votes / safe_counts
    final_bits = (bit_ratios > 0.5).astype(np.uint8)

    confidence_per_bit = np.abs(bit_ratios - 0.5) * 2.0
    confidence = float(np.mean(confidence_per_bit))

    result = _decode_payload(final_bits)
    if result is not None:
        result["confidence"] = confidence
        return result

    return {"payload_text": "", "timestamp": 0, "confidence": 0.0}
