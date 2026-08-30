"""Visible-layer edit compositing — erase/add without touching invisible core."""

from __future__ import annotations

import numpy as np

from core.visible_edit import apply_visible_edits, parse_add_placements, parse_add_points


def _img(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(40, 200, (128, 128, 3), dtype=np.uint8)


def test_parse_add_points_accepts_arrays_and_objects() -> None:
    pts = parse_add_points('[{"x":0.2,"y":0.3}, [0.9, 0.1]]')
    assert len(pts) == 2
    assert pts[0] == (0.2, 0.3)
    assert pts[1] == (0.9, 0.1)


def test_parse_add_placements_with_layers() -> None:
    items = parse_add_placements(
        '[{"layer":"blur_bar","x":0.1,"y":0.2,"w":0.3,"h":0.1}, {"layer":"emboss","x":0.5,"y":0.5}]'
    )
    assert len(items) == 2
    assert items[0]["layer"] == "blur_bar"
    assert items[0]["w"] == 0.3
    assert items[1]["layer"] == "emboss"


def test_erase_mask_restores_invisible_core_in_region() -> None:
    original = _img(1)
    invisible = original.copy()
    invisible[50:70, 50:70] = 10

    full = original.copy()
    full[:, :, 0] = np.clip(full[:, :, 0].astype(np.int32) + 40, 0, 255).astype(np.uint8)

    mask = np.zeros((128, 128), dtype=np.float32)
    mask[40:88, 40:88] = 1.0

    out = apply_visible_edits(original, full, invisible, erase_mask=mask)
    assert np.array_equal(out[60, 60], invisible[60, 60])
    assert not np.array_equal(out[10, 10], invisible[10, 10])


def test_add_displacement_placement_changes_body_pixels() -> None:
    original = _img(2)
    invisible = original.copy()
    full = original.copy()
    out = apply_visible_edits(
        original,
        full,
        invisible,
        add_placements=[{"layer": "displacement", "x": 0.5, "y": 0.5}],
        displacement={
            "text": "JW",
            "shift": 18,
            "font_ratio": 0.2,
            "seed": 7,
            "shadow": True,
        },
    )
    assert not np.array_equal(out, full)


def test_add_blur_mask_changes_body_pixels() -> None:
    original = _img(3)
    invisible = original.copy()
    full = original.copy()
    mask = np.zeros((128, 128), dtype=np.float32)
    mask[50:80, 20:100] = 1.0
    out = apply_visible_edits(
        original,
        full,
        invisible,
        add_blur_mask=mask,
        blur_opts={"text": "X", "sigma": 14, "seed": 1},
    )
    assert not np.array_equal(out, full)
