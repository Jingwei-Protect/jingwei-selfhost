"""Unit tests for ``core.face_blob_disruption``."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from core.face_blob_disruption import apply_face_blob_disruption


def _synth(h: int = 200, w: int = 200, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(40, 220, size=(h, w, 3), dtype=np.uint8)


def test_shape_dtype() -> None:
    img = _synth()
    out = apply_face_blob_disruption(img, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_deterministic() -> None:
    img = _synth(seed=1)
    a = apply_face_blob_disruption(img, seed=42)
    b = apply_face_blob_disruption(img, seed=42)
    assert np.array_equal(a, b)


def test_different_seeds_differ() -> None:
    img = _synth(seed=2)
    a = apply_face_blob_disruption(img, seed=1)
    b = apply_face_blob_disruption(img, seed=2)
    assert not np.array_equal(a, b)


def test_modifies_image() -> None:
    img = _synth(seed=3)
    out = apply_face_blob_disruption(
        img, n_blobs=3, saturation_boost=1.6, seed=42
    )
    assert not np.array_equal(out, img)


def test_saturation_actually_boosts() -> None:
    """Inside the face ROI, blob pixels should have higher S (HSV) than baseline."""
    h, w = 256, 256
    img = np.full((h, w, 3), 160, dtype=np.uint8)
    img[:, :, 0] = 200
    img[:, :, 2] = 120
    out = apply_face_blob_disruption(
        img,
        n_blobs=3,
        blob_size_ratio=0.35,
        saturation_boost=1.8,
        seed=42,
    )
    hsv_in = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    hsv_out = cv2.cvtColor(out, cv2.COLOR_RGB2HSV)
    # Face fallback ROI lives in the upper-central region; sample it.
    upper_in = hsv_in[: h // 3, w // 4 : 3 * w // 4, 1].mean()
    upper_out = hsv_out[: h // 3, w // 4 : 3 * w // 4, 1].mean()
    assert upper_out > upper_in + 5, (
        f"Saturation should rise inside face ROI; "
        f"in={upper_in:.1f}, out={upper_out:.1f}"
    )


def test_affects_upper_face_region_on_portrait() -> None:
    """On a tall portrait, modification must concentrate in the upper half
    (where the face fallback ROI lives)."""
    h, w = 600, 300
    # Use a chromatic image so the hue+saturation shift produces visible
    # pixel diffs (a pure-grey image has S=0 and is invariant to hue rotation).
    rng = np.random.default_rng(123)
    img = rng.integers(60, 200, size=(h, w, 3), dtype=np.uint8)
    out = apply_face_blob_disruption(img, n_blobs=3, seed=42)
    diff = np.any(out != img, axis=2)
    upper = int(diff[: h // 2].sum())
    lower = int(diff[h // 2 :].sum())
    assert upper > lower * 3, (
        f"Blob disruption should target upper-half face region, "
        f"upper={upper}, lower={lower}"
    )


def test_irregular_shape_not_rectangular() -> None:
    """The modified mask should NOT match a single axis-aligned rectangle.

    Sanity check: if the bounding box of changes is much larger than the
    actual changed-pixel area, the change is genuinely irregular.
    """
    rng = np.random.default_rng(321)
    img = rng.integers(60, 200, size=(256, 256, 3), dtype=np.uint8)
    out = apply_face_blob_disruption(img, n_blobs=3, seed=42)
    diff = np.any(out != img, axis=2)
    ys, xs = np.where(diff)
    if len(ys) == 0:
        pytest.skip("No changes produced — cannot evaluate shape")
    bbox_area = (ys.max() - ys.min() + 1) * (xs.max() - xs.min() + 1)
    filled = float(len(ys))
    fill_ratio = filled / max(bbox_area, 1)
    assert fill_ratio < 0.85, (
        f"Changed region should not fill its bbox like a rectangle "
        f"(fill_ratio={fill_ratio:.2f})"
    )


def test_parameter_clamping() -> None:
    img = _synth(seed=4)
    out_low = apply_face_blob_disruption(
        img,
        n_blobs=0,
        blob_size_ratio=0.0,
        hue_shift_range=(0, 0),
        saturation_boost=0.0,
        edge_roughness=1,
        feather_px=-1,
        seed=42,
    )
    out_high = apply_face_blob_disruption(
        img,
        n_blobs=100,
        blob_size_ratio=10.0,
        hue_shift_range=(999, 999),
        saturation_boost=100.0,
        edge_roughness=999,
        feather_px=999,
        seed=42,
    )
    assert out_low.shape == img.shape
    assert out_high.shape == img.shape


def test_invalid_dtype_raises() -> None:
    img = _synth().astype(np.float32)
    with pytest.raises(ValueError):
        apply_face_blob_disruption(img)


def test_too_small_image_raises() -> None:
    img = np.zeros((8, 8, 3), dtype=np.uint8)
    with pytest.raises(ValueError):
        apply_face_blob_disruption(img)
