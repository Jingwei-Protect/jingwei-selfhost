"""M4：LSB 隱形水印模組。

以最低有效位元（Least Significant Bit）技術將文字水印嵌入影像，
嵌入後視覺無感（最大 ±1 pixel，PSNR > 50 dB）。

資料格式（embed / extract 雙向相容）：
    [4 bytes magic: b'WMRK'] [4 bytes BE length] [UTF-8 payload]

magic number 確保 extract 能明確辨識「此影像是否已嵌入水印」；
對未嵌入的影像呼叫 extract 時，magic check 失敗即 raise ValueError，
行為確定，不回傳垃圾。

嵌入順序：以 row-major 順序逐像素的 R、G、B 三通道依序嵌入，
位元序為 MSB first（每個 byte 的最高有效位優先）。

本模組不依賴任何深度學習框架，僅使用 numpy、struct。
"""

from __future__ import annotations

import struct

import numpy as np

_MAGIC = b"WMRK"
_HEADER_BYTES = 8  # 4 magic + 4 length
_HEADER_BITS = _HEADER_BYTES * 8


def _validate_input(image: np.ndarray) -> None:
    """驗證輸入影像格式，不符合時 raise ValueError。

    接受條件：
    - dtype 必須為 uint8。
    - shape 必須為 (H, W, 3)。
    - H ≥ 8 且 W ≥ 8。

    Raises
    ------
    ValueError
    """
    if image.dtype != np.uint8:
        raise ValueError(
            f"Input dtype must be uint8, got {image.dtype}. "
            "Float inputs are rejected by design; convert to uint8 first."
        )
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(
            f"Input must be an HxWx3 RGB array, got shape {image.shape}."
        )
    h, w = image.shape[:2]
    if h < 8 or w < 8:
        raise ValueError(
            f"Image dimensions must be at least 8×8, got {h}×{w}."
        )


def _bytes_to_bits(data: bytes) -> list[int]:
    """將 bytes 轉換為 MSB-first 位元串列。"""
    return [(byte >> (7 - i)) & 1 for byte in data for i in range(8)]


def _bits_to_bytes(bits: list[int]) -> bytes:
    """將 MSB-first 位元串列轉換回 bytes。"""
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        out.append(byte)
    return bytes(out)


def embed_lsb_watermark(image: np.ndarray, text: str) -> np.ndarray:
    """將文字水印以 LSB 技術嵌入影像。

    嵌入格式：
        data = b'WMRK' + struct.pack('>I', len(payload)) + payload
        （magic 4 bytes + length 4 bytes + UTF-8 payload）

    嵌入方式：以 row-major 順序逐像素 R→G→B 依序修改 LSB，
    位元序為 MSB first。此為破壞性操作：對已含水印的影像再次 embed
    將覆蓋原有水印。

    Parameters
    ----------
    image:
        輸入影像，uint8 RGB，shape (H, W, 3)。
    text:
        要嵌入的文字（任意 UTF-8，含中文、Emoji）。

    Returns
    -------
    np.ndarray
        嵌入水印後的影像，uint8 RGB，shape 與輸入相同，PSNR > 50 dB。

    Raises
    ------
    ValueError
        輸入格式不符，或文字長度超過影像容量。
    """
    _validate_input(image)

    payload = text.encode("utf-8")
    data = _MAGIC + struct.pack(">I", len(payload)) + payload
    bits = _bytes_to_bits(data)

    h, w = image.shape[:2]
    total_bits = h * w * 3
    if len(bits) > total_bits:
        raise ValueError(
            f"Text too long: needs {len(bits)} bits, "
            f"image capacity is {total_bits} bits "
            f"({total_bits // 8} bytes)."
        )

    result = image.copy()
    flat = result.reshape(-1)  # row-major R,G,B,R,G,B,...

    for idx, bit in enumerate(bits):
        flat[idx] = (flat[idx] & 0xFE) | bit

    return result


def extract_lsb_watermark(image: np.ndarray) -> str:
    """從影像中提取 LSB 水印文字。

    讀取順序與 embed 完全對應（row-major，MSB first）。

    驗證流程：
    1. 讀取前 32 bits → 驗證 magic == b'WMRK'；不符即 raise ValueError。
    2. 讀取接下來 32 bits → 解析 payload 長度 length。
    3. 容量前置檢查，防止記憶體溢出。
    4. 讀取 length × 8 bits → 組 bytes → UTF-8 解碼。

    Parameters
    ----------
    image:
        待提取水印的 uint8 RGB 影像，shape (H, W, 3)。

    Returns
    -------
    str
        嵌入的文字水印。

    Raises
    ------
    ValueError
        影像格式不符、magic 驗證失敗、長度超出容量，
        或 payload 非合法 UTF-8。
    """
    _validate_input(image)

    h, w = image.shape[:2]
    flat = image.reshape(-1)
    total_bits = h * w * 3

    def _read_bits(start: int, count: int) -> list[int]:
        return [int(flat[start + i]) & 1 for i in range(count)]

    # 讀 magic（前 32 bits）
    if total_bits < _HEADER_BITS:
        raise ValueError("Image too small to contain a watermark.")

    magic_bits = _read_bits(0, 32)
    magic_bytes = _bits_to_bytes(magic_bits)
    if magic_bytes != _MAGIC:
        raise ValueError("No valid watermark found.")

    # 讀 length（接下來 32 bits）
    length_bits = _read_bits(32, 32)
    length = struct.unpack(">I", _bits_to_bytes(length_bits))[0]

    max_payload_bytes = (total_bits - _HEADER_BITS) // 8
    if length > max_payload_bytes:
        raise ValueError(
            f"Watermark length header ({length} bytes) exceeds image capacity "
            f"({max_payload_bytes} bytes); image may not be watermarked."
        )

    # 讀 payload
    payload_bits = _read_bits(_HEADER_BITS, length * 8)
    payload = _bits_to_bytes(payload_bits)

    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "Extracted bytes are not valid UTF-8; image may not be watermarked."
        ) from exc
