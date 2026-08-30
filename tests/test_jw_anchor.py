"""Regression tests for the anchor's geometric robustness and its FP floor.

The anchor is the layer that carries provenance past a crop, since the JW
frequency payload does not survive one. It previously had no test module, and
two defects were found in that blind spot:

  * on textured content the per-corner peak ranking dropped the real anchor
    (it can rank ~300 of ~640 peaks against fur), so crops failed to decode;
  * unmarked images produced checksum-valid records at a measurable rate.

The second matters more than the first. These tests pin both, and deliberately
use textured rather than smooth content, because smooth images pass even with
the ranking bug present.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from core.jw_anchor import (
    _MIN_ANCHOR_CONFIDENCE,
    artist_code,
    embed_anchor_signature,
    read_anchor_tracking,
)

ARTIST = "TestArtist"
CREATED = "2026-07-01"


def _textured(h: int = 512, w: int = 640, seed: int = 3) -> np.ndarray:
    """Busy content: the ranking bug is invisible on smooth images."""
    rng = np.random.default_rng(seed)
    base = rng.integers(60, 200, (h // 8, w // 8, 3), dtype=np.uint8)
    img = cv2.resize(base, (w, h), interpolation=cv2.INTER_LINEAR)
    fine = rng.normal(0, 18, (h, w, 3))
    return np.clip(img.astype(np.float64) + fine, 0, 255).astype(np.uint8)


def _crop(img: np.ndarray, frac: float) -> np.ndarray:
    h, w = img.shape[:2]
    dy, dx = int(h * frac / 2), int(w * frac / 2)
    return np.ascontiguousarray(img[dy : h - dy, dx : w - dx])


def _rotate(img: np.ndarray, deg: float) -> np.ndarray:
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1.0)
    return cv2.warpAffine(
        img, m, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE
    )


@pytest.fixture(scope="module")
def marked() -> np.ndarray:
    return embed_anchor_signature(_textured(), ARTIST, created_at=CREATED)


def test_roundtrip_clean(marked: np.ndarray) -> None:
    rec = read_anchor_tracking(marked, ref=CREATED, known_artist=ARTIST)
    assert rec is not None
    assert rec["artist_code"] == artist_code(ARTIST)
    assert rec["artist_matches"] is True


@pytest.mark.parametrize("frac", [0.05, 0.10])
def test_survives_crop_on_textured_content(marked: np.ndarray, frac: float) -> None:
    """Crop is the common theft edit and the one JW cannot survive."""
    rec = read_anchor_tracking(_crop(marked, frac), ref=CREATED)
    assert rec is not None, f"anchor lost at {frac:.0%} crop"
    assert rec["artist_code"] == artist_code(ARTIST)


@pytest.mark.parametrize("deg", [1.0, 2.0])
def test_survives_small_rotation(marked: np.ndarray, deg: float) -> None:
    rec = read_anchor_tracking(_rotate(marked, deg), ref=CREATED)
    assert rec is not None, f"anchor lost at {deg} degree rotation"
    assert rec["artist_code"] == artist_code(ARTIST)


def test_confidence_clears_the_floor(marked: np.ndarray) -> None:
    """Genuine recoveries must keep headroom over the false-positive floor,
    otherwise the floor is silently costing recall on harder inputs."""
    rec = read_anchor_tracking(_crop(marked, 0.10), ref=CREATED)
    assert rec is not None
    assert rec["confidence"] > _MIN_ANCHOR_CONFIDENCE * 1.2


def test_no_false_positive_on_unmarked_geometry() -> None:
    """Unmarked frames under the same geometry must not decode.

    Each candidate quad is an independent roll against a 24-bit record, so the
    widened crop search multiplies the chances of a spurious checksum pass.
    Falsely attributing an unmarked image is worse than missing a real mark.
    """
    rng = np.random.default_rng(11)
    for i in range(8):
        img = _textured(seed=100 + i)
        att = _rotate(_crop(img, float(rng.uniform(0.0, 0.10))), float(rng.uniform(-2, 2)))
        assert read_anchor_tracking(att) is None, f"fabricated an anchor on unmarked image {i}"
