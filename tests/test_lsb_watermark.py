"""M4 LSB 隱形水印模組單元測試。"""

import numpy as np
import pytest

from core.lsb_watermark import embed_lsb_watermark, extract_lsb_watermark


def _psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    if mse == 0.0:
        return float("inf")
    return 20.0 * np.log10(255.0 / np.sqrt(mse))


def _img(h: int = 256, w: int = 256, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 256, (h, w, 3), dtype=np.uint8)


def test_embed_extract_roundtrip_ascii() -> None:
    """ASCII + 中文混合文字往返完整恢復。"""
    text = "Artist: 张三 #2024"
    img = _img()
    watermarked = embed_lsb_watermark(img, text)
    recovered = extract_lsb_watermark(watermarked)
    assert recovered == text


def test_embed_extract_roundtrip_chinese() -> None:
    """全中文 UTF-8 文字往返。"""
    text = "画师小明的作品@2024"
    img = _img()
    watermarked = embed_lsb_watermark(img, text)
    recovered = extract_lsb_watermark(watermarked)
    assert recovered == text


def test_embed_extract_roundtrip_emoji() -> None:
    """4-byte UTF-8 Emoji 往返。"""
    text = "🎨"
    img = _img()
    watermarked = embed_lsb_watermark(img, text)
    recovered = extract_lsb_watermark(watermarked)
    assert recovered == text


def test_capacity_exceeded_raises() -> None:
    """文字長度超過影像容量應 raise ValueError。"""
    img = _img(8, 8)  # 8×8×3 = 192 bits = 24 bytes 容量，含 8 bytes header 僅剩 16 bytes
    long_text = "A" * 20  # 20 bytes payload，超出容量
    with pytest.raises(ValueError, match="too long"):
        embed_lsb_watermark(img, long_text)


def test_lsb_change_preserves_high_psnr() -> None:
    """嵌入後 PSNR > 50 dB（僅 LSB 改動，最大 ±1 per pixel）。"""
    text = "画师版权 2024"
    img = _img()
    watermarked = embed_lsb_watermark(img, text)
    psnr_val = _psnr(img, watermarked)
    assert psnr_val > 50.0, f"PSNR expected > 50 dB, got {psnr_val:.2f} dB"


def test_extract_from_unmodified_raises() -> None:
    """對未嵌入水印的隨機影像呼叫 extract 必須 raise ValueError（magic check 失敗）。"""
    img = _img(seed=99)
    with pytest.raises(ValueError):
        extract_lsb_watermark(img)


def test_input_validation() -> None:
    h, w = 64, 64
    with pytest.raises(ValueError):
        embed_lsb_watermark(np.zeros((h, w), dtype=np.uint8), "test")
    with pytest.raises(ValueError):
        embed_lsb_watermark(np.zeros((h, w, 3), dtype=np.float32), "test")
    with pytest.raises(ValueError):
        embed_lsb_watermark(np.zeros((h, w, 4), dtype=np.uint8), "test")
    with pytest.raises(ValueError):
        extract_lsb_watermark(np.zeros((h, w), dtype=np.uint8))
    with pytest.raises(ValueError):
        extract_lsb_watermark(np.zeros((h, w, 3), dtype=np.float32))
