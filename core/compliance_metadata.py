"""M10：合規元數據（EXIF / IPTC / 可選 C2PA）嵌入與讀取。

以傳統側車／Chunk 方式寫入版權與創作者資訊，不改變 RGB 像素。JPEG 依序嘗試
EXIF（piexif）與 IPTC（iptcinfo3），每步寫入前備份、寫入後以 RGB 像素 SHA-256
與基準比對；像素變動則還原並略過該後端。兩者皆失敗時拋出 ``RuntimeError``。

PNG 僅使用 Pillow ``PngInfo`` 之 tEXt／zTXt，不使用 piexif、不呼叫 iptcinfo3。

C2PA 簽署需金鑰與 ``Signer``，本模組嵌入時僅在已安裝套件且具備簽署能力時嘗試；
預設環境會略過並以 ``warnings.warn`` 說明。讀取時若已安裝 ``c2pa-python``，
以 ``Reader.try_create`` 解析 manifest：無套件為 ``None``、無憑證為 ``{}``、
有則為解析後之 ``dict``。
"""

from __future__ import annotations

import datetime
import hashlib
import json
import shutil
import tempfile
import warnings
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Callable, Optional

from PIL import Image, PngImagePlugin

import piexif
from iptcinfo3 import IPTCInfo

try:
    import c2pa  # type: ignore

    C2PA_AVAILABLE = True
except ImportError:  # pragma: no cover
    c2pa = None  # type: ignore
    C2PA_AVAILABLE = False

DEFAULT_COPYRIGHT = "All Rights Reserved. No AI Training/Editing."
RIGHTS_USAGE_TERMS = "No AI Training/Editing permitted."

_ALLOWED_SUFFIX = frozenset({".jpg", ".jpeg", ".png"})


def _pixel_sha256(image_path: Path) -> str:
    """將影像轉為 RGB 後對像素位元組計算 SHA-256。"""
    with Image.open(image_path) as im:
        im.load()
        raw = im.convert("RGB").tobytes()
    return hashlib.sha256(raw).hexdigest()


def _try_backend(
    path: Path,
    baseline_hash: str,
    embed_fn: Callable[[], None],
    backend_name: str,
) -> bool:
    """備份、嵌入、驗證像素；失敗或像素變更則還原並回傳 False。"""
    import os

    fd, tmp_name = tempfile.mkstemp(
        suffix=path.suffix, dir=path.parent, prefix=".compliance_"
    )
    os.close(fd)
    shutil.copy2(path, tmp_name)
    try:
        try:
            embed_fn()
        except Exception as exc:  # noqa: BLE001
            shutil.copy2(tmp_name, path)
            warnings.warn(
                f"合規後端 {backend_name} 寫入失敗：{exc}",
                UserWarning,
                stacklevel=3,
            )
            return False
        if _pixel_sha256(path) != baseline_hash:
            shutil.copy2(tmp_name, path)
            warnings.warn(
                f"合規後端 {backend_name} 改變了像素資料，已還原並略過。",
                UserWarning,
                stacklevel=3,
            )
            return False
        return True
    finally:
        Path(tmp_name).unlink(missing_ok=True)


def _exif_bytes_to_str(val: Any) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return str(val)


def _format_exif_datetime(when: int | float) -> str:
    """EXIF DateTime string ``YYYY:MM:DD HH:MM:SS``."""
    return datetime.datetime.fromtimestamp(float(when)).strftime("%Y:%m:%d %H:%M:%S")


def _write_exif_jpeg(
    path: Path,
    artist: Optional[str],
    copyright_text: str,
    protected_at: int | float | None = None,
) -> None:
    exif_dict = piexif.load(str(path))
    zeroth = exif_dict.get("0th")
    if zeroth is None:
        zeroth = {}
    else:
        zeroth = dict(zeroth)
    exif_ifd = exif_dict.get("Exif")
    if exif_ifd is None:
        exif_ifd = {}
    else:
        exif_ifd = dict(exif_ifd)
    exif_dict.pop("1st", None)
    exif_dict.pop("thumbnail", None)
    if artist:
        zeroth[piexif.ImageIFD.Artist] = artist.encode("utf-8")
    zeroth[piexif.ImageIFD.Copyright] = copyright_text.encode("utf-8")
    if protected_at is not None:
        dt = _format_exif_datetime(protected_at).encode("ascii")
        zeroth[piexif.ImageIFD.DateTime] = dt
        exif_ifd[piexif.ExifIFD.DateTimeOriginal] = dt
        exif_ifd[piexif.ExifIFD.DateTimeDigitized] = dt
    exif_dict["0th"] = zeroth
    if protected_at is not None:
        exif_dict["Exif"] = exif_ifd
    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, str(path))


def _write_iptc_jpeg(
    path: Path,
    artist: Optional[str],
    copyright_text: str,
) -> None:
    info = IPTCInfo(
        str(path),
        force=True,
        inp_charset="utf_8",
        out_charset="utf_8",
    )
    info["copyright notice"] = copyright_text
    info["special instructions"] = RIGHTS_USAGE_TERMS
    if artist:
        info["by-line"] = artist
    info.save()


