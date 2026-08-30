"""evaluation.visualize 單元測試。"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from evaluation.visualize import generate_comparison


def test_generate_comparison_creates_file(tmp_path) -> None:
    img = np.random.default_rng(0).integers(0, 256, (16, 16, 3), dtype=np.uint8)
    p = np.clip(img.astype(np.int16) + 5, 0, 255).astype(np.uint8)
    out = tmp_path / "cmp.png"
    generate_comparison(img, p, str(out))
    assert out.is_file()


def test_generate_comparison_output_is_valid_png(tmp_path) -> None:
    img = np.random.default_rng(1).integers(0, 256, (24, 24, 3), dtype=np.uint8)
    out = tmp_path / "v.png"
    generate_comparison(img, img, str(out))
    with Image.open(out) as im:
        im.load()
        assert im.format == "PNG"


def test_generate_comparison_output_has_3x_width(tmp_path) -> None:
    w, h = 32, 28
    img = np.random.default_rng(2).integers(0, 256, (h, w, 3), dtype=np.uint8)
    out = tmp_path / "wide.png"
    generate_comparison(img, img, str(out))
    with Image.open(out) as im:
        expected_w = 3 * w + 2
        assert abs(im.width - expected_w) <= 2
        assert im.height > h


def test_input_validation(tmp_path) -> None:
    a = np.zeros((16, 16, 3), dtype=np.uint8)
    b = np.zeros((15, 16, 3), dtype=np.uint8)
    with pytest.raises(ValueError):
        generate_comparison(a, b, str(tmp_path / "x.png"))
    with pytest.raises(ValueError, match=".png"):
        generate_comparison(a, a, str(tmp_path / "x.jpg"))


def test_generate_comparison_too_small_for_ssim(tmp_path) -> None:
    img = np.zeros((8, 8, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="11"):
        generate_comparison(img, img, str(tmp_path / "s.png"))


def test_generate_comparison_caps_display_long_edge(tmp_path) -> None:
    """Screen comparison must not keep a 3-panel full-resolution PNG."""
    rng = np.random.default_rng(4)
    img = rng.integers(0, 256, (200, 180, 3), dtype=np.uint8)
    out = tmp_path / "capped.png"
    generate_comparison(img, img, str(out), max_side=90)
    with Image.open(out) as im:
        assert im.width <= 3 * 90 + 4
        assert im.height <= 90 + 48


def test_generate_comparison_default_keeps_full_display(tmp_path) -> None:
    """Eval scripts omit max_side and must keep native panel size."""
    img = np.zeros((20, 1000, 3), dtype=np.uint8)
    out = tmp_path / "full.png"
    generate_comparison(img, img, str(out))
    with Image.open(out) as im:
        assert im.width >= 3 * 1000
