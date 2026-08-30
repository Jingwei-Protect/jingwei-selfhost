"""Optional adversarial protect API (PhotoGuard Encoder) — local / experimental."""

from __future__ import annotations

import base64
import io
import logging

import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

from api.error_codes import (
    ADV_DEPS_MISSING,
    ADV_FEATURE_DISABLED,
    ADV_PROTECT_FAILED,
)
from api.services.limits import (
    check_image_pixels,
    check_rate_limit,
    check_upload_size,
    rate_limit_protect_per_min,
)
from core.adv_protect import (
    adv_protect_enabled,
    resolve_device,
    run_encoder_attack,
    torch_installed,
)
from core.adv_protect.config import adv_protect_model_id

logger = logging.getLogger(__name__)

router = APIRouter(tags=["adv-protect"])


def _read_upload_rgb(upload: UploadFile) -> np.ndarray:
    from core.color_profile import decode_upload_pil
    from core.upload_decode import open_upload_image

    data = upload.file.read()
    check_upload_size(len(data))
    img = open_upload_image(data)
    rgb, _alpha = decode_upload_pil(img)
    return rgb


def _encode_png_data_url(rgb: np.ndarray) -> str:
    pil = Image.fromarray(rgb, mode="RGB")
    buf = io.BytesIO()
    pil.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


@router.get("/adv-protect/status")
def adv_protect_status() -> JSONResponse:
    """Always available: reports whether the experimental path can run."""
    enabled = adv_protect_enabled()
    has_torch = torch_installed()
    device_hint = "unknown"
    if has_torch:
        try:
            device_hint = resolve_device()
        except Exception as exc:  # noqa: BLE001 — status must not 500
            device_hint = f"error:{exc}"
    return JSONResponse(
        {
            "ok": True,
            "enabled": enabled,
            "torch_installed": has_torch,
            "device_hint": device_hint,
            "model_id": adv_protect_model_id(),
        }
    )


@router.post("/adv-protect")
async def adv_protect_run(
    request: Request,
    image: UploadFile = File(...),
    steps: str = Form("50"),
    eps: str = Form("0.06"),
    seed: str = Form("0"),
) -> JSONResponse:
    """Run PhotoGuard Encoder attack when ``ENABLE_ADV_PROTECT=1``."""
    check_rate_limit(request, "adv-protect", rate_limit_protect_per_min())

    if not adv_protect_enabled():
        return JSONResponse(
            {
                "ok": False,
                "error": "对抗保护未启用。本机请在 .env 设置 ENABLE_ADV_PROTECT=1 后重启。",
                "error_code": ADV_FEATURE_DISABLED,
            },
            status_code=403,
        )

    if not torch_installed():
        return JSONResponse(
            {
                "ok": False,
                "error": "未安装对抗保护依赖。请执行: pip install -r requirements-adv.txt",
                "error_code": ADV_DEPS_MISSING,
            },
            status_code=503,
        )

    try:
        steps_i = int(float(steps))
    except (TypeError, ValueError):
        steps_i = 50
    try:
        eps_f = float(eps)
    except (TypeError, ValueError):
        eps_f = 0.06
    try:
        seed_i = int(float(seed))
    except (TypeError, ValueError):
        seed_i = 0

    try:
        rgb = _read_upload_rgb(image)
        check_image_pixels(rgb)
        if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3:
            raise ValueError("图片格式不支持，请上传 RGB 图片")
        if min(rgb.shape[:2]) < 64:
            raise ValueError("图片太小，请上传至少 64x64 像素的图片")

        out, metrics = run_encoder_attack(
            rgb, steps=steps_i, eps=eps_f, seed=seed_i
        )
        return JSONResponse(
            {
                "ok": True,
                "image": _encode_png_data_url(out),
                "metrics": metrics,
            }
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("adv-protect failed")
        return JSONResponse(
            {
                "ok": False,
                "error": str(exc) or "对抗保护处理失败",
                "error_code": ADV_PROTECT_FAILED,
            },
            status_code=500,
        )