def _embed_c2pa_if_available(path: Path, baseline_hash: str) -> bool:
    """C2PA 須金鑰簽署；此處不實作自動簽章，僅提示後略過。"""
    if not C2PA_AVAILABLE:
        return False
    warnings.warn(
        "C2PA 簽署需要 Manifest 與金鑰（Signer）；"
        "本工具不於此自動簽章，請使用 contentauth/c2pa-python 範例或外部工具。",
        UserWarning,
        stacklevel=2,
    )
    _ = path, baseline_hash
    return False


def _embed_jpeg(
    path: Path,
    artist: Optional[str],
    copyright_text: str,
    protected_at: int | float | None = None,
) -> None:
    baseline = _pixel_sha256(path)
    successes = 0
    if _try_backend(
        path,
        baseline,
        lambda: _write_exif_jpeg(path, artist, copyright_text, protected_at),
        "EXIF(piexif)",
    ):
        successes += 1
    if _try_backend(
        path,
        baseline,
        lambda: _write_iptc_jpeg(path, artist, copyright_text),
        "IPTC(iptcinfo3)",
    ):
        successes += 1
    if _embed_c2pa_if_available(path, baseline):
        successes += 1
    if successes == 0:
        raise RuntimeError(
            "JPEG 合規元數據：EXIF 與 IPTC 均失敗，未寫入任何欄位。"
        )


def _embed_png(
    path: Path,
    artist: Optional[str],
    copyright_text: str,
    protected_at: int | float | None = None,
) -> None:
    baseline = _pixel_sha256(path)
    import os

    fd, tmp_name = tempfile.mkstemp(
        suffix=path.suffix, dir=path.parent, prefix=".compliance_"
    )
    os.close(fd)
    shutil.copy2(path, tmp_name)
    try:
        with Image.open(path) as im:
            im.load()
            icc = im.info.get("icc_profile")
            pnginfo = PngImagePlugin.PngInfo()
            if artist:
                pnginfo.add_text("Artist", artist)
            pnginfo.add_text("Copyright", copyright_text)
            pnginfo.add_text("SpecialInstructions", RIGHTS_USAGE_TERMS)
            pnginfo.add_text("IPTC:CopyrightNotice", copyright_text)
            if artist:
                pnginfo.add_text("IPTC:By-line", artist)
            pnginfo.add_text("IPTC:SpecialInstructions", RIGHTS_USAGE_TERMS)
            if protected_at is not None:
                pnginfo.add_text(
                    "DateTime",
                    datetime.datetime.fromtimestamp(float(protected_at)).strftime("%Y-%m-%d %H:%M:%S"),
                )
            save_kw: dict = {"format": "PNG", "pnginfo": pnginfo, "optimize": False}
            if icc:
                save_kw["icc_profile"] = icc
            im.save(path, **save_kw)
        if _pixel_sha256(path) != baseline:
            shutil.copy2(tmp_name, path)
            raise RuntimeError("PNG 元數據寫入後像素校驗失敗，已還原。")
    finally:
        Path(tmp_name).unlink(missing_ok=True)


def embed_compliance_metadata(
    path: str | Path,
    *,
    artist: Optional[str] = None,
    copyright_text: str = DEFAULT_COPYRIGHT,
    protected_at: int | float | None = None,
) -> None:
    """將合規元數據寫入影像檔。

    Parameters
    ----------
    path:
        僅支援 ``.jpg`` / ``.jpeg`` / ``.png``（不分大小寫）。
    artist:
        創作者／IPTC by-line；``None`` 則不寫入創作者欄位。
    copyright_text:
        版權字串，預設為禁止 AI 訓練／編輯之聲明。

    Raises
    ------
    FileNotFoundError
        檔案不存在。
    ValueError
        副檔名不支援。
    RuntimeError
        JPEG 且 EXIF 與 IPTC 皆未成功寫入。
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"找不到檔案：{p}")
    suf = p.suffix.lower()
    if suf not in _ALLOWED_SUFFIX:
        raise ValueError(
            f"不支援的副檔名 {p.suffix!r}，僅支援 .jpg、.jpeg、.png。"
        )
    if suf in (".jpg", ".jpeg"):
        _embed_jpeg(p, artist, copyright_text, protected_at)
    else:
        _embed_png(p, artist, copyright_text, protected_at)


def read_compliance_metadata(path: str | Path) -> dict[str, Any]:
    """讀取 EXIF、IPTC、C2PA 彙整結果。

    ``c2pa``：未安裝為 ``None``；已安裝但無 manifest／解析失敗為 ``{}``；
    有內嵌憑證則為字典（通常由 ``Reader.json()`` 解析而來）。
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"找不到檔案：{p}")
    suf = p.suffix.lower()
    if suf not in _ALLOWED_SUFFIX:
        raise ValueError(
            f"不支援的副檔名 {p.suffix!r}，僅支援 .jpg、.jpeg、.png。"
        )

    out: dict[str, Any] = {"exif": None, "iptc": None, "c2pa": None}

    if suf in (".jpg", ".jpeg"):
        out["exif"] = _read_exif_jpeg(p)
        out["iptc"] = _read_iptc_jpeg(p)
    else:
        tex = _read_png_text_chunks(p)
        out["exif"] = tex["exif_summary"]
        out["iptc"] = tex["iptc_summary"]

    if not C2PA_AVAILABLE:
        out["c2pa"] = None
    else:
        out["c2pa"] = _read_c2pa_payload(p, suf)

    return out


