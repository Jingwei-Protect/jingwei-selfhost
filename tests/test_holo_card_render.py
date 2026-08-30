"""ProvenPix-style foil card frames — rest is the photo, motion is one streak."""

from __future__ import annotations

import numpy as np

from core.holo_card_render import _rim_plate, compose_holo_card, generate_holo_card_frames


def test_rim_plate_is_silver() -> None:
    face = np.full((20, 30, 3), 200, dtype=np.uint8)
    plate = _rim_plate(face, 4)
    corner = plate[0, 0].astype(np.float32)
    assert float(corner.mean()) > 90


def test_rest_pose_keeps_the_photo() -> None:
    rng = np.random.default_rng(0)
    img = rng.integers(0, 256, (48, 64, 3), dtype=np.uint8)
    out = compose_holo_card(img, x=0.2, y=0.8, on=0.0)
    assert np.array_equal(out, img)


def test_pointer_on_adds_foil() -> None:
    rng = np.random.default_rng(1)
    img = rng.integers(40, 200, (48, 64, 3), dtype=np.uint8)
    out = compose_holo_card(img, x=0.7, y=0.3, on=1.0)
    assert out.shape == img.shape
    assert out.dtype == np.uint8
    assert not np.array_equal(out, img)


def test_scene_is_a_card_on_a_desk() -> None:
    rng = np.random.default_rng(2)
    img = rng.integers(0, 256, (48, 64, 3), dtype=np.uint8)
    frames = generate_holo_card_frames(img, n_frames=10)
    assert len(frames) == 10
    first = frames[0]
    assert first.shape[0] > img.shape[0]
    assert first.shape[1] > img.shape[1]
    # Light desk shows in the corners — not a full-bleed photo.
    corner = first[:4, :4].astype(np.float32).mean()
    assert corner > 170
    assert not np.array_equal(frames[0], frames[4])
    mid = frames[5]
    assert np.mean(np.abs(mid.astype(np.int16) - first.astype(np.int16))) > 1.0
