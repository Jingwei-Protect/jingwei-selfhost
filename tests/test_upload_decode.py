"""Upload decode helpers for protect/inspect routes."""

from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image

from core.upload_decode import open_upload_image


def test_open_valid_jpeg() -> None:
    buf = io.BytesIO()
    Image.fromarray(np.zeros((32, 32, 3), dtype=np.uint8)).save(buf, format="JPEG")
    img = open_upload_image(buf.getvalue())
    assert img.size == (32, 32)


def test_open_rejects_too_short() -> None:
    with pytest.raises(ValueError, match="过短"):
        open_upload_image(b"\xff\xd8")