def _read_exif_jpeg(path: Path) -> Optional[dict[str, Optional[str]]]:
    try:
        raw = piexif.load(str(path))
    except Exception:  # noqa: BLE001
        return None
    zeroth = raw.get("0th")
    if not zeroth:
        return None
    artist = _exif_bytes_to_str(zeroth.get(piexif.ImageIFD.Artist))
    cr = _exif_bytes_to_str(zeroth.get(piexif.ImageIFD.Copyright))
    dt = _exif_bytes_to_str(zeroth.get(piexif.ImageIFD.DateTime))
    exif_ifd = raw.get("Exif") or {}
    if not dt:
        dt = _exif_bytes_to_str(exif_ifd.get(piexif.ExifIFD.DateTimeOriginal))
    if not any([artist, cr, dt]):
        return None
    out: dict[str, Optional[str]] = {"artist": artist, "copyright": cr}
    if dt:
        out["datetime"] = dt
    return out


def _read_iptc_jpeg(path: Path) -> Optional[dict[str, Optional[str]]]:
    try:
        info = IPTCInfo(str(path), force=True)
    except Exception:  # noqa: BLE001
        return None

    def _get(key: str) -> Optional[str]:
        val = info[key]
        if val is None:
            return None
        if isinstance(val, bytes):
            return val.decode("utf-8", errors="replace")
        return str(val)

    cr = _get("copyright notice")
    by = _get("by-line")
    sp = _get("special instructions")
    if cr is None and by is None and sp is None:
        return None
    return {
        "copyright_notice": cr,
        "by_line": by,
        "special_instructions": sp,
    }


def _as_opt_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    return v if isinstance(v, str) else str(v)


def _read_png_text_chunks(path: Path) -> dict[str, Any]:
    with Image.open(path) as im:
        im.load()
        info = dict(im.info)

    artist_s = _as_opt_str(info.get("Artist"))
    copyright_s = _as_opt_str(info.get("Copyright"))
    special_s = _as_opt_str(info.get("SpecialInstructions"))
    datetime_s = _as_opt_str(info.get("DateTime"))

    exif_summary: Optional[dict[str, Optional[str]]] = None
    if artist_s or copyright_s or datetime_s:
        exif_summary = {"artist": artist_s, "copyright": copyright_s}
        if datetime_s:
            exif_summary["datetime"] = datetime_s

    iptc_cr = _as_opt_str(info.get("IPTC:CopyrightNotice", copyright_s))
    iptc_by = _as_opt_str(info.get("IPTC:By-line", artist_s))
    iptc_sp = _as_opt_str(info.get("IPTC:SpecialInstructions", special_s))

    iptc_summary: Optional[dict[str, Optional[str]]] = {
        "copyright_notice": iptc_cr,
        "by_line": iptc_by,
        "special_instructions": iptc_sp,
    }
    if not any(iptc_summary.values()):
        iptc_summary = None

    return {"exif_summary": exif_summary, "iptc_summary": iptc_summary}


def _read_c2pa_payload(path: Path, suffix: str) -> dict[str, Any]:
    """以 ``Reader.try_create`` 讀取；無 manifest 或例外回傳空 dict。"""
    assert c2pa is not None
    reader_factory = getattr(c2pa, "Reader", None)
    if reader_factory is None:
        return {}
    try_create = getattr(reader_factory, "try_create", None)
    if not callable(try_create):
        return {}
    try:
        reader = try_create(path)
        if reader is None:
            reader = try_create(str(path))
    except TypeError:
        try:
            mime = "image/jpeg" if suffix.lower() in (".jpg", ".jpeg") else "image/png"
            reader = try_create(mime, path)
        except Exception:  # noqa: BLE001
            return {}
    except Exception:  # noqa: BLE001
        return {}
    if reader is None:
        return {}
    cm = reader if hasattr(reader, "__enter__") else nullcontext(reader)
    try:
        with cm as r:
            return _reader_json_to_dict(r)
    except Exception:  # noqa: BLE001
        return {}


def _reader_json_to_dict(reader: Any) -> dict[str, Any]:
    json_fn = getattr(reader, "json", None)
    if not callable(json_fn):
        return {}
    raw_j = json_fn()
    if isinstance(raw_j, str):
        try:
            parsed = json.loads(raw_j)
            return parsed if isinstance(parsed, dict) else {"data": parsed}
        except json.JSONDecodeError:
            return {}
    if isinstance(raw_j, dict):
        return raw_j
    return {}
