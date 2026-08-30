"""Courtesy logo overlay — shape and tint, not removal resistance."""

from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image

from core.logo_watermark import apply_logo_watermark, decode_logo_bytes


def _solid_host(h: int = 120, w: int = 160, value: int = 80) -> np.ndarray:
    return np.full((h, w, 3), value, dtype=np.uint8)


def _block_logo(h: int = 32, w: int = 48, rgb: tuple[int, int, int] = (255, 0, 0)) -> np.ndarray:
    logo = np.zeros((h, w, 4), dtype=np.uint8)
    logo[4:-4, 4:-4, :3] = rgb
    logo[4:-4, 4:-4, 3] = 255
    return logo


def test_decode_png_keeps_alpha() -> None:
    img = Image.fromarray(_block_logo())
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    arr = decode_logo_bytes(buf.getvalue())
    assert arr.shape[2] == 4
    assert arr.dtype == np.uint8
    assert int(arr[:, :, 3].max()) == 255


def test_empty_bytes_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        decode_logo_bytes(b"")


def test_gray_tint_equalizes_channels() -> None:
    host = _solid_host()
    logo = _block_logo(rgb=(200, 40, 40))
    out = apply_logo_watermark(
        host, logo, opacity=1.0, scale=0.30, tint="gray", position="center"
    )
    # The pasted region must no longer be a saturated red stamp.
    assert int(out.max()) < 200
    cy, cx = host.shape[0] // 2, host.shape[1] // 2
    pixel = out[cy, cx].astype(int)
    assert abs(int(pixel[0]) - int(pixel[1])) <= 2
    assert abs(int(pixel[1]) - int(pixel[2])) <= 2


def test_white_tint_brightens_the_mark() -> None:
    host = _solid_host(value=40)
    logo = _block_logo(rgb=(10, 80, 200))
    out = apply_logo_watermark(
        host, logo, opacity=1.0, scale=0.30, tint="white", position="center"
    )
    cy, cx = host.shape[0] // 2, host.shape[1] // 2
    pixel = out[cy, cx]
    assert int(pixel.min()) >= 200


def test_bottom_right_does_not_touch_top_left() -> None:
    host = _solid_host()
    logo = _block_logo()
    out = apply_logo_watermark(
        host, logo, opacity=1.0, scale=0.25, position="bottom_right", tint="white"
    )
    assert np.array_equal(out[2, 2], host[2, 2])
    assert not np.array_equal(out[-16, -20], host[-16, -20])


def test_disabled_looking_opacity_still_changes_pixels() -> None:
    host = _solid_host()
    logo = _block_logo()
    out = apply_logo_watermark(host, logo, opacity=0.2, scale=0.25, tint="white")
    assert out.shape == host.shape
    assert not np.array_equal(out, host)
