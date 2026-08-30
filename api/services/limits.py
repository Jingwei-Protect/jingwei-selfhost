"""Upload size / pixel limits + lightweight in-process IP rate limiting.

Production-grade limiting should still use Nginx `limit_req` in front of this
process. This module provides an extra safety net at the application layer and
is suitable for single-instance VPS deployments.

All limits are configurable via environment variables (see ``.env.example``):

* ``MAX_UPLOAD_BYTES``           — hard cap on raw request body (default 12 MiB).
* ``MAX_IMAGE_LONG_EDGE``        — pixel long-edge cap after decode (default 4096).
* ``MAX_IMAGE_PIXELS``           — total pixel cap after decode (default 24 MP).
* ``RATE_LIMIT_PROTECT_PER_MIN``  — per-IP requests/minute on /api/protect.
* ``RATE_LIMIT_PREVIEW_PER_MIN``  — per-IP requests/minute on /api/protect/preview.
* ``RATE_LIMIT_VERIFY_PER_MIN``   — per-IP requests/minute on /api/verify.
* ``RATE_LIMIT_DELIVERY_PER_MIN`` — per-IP requests/minute on /api/delivery.
* ``RATE_LIMIT_AUTH_LOGIN_PER_MIN``    — per-IP login attempts/minute.
* ``RATE_LIMIT_AUTH_REGISTER_PER_MIN`` — per-IP registrations/minute.
* ``RATE_LIMIT_FEEDBACK_PER_MIN`` — per-IP feedback submissions/minute.
* ``RATE_LIMIT_TRUST_PROXY``      — set to ``1`` to trust ``X-Forwarded-For``.
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from typing import Deque

import numpy as np
from fastapi import HTTPException, Request


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def max_upload_bytes() -> int:
    return _env_int("MAX_UPLOAD_BYTES", 12 * 1024 * 1024)


def max_image_long_edge() -> int:
    return _env_int("MAX_IMAGE_LONG_EDGE", 4096)


def max_image_pixels() -> int:
    return _env_int("MAX_IMAGE_PIXELS", 24_000_000)


def rate_limit_protect_per_min() -> int:
    return _env_int("RATE_LIMIT_PROTECT_PER_MIN", 8)


def rate_limit_preview_per_min() -> int:
    """Visible-layer preview is cheap and called while users tweak sliders —
    give it a much larger budget than the heavy /api/protect endpoint."""
    return _env_int("RATE_LIMIT_PREVIEW_PER_MIN", 40)


def rate_limit_verify_per_min() -> int:
    return _env_int("RATE_LIMIT_VERIFY_PER_MIN", 30)


def rate_limit_inspect_per_min() -> int:
    return _env_int("RATE_LIMIT_INSPECT_PER_MIN", 20)


def rate_limit_delivery_per_min() -> int:
    return _env_int("RATE_LIMIT_DELIVERY_PER_MIN", 8)


def rate_limit_delivery_decrypt_batch_per_min() -> int:
    """Batch tile decrypt after unlock — needs a higher budget than encrypt/unlock."""
    return _env_int("RATE_LIMIT_DELIVERY_DECRYPT_BATCH_PER_MIN", 120)


def rate_limit_auth_login_per_min() -> int:
    return _env_int("RATE_LIMIT_AUTH_LOGIN_PER_MIN", 20)


def rate_limit_auth_register_per_min() -> int:
    return _env_int("RATE_LIMIT_AUTH_REGISTER_PER_MIN", 6)


def rate_limit_feedback_per_min() -> int:
    return _env_int("RATE_LIMIT_FEEDBACK_PER_MIN", 5)


def rate_limit_public_visit_per_min() -> int:
    return _env_int("RATE_LIMIT_PUBLIC_VISIT_PER_MIN", 20)


def _trust_proxy() -> bool:
    return os.environ.get("RATE_LIMIT_TRUST_PROXY", "0").strip() == "1"


def client_ip(request: Request) -> str:
    if _trust_proxy():
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
        real = request.headers.get("x-real-ip")
        if real:
            return real.strip()
    return request.client.host if request.client else "unknown"


# ── In-process sliding window per IP+bucket ─────────────────────────────────
_lock = threading.Lock()
_buckets: dict[tuple[str, str], Deque[float]] = {}
_BUCKET_PRUNE_EVERY = 500
_bucket_ops = 0


def _prune_stale_buckets(now: float, *, max_age_sec: float = 120.0) -> None:
    """Drop idle bucket keys so long-running processes do not grow without bound."""
    cutoff = now - max_age_sec
    stale = [key for key, dq in _buckets.items() if not dq or dq[-1] < cutoff]
    for key in stale:
        _buckets.pop(key, None)


def check_rate_limit(request: Request, bucket: str, per_minute: int) -> None:
    """Raise 429 if this IP exceeded ``per_minute`` requests in the last 60s."""
    if per_minute <= 0:
        return
    ip = client_ip(request)
    now = time.monotonic()
    cutoff = now - 60.0
    key = (ip, bucket)
    global _bucket_ops
    with _lock:
        dq = _buckets.get(key)
        if dq is None:
            dq = deque()
            _buckets[key] = dq
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= per_minute:
            retry_after = max(1, int(60 - (now - dq[0])))
            raise HTTPException(
                status_code=429,
                detail=f"请求过于频繁，请 {retry_after}s 后再试",
                headers={"Retry-After": str(retry_after)},
            )
        dq.append(now)
        _bucket_ops += 1
        if _bucket_ops >= _BUCKET_PRUNE_EVERY:
            _bucket_ops = 0
            _prune_stale_buckets(now)


def check_upload_size(raw_size: int) -> None:
    cap = max_upload_bytes()
    if raw_size > cap:
        raise HTTPException(
            status_code=413,
            detail=f"图片体积超过上限（{cap // (1024 * 1024)} MB），请压缩后再上传",
        )


def check_image_pixels(image_array: np.ndarray) -> None:
    h, w = image_array.shape[:2]
    long_edge_cap = max_image_long_edge()
    pixel_cap = max_image_pixels()
    if max(h, w) > long_edge_cap:
        raise HTTPException(
            status_code=413,
            detail=f"图片长边超过 {long_edge_cap}px，请缩小后再上传",
        )
    if h * w > pixel_cap:
        mp_cap = pixel_cap // 1_000_000
        raise HTTPException(
            status_code=413,
            detail=f"图片总像素超过 {mp_cap}MP，请缩小后再上传",
        )
