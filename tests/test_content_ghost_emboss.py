"""Unit tests for ``core.content_ghost_emboss``."""

from __future__ import annotations

import numpy as np
import pytest

from core.content_ghost_emboss import apply_content_ghost_emboss


def _make_image(h: int = 128, w: int = 128, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(30, 220, size=(h, w, 3), dtype=np.uint8)


def test_shape_dtype() -> None:
    img = _make_image()
    out = apply_content_ghost_emboss(img, opacity=0.05, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_deterministic() -> None:
    img = _make_image(seed=1)
    a = apply_content_ghost_emboss(img, opacity=0.05, seed=42)
    b = apply_content_ghost_emboss(img, opacity=0.05, seed=42)
    assert np.array_equal(a, b)


def test_different_seeds() -> None:
    img = _make_image(seed=2)
    a = apply_content_ghost_emboss(img, seed=1)
    b = apply_content_ghost_emboss(img, seed=2)
    assert not np.array_equal(a, b)


def test_modifies_image() -> None:
    img = _make_image(seed=3)
    out = apply_content_ghost_emboss(img, opacity=0.06, seed=42)
    assert not np.array_equal(out, img)


def test_high_psnr() -> None:
    """Ghost emboss at default opacity should be nearly invisible — PSNR > 35 dB."""
    img = _make_image(h=256, w=256, seed=5)
    out = apply_content_ghost_emboss(img, opacity=0.05, seed=42)
    mse = float(np.mean((img.astype(float) - out.astype(float)) ** 2))
    if mse > 0:
        psnr = 10.0 * np.log10(255.0 ** 2 / mse)
        assert psnr > 35.0, f"PSNR too low: {psnr:.1f} dB"


def test_opacity_clamping() -> None:
    img = _make_image(seed=6)
    a = apply_content_ghost_emboss(img, opacity=0.0, seed=42)
    b = apply_content_ghost_emboss(img, opacity=0.03, seed=42)
    assert np.array_equal(a, b), "opacity below 0.03 should clamp to 0.03"

    c = apply_content_ghost_emboss(img, opacity=1.0, seed=42)
    d = apply_content_ghost_emboss(img, opacity=0.08, seed=42)
    assert np.array_equal(c, d), "opacity above 0.08 should clamp to 0.08"


def test_chromatic_shift_zero() -> None:
    img = _make_image(seed=7)
    out = apply_content_ghost_emboss(img, chromatic_shift=0, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_invalid_dtype_raises() -> None:
    img = _make_image().astype(np.float32)
    with pytest.raises(ValueError):
        apply_content_ghost_emboss(img)


def test_invalid_shape_raises() -> None:
    img = np.zeros((128, 128), dtype=np.uint8)
    with pytest.raises(ValueError):
        apply_content_ghost_emboss(img)


def test_small_image_raises() -> None:
    img = np.zeros((16, 16, 3), dtype=np.uint8)
    with pytest.raises(ValueError):
        apply_content_ghost_emboss(img)


def test_rectangular_image() -> None:
    img = _make_image(h=200, w=100, seed=10)
    out = apply_content_ghost_emboss(img, opacity=0.05, seed=42)
    assert out.shape == (200, 100, 3)
    assert out.dtype == np.uint8


def test_effect_localized_to_face_region() -> None:
    """Ghost emboss must not brighten a large centered block (full-frame bug)."""
    from core.content_ghost_emboss import _largest_face_rect
    from core.face_shield import _detect_faces

    img = _make_image(h=256, w=256, seed=11)
    faces = _detect_faces(img)
    assert faces, "expected heuristic face region"
    fx, fy, fw, fh, _ = _largest_face_rect(img, faces)
    out = apply_content_ghost_emboss(img, opacity=0.08, seed=42)
    diff = np.abs(out.astype(np.int16) - img.astype(np.int16)).sum(axis=2)
    corner_mean = float(diff[:32, :32].mean())
    face_mean = float(diff[fy:fy + fh, fx:fx + fw].mean())
    outer_mean = float(np.concatenate([
        diff[: fy, :].ravel(),
        diff[fy + fh:, :].ravel(),
        diff[fy:fy + fh, :fx].ravel(),
        diff[fy:fy + fh, fx + fw:].ravel(),
    ]).mean()) if fy + fh <= diff.shape[0] else corner_mean
    assert face_mean >= corner_mean * 0.5
    assert outer_mean <= face_mean * 1.25 + 1.0
