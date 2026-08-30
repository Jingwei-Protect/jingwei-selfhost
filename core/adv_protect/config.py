"""Environment configuration for optional adversarial protect (local / experimental)."""

from __future__ import annotations

import os


def adv_protect_enabled() -> bool:
    """Return True when experimental adv-protect API may run heavy inference."""
    return os.environ.get("ENABLE_ADV_PROTECT", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def adv_protect_model_id() -> str:
    return os.environ.get(
        "ADV_PROTECT_MODEL_ID",
        "runwayml/stable-diffusion-v1-5",
    ).strip() or "runwayml/stable-diffusion-v1-5"


def adv_protect_device_pref() -> str:
    """``auto`` | ``cuda`` | ``cpu``."""
    raw = os.environ.get("ADV_PROTECT_DEVICE", "auto").strip().lower()
    if raw in ("cuda", "cpu", "auto"):
        return raw
    return "auto"


def adv_protect_max_side() -> int:
    raw = os.environ.get("ADV_PROTECT_MAX_SIDE", "512").strip()
    try:
        n = int(raw)
    except ValueError:
        return 512
    return max(64, min(n, 1024))
