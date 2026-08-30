"""tests/test_face_shield.py — face shield module unit tests."""

from __future__ import annotations

import importlib

import numpy as np
import pytest

from core.face_shield import apply_face_shield


def _synth(h: int = 128, w: int = 128) -> np.ndarray:
    return np.random.default_rng(0).integers(0, 256, (h, w, 3), dtype=np.uint8)


def test_shape_dtype():
    img = _synth()
    out = apply_face_shield(img, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_deterministic():
    img = _synth()
    a = apply_face_shield(img, seed=42)
    b = apply_face_shield(img, seed=42)
    assert np.array_equal(a, b)


def test_no_face_fallback():
    """Plain gradient image has no face; fallback upper-central box should fire."""
    h, w = 128, 128
    img = np.zeros((h, w, 3), dtype=np.uint8)
    for x in range(w):
        img[:, x] = int(255 * x / max(w - 1, 1))
    out = apply_face_shield(img, seed=42)
    assert not np.array_equal(out, img)


def test_fallback_targets_upper_half_on_portrait():
    """For a tall portrait, fallback must apply to the upper region (face area),
    not the centre (chest/belt area)."""
    h, w = 600, 300
    img = np.full((h, w, 3), 128, dtype=np.uint8)
    out = apply_face_shield(img, seed=42)
    diff = np.any(out != img, axis=2)
    upper_diff = int(diff[: h // 2].sum())
    lower_diff = int(diff[h // 2 :].sum())
    assert upper_diff > lower_diff * 2, (
        f"Fallback should affect upper half (face zone), "
        f"got upper={upper_diff}, lower={lower_diff}"
    )


def test_custom_text():
    img = _synth()
    out = apply_face_shield(img, overlay_text="TEST", seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_opacity_params():
    img = _synth()
    out = apply_face_shield(img, grid_opacity=0.1, text_opacity=0.5, seed=42)
    assert out.shape == img.shape


def test_fake_rects_modify_image():
    img = _synth(256, 256)
    out = apply_face_shield(img, seed=42)
    assert not np.array_equal(out, img)


def test_import_survives_missing_cascadeclassifier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing face_shield must not crash when cv2 lacks CascadeClassifier."""
    import cv2
    import core.face_shield as fs

    monkeypatch.delattr(cv2, "CascadeClassifier", raising=False)
    reloaded = importlib.reload(fs)
    try:
        assert reloaded._ensure_cascades() is False
        img = _synth()
        # Fallback ROI still applies disruption when cascades unavailable.
        out = reloaded.apply_face_shield(img, seed=1)
        assert out.shape == img.shape
        assert out.dtype == np.uint8
        assert not np.array_equal(out, img)
    finally:
        importlib.reload(fs)
