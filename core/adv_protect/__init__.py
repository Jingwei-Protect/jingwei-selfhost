"""Optional adversarial (PhotoGuard Encoder) protection — local / experimental."""

from __future__ import annotations

from core.adv_protect.config import adv_protect_enabled
from core.adv_protect.encoder import resolve_device, run_encoder_attack, torch_installed

try:
    from core.adv_protect.diffusion import run_diffusion_attack
except Exception:  # pragma: no cover — optional until deps ready
    run_diffusion_attack = None  # type: ignore[assignment]

__all__ = [
    "adv_protect_enabled",
    "resolve_device",
    "run_encoder_attack",
    "run_diffusion_attack",
    "torch_installed",
]
