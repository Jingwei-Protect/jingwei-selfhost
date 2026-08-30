"""Unit tests for ``core.face_emboss_lock``."""

from __future__ import annotations

import numpy as np
import pytest

from core.face_emboss_lock import apply_face_emboss_lock


def _make_image(h: int = 128, w: int = 128, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(30, 220, size=(h, w, 3), dtype=np.uint8)


def test_shape_dtype() -> None:
    img = _make_image()
    out = apply_face_emboss_lock(img, shift_px=12, opacity=0.20, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_deterministic() -> None:
    img = _make_image(seed=1)
    a = apply_face_emboss_lock(img, seed=42)
    b = apply_face_emboss_lock(img, seed=42)
    assert np.array_equal(a, b)


def test_different_seeds() -> None:
    img = _make_image(seed=2)
    a = apply_face_emboss_lock(img, seed=1)
    b = apply_face_emboss_lock(img, seed=2)
    assert not np.array_equal(a, b)


def test_modifies_image() -> None:
    img = _make_image(seed=3)
    out = apply_face_emboss_lock(img, shift_px=12, opacity=0.20, seed=42)
    assert not np.array_equal(out, img)


def test_shift_clamping() -> None:
    img = _make_image(seed=4)
    a = apply_face_emboss_lock(img, shift_px=0, seed=42)
    b = apply_face_emboss_lock(img, shift_px=5, seed=42)
    assert np.array_equal(a, b), "shift_px below 5 should clamp to 5"


def test_opacity_clamping() -> None:
    img = _make_image(seed=5)
    a = apply_face_emboss_lock(img, opacity=0.01, seed=42)
    b = apply_face_emboss_lock(img, opacity=0.10, seed=42)
    assert np.array_equal(a, b), "opacity below 0.10 should clamp to 0.10"


def test_invalid_dtype_raises() -> None:
    img = _make_image().astype(np.float32)
    with pytest.raises(ValueError):
        apply_face_emboss_lock(img)


def test_invalid_shape_raises() -> None:
    img = np.zeros((128, 128), dtype=np.uint8)
    with pytest.raises(ValueError):
        apply_face_emboss_lock(img)


def test_small_image_raises() -> None:
    img = np.zeros((16, 16, 3), dtype=np.uint8)
    with pytest.raises(ValueError):
        apply_face_emboss_lock(img)


def test_rectangular_image() -> None:
    img = _make_image(h=200, w=100, seed=10)
    out = apply_face_emboss_lock(img, seed=42)
    assert out.shape == (200, 100, 3)


def test_no_chromatic_shift() -> None:
    img = _make_image(seed=6)
    out = apply_face_emboss_lock(img, chromatic_shift=0, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_pipeline_integration() -> None:
    """Smoke test via pipeline."""
    from core.pipeline import protect_image
    img = _make_image(h=128, w=128, seed=7)
    out = protect_image(
        img, delivery_mode=True, protection_mode="face_emboss_lock", seed=42,
    )
    assert out.shape == img.shape
    assert out.dtype == np.uint8
    assert not np.array_equal(out, img)


def test_center_roi_skips_face_detection() -> None:
    """Protect-page dashed-box path: center_roi must not call Haar detection."""
    import core.face_emboss_lock as mod

    calls: list[str] = []

    def _boom(_image: np.ndarray, **_kwargs: object) -> list[tuple[int, int, int, int]]:
        calls.append("detect")
        raise AssertionError("face detection must not run for center_roi=True")

    # Patch only if already imported; center_roi path must not import/call it.
    import sys
    import types

    fake = types.ModuleType("core.face_shield")
    fake._detect_faces = _boom  # type: ignore[attr-defined]
    prev = sys.modules.get("core.face_shield")
    sys.modules["core.face_shield"] = fake
    try:
        # Reload emboss module bindings? apply_face_emboss_lock lazy-imports inside else.
        img = _make_image(h=96, w=96, seed=11)
        out = mod.apply_face_emboss_lock(
            img,
            shift_px=12,
            opacity=0.25,
            seed=7,
            emboss_text="JW",
            center_roi=True,
        )
        assert out.shape == img.shape
        assert out.dtype == np.uint8
        assert not np.array_equal(out, img)
        assert calls == []
    finally:
        if prev is None:
            sys.modules.pop("core.face_shield", None)
        else:
            sys.modules["core.face_shield"] = prev


def test_center_roi_works_when_cascadeclassifier_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: broken OpenCV without CascadeClassifier must not break box emboss."""
    import cv2

    monkeypatch.delattr(cv2, "CascadeClassifier", raising=False)
    # Ensure a fresh face_shield would also be safe if imported elsewhere.
    import importlib
    import core.face_shield as fs

    importlib.reload(fs)
    try:
        img = _make_image(h=96, w=96, seed=12)
        out = apply_face_emboss_lock(
            img,
            shift_px=10,
            opacity=0.22,
            seed=3,
            emboss_text="A",
            center_roi=True,
        )
        assert out.shape == img.shape
        assert not np.array_equal(out, img)
    finally:
        importlib.reload(fs)


def test_visible_edit_face_emboss_placement() -> None:
    """Product path: placement box → center_roi face emboss."""
    from core.visible_edit import apply_visible_edits

    img = _make_image(h=160, w=160, seed=13)
    out = apply_visible_edits(
        img,
        img.copy(),
        img.copy(),
        add_placements=[{"layer": "face_emboss", "x": 0.5, "y": 0.4}],
        face_emboss_opts={
            "text": "JW",
            "shift": 12,
            "opacity": 0.25,
            "seed": 42,
            "patch_ratio": 0.28,
        },
    )
    assert out.shape == img.shape
    assert out.dtype == np.uint8
    assert not np.array_equal(out, img)
