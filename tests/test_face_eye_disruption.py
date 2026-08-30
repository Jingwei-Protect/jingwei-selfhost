"""Unit tests for ``core.face_eye_disruption``."""

from __future__ import annotations

import numpy as np
import pytest

from core.face_eye_disruption import apply_face_eye_disruption


def _synth(h: int = 200, w: int = 200, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(40, 220, size=(h, w, 3), dtype=np.uint8)


def test_shape_dtype() -> None:
    img = _synth()
    out = apply_face_eye_disruption(img, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_deterministic() -> None:
    img = _synth(seed=1)
    a = apply_face_eye_disruption(img, seed=42)
    b = apply_face_eye_disruption(img, seed=42)
    assert np.array_equal(a, b)


def test_different_seeds_differ() -> None:
    img = _synth(seed=2)
    a = apply_face_eye_disruption(img, seed=1, allow_fallback=True)
    b = apply_face_eye_disruption(img, seed=2, allow_fallback=True)
    assert not np.array_equal(a, b)


def test_modifies_image() -> None:
    img = _synth(seed=3)
    out = apply_face_eye_disruption(
        img, displacement_px=2.5, iris_hue_shift=10, seed=42, allow_fallback=True,
    )
    assert not np.array_equal(out, img)


def test_change_localised_to_eye_disks() -> None:
    """Changes must concentrate inside the predicted eye disks, not the
    whole face rect.

    The fallback face rect is ``(W/4, H/12, W/2, H/3)``.  With default
    proportions the two eye disks live near
    ``y ≈ ry + 0.38·rh`` and ``x ∈ {rx + 0.30·rw, rx + 0.70·rw}``.
    We assert that the changed-pixel area is much smaller than the
    fallback face rect area (i.e. it is truly *localised*).
    """
    h, w = 256, 256
    # Use a textured image so cv2.remap produces visible pixel diffs
    # (a uniform image is invariant under any displacement field).
    rng = np.random.default_rng(123)
    img = rng.integers(40, 220, size=(h, w, 3), dtype=np.uint8)
    out = apply_face_eye_disruption(
        img, displacement_px=2.5, iris_hue_shift=15, seed=42, allow_fallback=True,
    )
    diff = np.any(out != img, axis=2)
    changed = int(diff.sum())
    face_rect_area = (w // 2) * (h // 3)
    assert 0 < changed < face_rect_area * 0.45, (
        f"Eye disruption should be localised; "
        f"changed={changed}, face_rect_area={face_rect_area}"
    )


def test_low_psnr_floor() -> None:
    """Eye disruption is a tiny localised perturbation; PSNR should stay high."""
    img = _synth(h=256, w=256, seed=7)
    out = apply_face_eye_disruption(
        img, displacement_px=2.5, seed=42, allow_fallback=True,
    )
    mse = float(np.mean((img.astype(float) - out.astype(float)) ** 2))
    if mse > 0:
        psnr = 10.0 * np.log10(255.0 ** 2 / mse)
        assert psnr > 30.0, f"PSNR too low for tiny eye warp: {psnr:.1f} dB"


def test_displacement_clamping() -> None:
    img = _synth(seed=8)
    a = apply_face_eye_disruption(img, displacement_px=100.0, seed=42)
    b = apply_face_eye_disruption(img, displacement_px=5.0, seed=42)
    assert np.array_equal(a, b)


def test_zero_hue_still_warps() -> None:
    img = _synth(seed=9)
    out = apply_face_eye_disruption(
        img, displacement_px=2.5, iris_hue_shift=0, seed=42, allow_fallback=True,
    )
    assert not np.array_equal(out, img)


def test_no_fallback_leaves_illustration_unchanged() -> None:
    """Without a detected face, stealth must not paint fallback eye disks."""
    img = _synth(h=400, w=300, seed=11)
    out = apply_face_eye_disruption(img, seed=42, allow_fallback=False)
    assert np.array_equal(out, img)


def test_invalid_dtype_raises() -> None:
    img = _synth().astype(np.float32)
    with pytest.raises(ValueError):
        apply_face_eye_disruption(img)


def test_too_small_image_raises() -> None:
    img = np.zeros((8, 8, 3), dtype=np.uint8)
    with pytest.raises(ValueError):
        apply_face_eye_disruption(img)
