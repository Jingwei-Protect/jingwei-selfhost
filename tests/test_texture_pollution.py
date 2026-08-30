"""M6 紋理污染模組單元測試。"""

import numpy as np
import pytest

from core.texture_pollution import (
    _generate_moire_pattern,
    _shape_spectrum,
    apply_texture_pollution,
)


def _psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    if mse == 0.0:
        return float("inf")
    return 20.0 * np.log10(255.0 / np.sqrt(mse))


def _img(seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 256, (256, 256, 3), dtype=np.uint8)


def test_output_shape_unchanged() -> None:
    """三種 texture_type 各跑一次，shape 與 dtype 不變。"""
    img = _img()
    for ttype in ("moire", "halftone", "noise"):
        out = apply_texture_pollution(img, texture_type=ttype, opacity=0.05, seed=42)
        assert out.shape == img.shape, f"{ttype} shape mismatch"
        assert out.dtype == np.uint8, f"{ttype} dtype mismatch"


def test_opacity_zero_returns_identical() -> None:
    """opacity=0 觸發 fast-path，輸出與輸入逐像素完全相同。"""
    img = _img()
    out = apply_texture_pollution(img, opacity=0.0)
    assert np.array_equal(img, out)


def test_default_opacity_meets_quality() -> None:
    """opacity=0.05, moire → PSNR > 38 dB（PRD §6.4 中度門檻）。"""
    img = _img()
    out = apply_texture_pollution(img, texture_type="moire", opacity=0.05, seed=42)
    psnr_val = _psnr(img, out)
    assert psnr_val > 38.0, f"PSNR expected > 38 dB, got {psnr_val:.2f} dB"


def test_deterministic_with_seed() -> None:
    img = _img()
    out1 = apply_texture_pollution(img, texture_type="moire", opacity=0.05, seed=42)
    out2 = apply_texture_pollution(img, texture_type="moire", opacity=0.05, seed=42)
    assert np.array_equal(out1, out2)


def test_all_texture_types_supported() -> None:
    """moire / halftone / noise 三者均能無 exception 執行並輸出 uint8。"""
    img = _img()
    for ttype in ("moire", "halftone", "noise"):
        out = apply_texture_pollution(
            img, texture_type=ttype, opacity=0.05, frequency=0.5, seed=42
        )
        assert out.dtype == np.uint8
        assert out.shape == img.shape


def test_spectral_energy_in_target_band() -> None:
    """單獨 pattern 經 _shape_spectrum 後，[0.3, 0.5] 環狀區內能量占比 > 50%。"""
    rng = np.random.default_rng(42)
    raw = _generate_moire_pattern((256, 256), frequency=0.5, rng=rng)
    shaped = _shape_spectrum(raw, target_band=(0.3, 0.5))

    F = np.fft.fft2(shaped)
    power = (F * np.conj(F)).real

    h, w = shaped.shape
    fy = np.fft.fftfreq(h)
    fx = np.fft.fftfreq(w)
    R = np.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2)

    in_band = (R >= 0.3) & (R <= 0.5)
    energy_in_band = float(power[in_band].sum())
    energy_total = float(power.sum())
    ratio = energy_in_band / max(energy_total, 1e-12)

    assert ratio > 0.5, f"Energy ratio in [0.3, 0.5] expected > 0.5, got {ratio:.4f}"


def test_input_validation() -> None:
    h, w = 64, 64
    with pytest.raises(ValueError):
        apply_texture_pollution(np.zeros((h, w), dtype=np.uint8))
    with pytest.raises(ValueError):
        apply_texture_pollution(np.zeros((h, w, 3), dtype=np.float32))
    with pytest.raises(ValueError):
        apply_texture_pollution(np.zeros((h, w, 4), dtype=np.uint8))


def test_invalid_texture_type_raises() -> None:
    img = _img()
    with pytest.raises(ValueError, match="texture_type"):
        apply_texture_pollution(img, texture_type="unknown")  # type: ignore[arg-type]
