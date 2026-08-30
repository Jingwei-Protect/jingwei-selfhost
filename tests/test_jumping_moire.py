"""Unit tests for ``core.jumping_moire``."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from core.jumping_moire import _HIGH_BAND, _LOW_BAND, apply_jumping_moire


def _flat_image(size: int = 256, gray: int = 128) -> np.ndarray:
    return np.full((size, size, 3), gray, dtype=np.uint8)


def _rgb_to_y(rgb: np.ndarray) -> np.ndarray:
    f = rgb.astype(np.float32)
    return 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]


def _band_energy(field: np.ndarray, freq_min: float, freq_max: float) -> float:
    h, w = field.shape
    fy = np.fft.fftfreq(h).reshape(-1, 1)
    fx = np.fft.fftfreq(w).reshape(1, -1)
    radius = np.sqrt(fy * fy + fx * fx)
    mask = (radius >= freq_min) & (radius <= freq_max)
    spec = np.fft.fft2(field)
    return float(np.sum(np.abs(spec[mask]) ** 2))


def test_shape_dtype_preserved() -> None:
    img = _flat_image(128)
    out = apply_jumping_moire(img, opacity=0.15, region_grid_size=8, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_deterministic_with_seed() -> None:
    img = _flat_image(128)
    a = apply_jumping_moire(img, opacity=0.15, region_grid_size=8, seed=42)
    b = apply_jumping_moire(img, opacity=0.15, region_grid_size=8, seed=42)
    assert np.array_equal(a, b)


def test_different_seeds_produce_different_output() -> None:
    img = _flat_image(128)
    a = apply_jumping_moire(img, opacity=0.15, region_grid_size=8, seed=1)
    b = apply_jumping_moire(img, opacity=0.15, region_grid_size=8, seed=2)
    assert not np.array_equal(a, b)


def test_dual_band_energy() -> None:
    img = _flat_image(256)
    out = apply_jumping_moire(img, opacity=0.20, region_grid_size=8, seed=42)
    diff = _rgb_to_y(out) - _rgb_to_y(img)
    low_e = _band_energy(diff, *_LOW_BAND)
    high_e = _band_energy(diff, *_HIGH_BAND)
    total_e = float(np.sum(np.abs(np.fft.fft2(diff)) ** 2))
    assert low_e > 0.05 * total_e
    assert high_e > 0.05 * total_e


def test_resize_survival() -> None:
    size = 256
    img = _flat_image(size)
    out = apply_jumping_moire(img, opacity=0.20, region_grid_size=8, seed=42)

    diff_orig = _rgb_to_y(out) - _rgb_to_y(img)
    low_orig = _band_energy(diff_orig, *_LOW_BAND)

    pil_out = Image.fromarray(out)
    pil_in = Image.fromarray(img)
    out_rt = np.array(
        pil_out.resize((size // 2, size // 2), Image.BICUBIC)
        .resize((size, size), Image.BICUBIC),
        dtype=np.uint8,
    )
    in_rt = np.array(
        pil_in.resize((size // 2, size // 2), Image.BICUBIC)
        .resize((size, size), Image.BICUBIC),
        dtype=np.uint8,
    )
    diff_rt = _rgb_to_y(out_rt) - _rgb_to_y(in_rt)
    low_rt = _band_energy(diff_rt, *_LOW_BAND)

    assert low_rt >= 0.30 * low_orig, f"low band survival too low: {low_rt / low_orig:.2%}"


def test_input_validation() -> None:
    with pytest.raises(ValueError):
        apply_jumping_moire(np.zeros((128, 128, 3), dtype=np.float32))
    with pytest.raises(ValueError):
        apply_jumping_moire(np.zeros((32, 32, 3), dtype=np.uint8))
    with pytest.raises(ValueError):
        apply_jumping_moire(_flat_image(128), opacity=0.5)
    with pytest.raises(ValueError):
        apply_jumping_moire(_flat_image(128), region_grid_size=2)
