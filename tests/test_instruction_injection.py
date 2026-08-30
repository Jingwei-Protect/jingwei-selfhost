"""tests/test_instruction_injection.py — instruction injection unit tests."""

from __future__ import annotations

import numpy as np

from core.instruction_injection import apply_instruction_injection


def _synth(h: int = 64, w: int = 64) -> np.ndarray:
    return np.random.default_rng(0).integers(0, 256, (h, w, 3), dtype=np.uint8)


def test_shape_dtype():
    img = _synth()
    out = apply_instruction_injection(img, opacity=0.12, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_deterministic():
    img = _synth()
    a = apply_instruction_injection(img, opacity=0.12, seed=42)
    b = apply_instruction_injection(img, opacity=0.12, seed=42)
    assert np.array_equal(a, b)


def test_spatial_only():
    img = _synth()
    out = apply_instruction_injection(img, freq_opacity=0.0, seed=42)
    assert out.shape == img.shape


def test_custom_commands():
    img = _synth()
    out = apply_instruction_injection(img, commands=["Test command"], seed=42)
    assert out.shape == img.shape


def test_modifies_image():
    img = _synth()
    out = apply_instruction_injection(img, opacity=0.12, seed=42)
    assert not np.array_equal(out, img)
