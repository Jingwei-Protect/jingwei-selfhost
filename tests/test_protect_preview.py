"""Protect preview path — visible layers and post-preview edits."""

from __future__ import annotations

import io

import numpy as np
from PIL import Image

from api.routes.protect import _apply_visible_edits_to_frame, _has_visible_edit_payload, _visible_edits_empty
from core.visible_preview import render_visible_preview


def _img(seed: int = 0, size: int = 128) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(40, 200, (size, size, 3), dtype=np.uint8)


def _mask_png(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).save(buf, format="PNG")
    return buf.getvalue()


def _edit_kwargs(**overrides: object) -> dict:
    base = {
        "erase_mask_arr": None,
        "add_placements": [],
        "add_blur_arr": None,
        "displacement_enabled": True,
        "displacement_text": "JW",
        "displacement_shift": 10,
        "displacement_font_ratio": 0.15,
        "displacement_seed": 1,
        "displacement_shadow": True,
        "blur_bar_enabled": True,
        "blur_bar_text": "",
        "blur_bar_sigma": 12,
        "emboss_enabled": True,
        "emboss_pattern": "diagonal",
        "emboss_strength": "medium",
        "emboss_text": "",
        "emboss_text_density": "dense",
        "face_emboss_enabled": True,
        "face_emboss_text": "",
        "face_emboss_shift": 12,
        "face_emboss_opacity": 0.25,
        "face_emboss_seed": 1,
    }
    base.update(overrides)
    return base


def test_visible_edits_empty_with_ndarray_masks() -> None:
    mask = np.zeros((64, 64), dtype=np.float32)
    mask[10:20, 10:20] = 1.0
    assert not _visible_edits_empty(mask, [], None)
    assert _visible_edits_empty(None, [], None)
    assert not _visible_edits_empty(None, [{"layer": "displacement", "x": 0.5, "y": 0.5}], None)
    assert _visible_edits_empty(None, [{"layer": "logo", "x": 0.2, "y": 0.3}], None)
    assert _visible_edits_empty(None, [{"layer": "halftone_signature", "x": 0.2, "y": 0.3}], None)


def test_has_visible_edit_payload_commit_flag() -> None:
    """Save-and-protect must run even when only halftone anchor moved (no add points)."""
    assert _has_visible_edit_payload(
        visible_edits_requested=True,
        erase_mask_arr=None,
        add_blur_arr=None,
        add_placements=[],
    )
    assert not _has_visible_edit_payload(
        visible_edits_requested=False,
        erase_mask_arr=None,
        add_blur_arr=None,
        add_placements=[],
    )
    mask = np.zeros((8, 8), dtype=np.float32)
    mask[2:5, 2:5] = 1.0
    assert _has_visible_edit_payload(
        visible_edits_requested=False,
        erase_mask_arr=mask,
        add_blur_arr=None,
        add_placements=[],
    )


def test_apply_visible_edits_to_frame_erase_mask_no_truth_error() -> None:
    img = _img(1)
    mask = np.zeros(img.shape[:2], dtype=np.float32)
    mask[20:40, 20:40] = 1.0
    out = _apply_visible_edits_to_frame(img, img.copy(), **_edit_kwargs(erase_mask_arr=mask))
    assert out.shape == img.shape


def test_apply_visible_edits_to_frame_no_edits_passthrough() -> None:
    img = _img(2)
    out = _apply_visible_edits_to_frame(img, img.copy(), **_edit_kwargs())
    assert np.array_equal(out, img)


def test_apply_visible_edits_to_frame_add_displacement() -> None:
    img = _img(3)
    out = _apply_visible_edits_to_frame(
        img,
        img.copy(),
        **_edit_kwargs(
            add_placements=[{"layer": "displacement", "x": 0.5, "y": 0.5}],
        ),
    )
    assert not np.array_equal(out, img)


