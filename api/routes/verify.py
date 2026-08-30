"""Verification API — extracts watermarks and metadata from uploaded image."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import numpy as np
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

from api.services.limits import (
    check_image_pixels,
    check_rate_limit,
    check_upload_size,
    rate_limit_verify_per_min,
)

router = APIRouter(tags=["verify"])


def _recover_signed_date(results: dict) -> str | None:
    """Recover the exact embed date (``YYYY-MM-DD``) from any surviving layer.

    The screenshot-robust anchor only carries year-month (16-bit budget), so the
    day is dropped there. The exact date is written at protect time into JW
    (``protected_at``), file metadata DateTime, and/or independent DWT/LSB — the
    user never types a date manually. We pull the day from whichever layer
    survived so the verify result can show ``signature + 年月日``. Returns None
    when only the anchor survives (e.g. screenshot) — then we fall back to
    year-month.
    """
    import datetime
    import re

    # 1) JW declaration embeds protected_at when auto_timestamp is on (no manual DWT needed).
    jw = results.get("jw") or {}
    if jw.get("found") and jw.get("protected_at"):
        try:
            return datetime.datetime.strptime(
                str(jw["protected_at"])[:10], "%Y-%m-%d",
            ).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # 2) Standalone / auto-seeded DWT timestamp.
    dwt = results.get("dwt") or {}
    ts = dwt.get("timestamp")
    if ts:
        try:
            return datetime.datetime.strptime(str(ts)[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            pass
    # 3) LSB suffix " | YYYY-MM-DD HH:MM:SS".
    lsb = results.get("lsb") or {}
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(lsb.get("text") or ""))
    if m:
        try:
            return datetime.date(int(m[1]), int(m[2]), int(m[3])).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # 4) DWT payload suffix "..._MMDD_HHMM" — no year, so borrow the anchor's year.
    anchor = results.get("anchor") or {}
    year = anchor.get("year")
    pm = re.search(r"_(\d{2})(\d{2})_\d{4}$", str(dwt.get("payload") or ""))
    if pm and year:
        try:
            return datetime.date(int(year), int(pm[1]), int(pm[2])).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # 5) Compliance metadata DateTime (written when JW or tracking is on).
    meta = results.get("metadata") or {}
    for bucket in (meta.get("exif") or {}, meta.get("iptc") or {}):
        raw_dt = bucket.get("datetime")
        if not raw_dt:
            continue
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y:%m:%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(str(raw_dt)[:19], fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


def _detection_image(image: np.ndarray, *, max_long_edge: int = 2048) -> np.ndarray:
    """Downscale very large uploads before frequency-domain watermark scans."""
    h, w = image.shape[:2]
    long_edge = max(h, w)
    if long_edge <= max_long_edge:
        return image
    scale = max_long_edge / long_edge
    nh = max(128, int(round(h * scale)))
    nw = max(128, int(round(w * scale)))
    resized = Image.fromarray(image).resize((nw, nh), Image.Resampling.LANCZOS)
    return np.array(resized, dtype=np.uint8)


def _read_upload_raw(upload: UploadFile) -> tuple[np.ndarray, bytes, str]:
    data = upload.file.read()
    check_upload_size(len(data))
    suffix = Path(upload.filename or "upload.png").suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".webp"):
        suffix = ".png"
    img = Image.open(io.BytesIO(data)).convert("RGB")
    return np.array(img, dtype=np.uint8), data, suffix


@router.post("/verify")
async def verify(
    request: Request,
    image: UploadFile = File(...),
    blind_wm_len: int = 0,
    blind_wm_password: int = 1234,
    claim_artists: str = Form(""),
) -> JSONResponse:
    check_rate_limit(request, "verify", rate_limit_verify_per_min())
    image_array, raw_bytes, suffix = _read_upload_raw(image)
    check_image_pixels(image_array)
    results: dict = {"dwt": None, "lsb": None, "metadata": None, "blind_wm": None,
                     "jw": None, "c2pa": None, "anchor": None}
    detection_array = _detection_image(image_array)

    try:
        from core.jingwei_protocol import extract_jw_for_verify

        results["jw"] = extract_jw_for_verify(detection_array)
    except Exception as exc:
        results["jw"] = {"found": False, "error": str(exc)}

    jw_found = bool(results.get("jw") and results["jw"].get("found"))

    try:
        from core.dwt_watermark import extract_dwt_watermark
        import datetime

        dwt = extract_dwt_watermark(detection_array)
        conf = float(dwt.get("confidence", 0))
        payload = dwt.get("payload_text") or ""
        # Only sweep scales when a payload was partially decoded but below threshold.
        # Empty payload + zero confidence is the normal unmarked case — skip recovery.
        if not jw_found and payload and conf < 0.60:
            from core.screenshot_recovery import extract_dwt_with_recovery

            dwt = extract_dwt_with_recovery(detection_array, initial_result=dwt)
            conf = float(dwt.get("confidence", 0))
            payload = dwt.get("payload_text") or ""
        ts = dwt.get("timestamp", 0)
        ts_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts > 0 else None
        results["dwt"] = {
            "found": conf >= 0.60 and bool(payload),
            "payload": payload,
            "timestamp": ts_str,
            "confidence": round(conf, 4),
            "recovered": bool(dwt.get("recovered")),
            "recovery": dwt.get("recovery"),
        }
    except Exception as exc:
        results["dwt"] = {"found": False, "error": str(exc)}

    try:
        from core.lsb_watermark import extract_lsb_watermark

        text = extract_lsb_watermark(image_array)
        results["lsb"] = {"found": True, "text": text}
    except ValueError:
        results["lsb"] = {"found": False}
    except Exception as exc:
        results["lsb"] = {"found": False, "error": str(exc)}

    tmp = Path(tempfile.mktemp(suffix=suffix))
    try:
        tmp.write_bytes(raw_bytes)
        from core.compliance_metadata import read_compliance_metadata
        from core.c2pa_verify import read_c2pa_from_path

        meta = read_compliance_metadata(str(tmp))
        exif = meta.get("exif") or {}
        iptc = meta.get("iptc") or {}
        has_meta = bool(exif) or bool(iptc)
        results["metadata"] = {
            "found": has_meta,
            "exif": exif if has_meta else None,
            "iptc": iptc if has_meta else None,
        }
        results["c2pa"] = read_c2pa_from_path(tmp)
    except Exception as exc:
        results["metadata"] = {"found": False, "error": str(exc)}
        results["c2pa"] = {"found": False, "available": False, "error": str(exc)}
    finally:
        tmp.unlink(missing_ok=True)

    if blind_wm_len > 0:
        try:
            from core.blind_watermark_adapter import extract_blind_watermark

            text = extract_blind_watermark(image_array, blind_wm_len, password=blind_wm_password)
            results["blind_wm"] = {"found": True, "text": text}
        except Exception as exc:
            results["blind_wm"] = {"found": False, "error": str(exc)}
    else:
        results["blind_wm"] = {"found": False, "hint": "需提供 wm_bit_length 才能提取强化盲水印"}

    # Screenshot-robust traceability anchor (追踪巩固): decode after other layers so
    # we can auto-translate the artist code from any surviving signature field.
    try:
        from core.jingwei_protocol import _estimate_orig_height_with_footer
        from core.jw_anchor import artist_code as _artist_code, read_anchor_tracking

        anchor = None
        h, w = detection_array.shape[:2]
        est_orig_h = _estimate_orig_height_with_footer(h, w)
        canvases = [detection_array]
        if est_orig_h is not None and 0 < est_orig_h < h:
            canvases.append(detection_array[:est_orig_h, :w])
        for canvas in canvases:
            hit = read_anchor_tracking(canvas)
            if hit is None:
                continue
            if anchor is None or hit.get("confidence", 0.0) > anchor.get("confidence", 0.0):
                anchor = hit
        if anchor is None:
            results["anchor"] = {"found": False}
        else:
            code = anchor["artist_code"]
            seen: set[str] = set()
            user_claims: list[str] = []
            for raw in (claim_artists or "").split("\n"):
                s = raw.strip()
                if s and s.lower() not in seen:
                    seen.add(s.lower())
                    user_claims.append(s)
            candidates: list[str] = list(user_claims)
            jw_data = results.get("jw") or {}
            for raw in (
                jw_data.get("artist"),
                (jw_data.get("manifest") or {}).get("artist"),
            ):
                if raw and str(raw).strip().lower() not in seen:
                    seen.add(str(raw).strip().lower())
                    candidates.append(str(raw).strip())
            dwt_data = results.get("dwt") or {}
            if dwt_data.get("found") and dwt_data.get("payload"):
                s = str(dwt_data["payload"]).strip()
                if s.lower() not in seen:
                    seen.add(s.lower())
                    candidates.append(s)
            lsb_data = results.get("lsb") or {}
            if lsb_data.get("found") and lsb_data.get("text"):
                s = str(lsb_data["text"]).strip()
                if s.lower() not in seen:
                    seen.add(s.lower())
                    candidates.append(s)
            meta_data = results.get("metadata") or {}
            for bucket in (meta_data.get("exif") or {}, meta_data.get("iptc") or {}):
                for key in ("artist", "Artist", "by-line", "By-line"):
                    raw = bucket.get(key)
                    if raw and str(raw).strip().lower() not in seen:
                        seen.add(str(raw).strip().lower())
                        candidates.append(str(raw).strip())

            claim_checked = bool(user_claims)
            matched_name = None
            matched_from_user = False
            for name in candidates:
                if _artist_code(name) == code:
                    matched_name = name
                    matched_from_user = name in user_claims
                    break
            claim_code: str | None = None
            if user_claims:
                claim_code = f"{_artist_code(user_claims[0]):03d}"
            # Only unlock the author display when the *user's*核对签名 matched.
            user_match = matched_name if matched_from_user else None
            results["anchor"] = {
                "found": True,
                "artist_code": f"{code:03d}",
                "artist_name": user_match,
                "artist_matches": (user_match is not None) if claim_checked else None,
                "claim_checked": claim_checked,
                "claim_code": claim_code,
                "year": anchor["year"],
                "month": anchor["month"],
                "year_month": f"{anchor['year']}-{anchor['month']:02d}",
                "confidence": round(float(anchor.get("confidence", 0.0)), 4),
            }
            # Upgrade to a full date (with day) when an intact hidden layer
            # preserved the exact embed timestamp; the anchor alone is month-only.
            signed_date = _recover_signed_date(results)
            if signed_date:
                results["anchor"]["signed_date"] = signed_date
    except Exception as exc:
        results["anchor"] = {"found": False, "error": str(exc)}

    return JSONResponse({"ok": True, **results})
