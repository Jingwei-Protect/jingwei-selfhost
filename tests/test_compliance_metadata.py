"""M10 合規元數據模組單元測試。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PIL import Image

from core.compliance_metadata import (
    DEFAULT_COPYRIGHT,
    RIGHTS_USAGE_TERMS,
    _pixel_sha256,
    embed_compliance_metadata,
    read_compliance_metadata,
)


def _new_rgb_image(path, ext: str = ".jpg") -> None:
    im = Image.new("RGB", (64, 64), (120, 55, 200))
    if ext.lower() in (".jpg", ".jpeg"):
        im.save(path, format="JPEG", quality=92)
    else:
        im.save(path, format="PNG")


def test_jpeg_exif_and_iptc_roundtrip(tmp_path) -> None:
    """JPEG 寫入後可自 EXIF 與 IPTC 讀回版權與創作者。"""
    p = tmp_path / "a.jpg"
    _new_rgb_image(p, ".jpg")
    embed_compliance_metadata(p, artist="Alice", copyright_text="自定义版权")
    meta = read_compliance_metadata(p)
    assert meta["exif"] is not None
    assert meta["exif"]["artist"] == "Alice"
    assert meta["exif"]["copyright"] == "自定义版权"
    assert meta["iptc"] is not None
    assert meta["iptc"]["copyright_notice"] == "自定义版权"
    assert meta["iptc"]["by_line"] == "Alice"
    assert meta["iptc"]["special_instructions"] == RIGHTS_USAGE_TERMS


def test_png_text_chunks_roundtrip(tmp_path) -> None:
    """PNG 僅使用 tEXt 語意，讀回與 EXIF／IPTC 對齊之摘要。"""
    p = tmp_path / "b.PNG"
    _new_rgb_image(p, ".png")
    embed_compliance_metadata(p, artist="Bob", copyright_text="CC")
    meta = read_compliance_metadata(p)
    assert meta["exif"] == {"artist": "Bob", "copyright": "CC"}
    assert meta["iptc"]["copyright_notice"] == "CC"
    assert meta["iptc"]["by_line"] == "Bob"


@pytest.mark.parametrize("ext", [".jpg", ".jpeg", ".png"])
def test_embed_does_not_change_rgb_sha256(tmp_path, ext: str) -> None:
    """嵌入元數據後 RGB 像素 SHA-256 不變。"""
    p = tmp_path / f"p{ext}"
    _new_rgb_image(p, ext)
    before = _pixel_sha256(p)
    embed_compliance_metadata(p, artist="Test", copyright_text="X")
    assert _pixel_sha256(p) == before


def test_default_copyright_string(tmp_path) -> None:
    """預設版權字串與 PRD 約定一致。"""
    p = tmp_path / "d.jpg"
    _new_rgb_image(p)
    embed_compliance_metadata(p, artist="陳創作者")
    exif = read_compliance_metadata(p)["exif"]
    assert exif is not None
    assert exif["copyright"] == DEFAULT_COPYRIGHT
    assert "No AI Training" in DEFAULT_COPYRIGHT


def test_unsupported_extension_raises(tmp_path) -> None:
    """不支援之副檔名應 ValueError。"""
    bad = tmp_path / "x.webp"
    bad.write_bytes(b"x")
    with pytest.raises(ValueError, match="不支援"):
        embed_compliance_metadata(bad)
    with pytest.raises(ValueError, match="不支援"):
        read_compliance_metadata(bad)


def test_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        embed_compliance_metadata("/nonexistent/dir/none.jpg")
    with pytest.raises(FileNotFoundError):
        read_compliance_metadata("/nonexistent/dir/none.jpg")


def test_read_c2pa_none_when_flag_off(monkeypatch, tmp_path) -> None:
    """未啟用 C2PA 套件時，讀取結果 ``c2pa`` 為 ``None``。"""
    import core.compliance_metadata as cm

    p = tmp_path / "c.jpg"
    _new_rgb_image(p)
    monkeypatch.setattr(cm, "C2PA_AVAILABLE", False)
    meta = read_compliance_metadata(p)
    assert meta["c2pa"] is None


def test_read_c2pa_empty_when_no_manifest(monkeypatch, tmp_path) -> None:
    """已安裝但檔案無 manifest 時回傳空 dict。"""
    import core.compliance_metadata as cm

    fake = MagicMock()
    fake.Reader = MagicMock()
    fake.Reader.try_create = MagicMock(return_value=None)
    p = tmp_path / "e.jpg"
    _new_rgb_image(p)
    monkeypatch.setattr(cm, "C2PA_AVAILABLE", True)
    monkeypatch.setattr(cm, "c2pa", fake)
    assert read_compliance_metadata(p)["c2pa"] == {}


def test_read_c2pa_json_from_mock_reader(monkeypatch, tmp_path) -> None:
    """C2PA Reader 回傳 JSON 字串時解析為 dict。"""

    class FakeReader:
        def __enter__(self) -> FakeReader:
            return self

        def __exit__(self, *args: object) -> bool:
            return False

        def json(self) -> str:
            return '{"source": "mock"}'

    import core.compliance_metadata as cm

    fake = MagicMock()
    fake.Reader = MagicMock()
    fake.Reader.try_create = MagicMock(return_value=FakeReader())

    p = tmp_path / "f.jpg"
    _new_rgb_image(p)
    monkeypatch.setattr(cm, "C2PA_AVAILABLE", True)
    monkeypatch.setattr(cm, "c2pa", fake)
    assert read_compliance_metadata(p)["c2pa"] == {"source": "mock"}