def test_apply_visible_edits_to_frame_add_blur_mask_only() -> None:
    img = _img(4)
    blur = np.zeros(img.shape[:2], dtype=np.float32)
    blur[50:80, 30:90] = 1.0
    out = _apply_visible_edits_to_frame(
        img,
        img.copy(),
        **_edit_kwargs(add_blur_arr=blur),
    )
    assert not np.array_equal(out, img)


def test_apply_visible_edits_to_frame_add_emboss_and_face_emboss() -> None:
    img = _img(5)
    out = _apply_visible_edits_to_frame(
        img,
        img.copy(),
        **_edit_kwargs(
            add_placements=[
                {"layer": "emboss", "x": 0.3, "y": 0.3},
                {"layer": "face_emboss", "x": 0.7, "y": 0.7},
            ],
        ),
    )
    assert not np.array_equal(out, img)


def test_render_visible_preview_baseline() -> None:
    img = _img(6)
    out = render_visible_preview(img)
    assert out.ndim == 3 and out.shape[2] == 3


def test_render_visible_preview_displacement() -> None:
    img = _img(7)
    out = render_visible_preview(
        img,
        displacement_enabled=True,
        displacement_text="Test",
        displacement_seed=11,
    )
    assert not np.array_equal(out, img)


def test_render_visible_preview_blur_bar_and_region_mask() -> None:
    img = _img(8)
    region = np.zeros(img.shape[:2], dtype=np.float32)
    region[40:90, 20:100] = 1.0
    out = render_visible_preview(
        img,
        blur_bar_enabled=True,
        blur_bar_text="Blur",
        blur_region_mask=region,
    )
    assert not np.array_equal(out, img)


def test_render_visible_preview_emboss_face_emboss_signature() -> None:
    img = _img(9)
    out = render_visible_preview(
        img,
        emboss_enabled=True,
        emboss_text="E",
        face_emboss_enabled=True,
        face_emboss_text="F",
        signature_text="Sig",
    )
    assert not np.array_equal(out, img)


def test_preview_pipeline_render_then_erase_edit() -> None:
    img = _img(10)
    base = render_visible_preview(
        img,
        displacement_enabled=True,
        displacement_text="Pipe",
        blur_bar_enabled=True,
        emboss_enabled=True,
    )
    mask = np.zeros(base.shape[:2], dtype=np.float32)
    mask[30:90, 30:90] = 1.0
    edited = _apply_visible_edits_to_frame(
        img,
        base,
        **_edit_kwargs(erase_mask_arr=mask, displacement_enabled=True, displacement_text="Pipe"),
    )
    assert edited.shape == base.shape
    assert not np.array_equal(edited, base)


def test_preview_pipeline_large_image_erase_edit() -> None:
    """Masks from the UI match preview JPEG size, not full upload size."""
    rng = np.random.default_rng(11)
    img = rng.integers(40, 200, (1800, 2400, 3), dtype=np.uint8)
    from core.visible_preview import downscale_for_preview, render_visible_preview

    preview_work, _ = downscale_for_preview(img)
    base = render_visible_preview(
        img,
        displacement_enabled=True,
        displacement_text="Large",
    )
    assert base.shape[:2] == preview_work.shape[:2]

    mask = np.zeros(base.shape[:2], dtype=np.float32)
    mask[40:120, 40:120] = 1.0
    edited = _apply_visible_edits_to_frame(
        preview_work,
        base,
        **_edit_kwargs(erase_mask_arr=mask, displacement_enabled=True, displacement_text="Large"),
    )
    assert edited.shape == base.shape


def test_load_erase_mask_png_roundtrip_for_preview_masks() -> None:
    from core.visible_edit import load_erase_mask_png

    arr = np.zeros((96, 96), dtype=np.float32)
    arr[10:30, 10:30] = 1.0
    png = _mask_png(arr)
    loaded = load_erase_mask_png(png, 96, 96)
    assert loaded.shape == (96, 96)
    assert loaded[20, 20] > 0.9
