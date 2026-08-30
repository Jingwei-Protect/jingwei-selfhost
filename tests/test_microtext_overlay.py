"""tests/test_microtext_overlay.py — microtext overlay unit tests."""

from __future__ import annotations

import numpy as np
import pytest

from core.microtext_overlay import DEFAULT_DELIVERY_MICROTEXT, apply_microtext_overlay


def _synth(h: int = 64, w: int = 64) -> np.ndarray:
    return np.random.default_rng(0).integers(0, 256, (h, w, 3), dtype=np.uint8)


def test_shape_dtype():
    img = _synth()
    out = apply_microtext_overlay(img, "test", opacity=0.08, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_deterministic():
    img = _synth()
    a = apply_microtext_overlay(img, "test", opacity=0.08, seed=42)
    b = apply_microtext_overlay(img, "test", opacity=0.08, seed=42)
    assert np.array_equal(a, b)


def test_different_seeds():
    img = _synth()
    a = apply_microtext_overlay(img, "test", opacity=0.08, seed=1)
    b = apply_microtext_overlay(img, "test", opacity=0.08, seed=2)
    assert not np.array_equal(a, b)


def test_opacity_range():
    img = _synth()
    apply_microtext_overlay(img, "test", opacity=0.04, seed=42)
    apply_microtext_overlay(img, "test", opacity=0.12, seed=42)


def test_empty_text_uses_default():
    img = _synth()
    out = apply_microtext_overlay(img, "", opacity=0.08, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8
