"""PhotoGuard-style Encoder attack (PGD on VAE latent mean).

Algorithm (inspired by MadryLab PhotoGuard, MIT License — idea/reference only):
1. Resize the image so the long edge ≤ ``max_side`` (default 512).
2. Map pixels to the VAE input range ``[-1, 1]``.
3. Run projected gradient descent that **minimizes** the L2 norm of the VAE
   encoder latent mean, so diffusion img2img / inpaint pipelines that re-encode
   the image see a degraded representation.
4. Project each step into an L∞ ball of radius ``eps`` around the clean image,
   then clamp to ``[-1, 1]``.
5. Map the adversarial image back to uint8 RGB and (if resized) blend the
   residual onto the full-resolution original via bilinear upsampling.

This is the lightweight *Encoder* attack, not the end-to-end diffusion attack.
It does not guarantee protection against all editors or after heavy JPEG/re-encode.
"""

from __future__ import annotations

import time
from typing import Any

import cv2
import numpy as np

from core.adv_protect.config import (
    adv_protect_device_pref,
    adv_protect_max_side,
    adv_protect_model_id,
)

# Cached AutoencoderKL on the resolved device (lazy).
_VAE: Any = None
_VAE_DEVICE: str | None = None
_VAE_MODEL_ID: str | None = None


def torch_installed() -> bool:
    """Return True if ``torch`` can be imported."""
    try:
        import torch  # noqa: F401

        return True
    except ImportError:
        return False


def resolve_device() -> str:
    """Resolve ``ADV_PROTECT_DEVICE`` to ``cuda`` or ``cpu``."""
    pref = adv_protect_device_pref()
    if pref == "cpu":
        return "cpu"
    if pref == "cuda":
        import torch

        if not torch.cuda.is_available():
            raise RuntimeError("ADV_PROTECT_DEVICE=cuda 但当前环境没有可用的 CUDA GPU")
        return "cuda"
    # auto
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def _validate_rgb(image: np.ndarray) -> None:
    if not isinstance(image, np.ndarray):
        raise TypeError("image must be a numpy ndarray")
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image must be HxWx3 uint8 RGB")
    h, w = image.shape[:2]
    if h < 64 or w < 64:
        raise ValueError("image must be at least 64x64")


def _resize_long_edge(image: np.ndarray, max_side: int) -> tuple[np.ndarray, float]:
    h, w = image.shape[:2]
    long_edge = max(h, w)
    if long_edge <= max_side:
        return image, 1.0
    scale = max_side / float(long_edge)
    nh = max(1, int(round(h * scale)))
    nw = max(1, int(round(w * scale)))
    # Keep even sizes for typical VAE stride-8 friendliness.
    nh = max(64, nh - (nh % 8))
    nw = max(64, nw - (nw % 8))
    out = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_AREA)
    return out, scale


def _get_vae(device: str):
    """Load and cache the SD VAE encoder (diffusers AutoencoderKL)."""
    global _VAE, _VAE_DEVICE, _VAE_MODEL_ID
    model_id = adv_protect_model_id()
    if _VAE is not None and _VAE_DEVICE == device and _VAE_MODEL_ID == model_id:
        return _VAE

    import torch
    from diffusers import AutoencoderKL

    dtype = torch.float16 if device == "cuda" else torch.float32
    vae = AutoencoderKL.from_pretrained(model_id, subfolder="vae", torch_dtype=dtype)
    vae = vae.to(device)
    vae.eval()
    for p in vae.parameters():
        p.requires_grad_(False)

    _VAE = vae
    _VAE_DEVICE = device
    _VAE_MODEL_ID = model_id
    return vae


def _pgd_encoder(
    x: "Any",
    vae: Any,
    *,
    eps: float,
    step_size: float,
    steps: int,
    device: str,
) -> "Any":
    """PGD minimizing ``||vae.encode(x).latent_dist.mean||_2`` in pixel space."""
    import torch

    # PhotoGuard demo: random start inside the eps-ball.
    delta = (torch.rand_like(x) * 2 * eps - eps).to(device)
    x_adv = (x + delta).detach()
    x_adv = torch.clamp(x_adv, -1.0, 1.0)

    for i in range(steps):
        # Mild step decay (same spirit as the PhotoGuard notebook schedule).
        actual_step = step_size * (1.0 - i / max(steps, 1))
        x_adv = x_adv.detach().requires_grad_(True)
        latents = vae.encode(x_adv).latent_dist.mean
        loss = latents.norm()
        (grad,) = torch.autograd.grad(loss, [x_adv])
        x_adv = x_adv - grad.detach().sign() * actual_step
        x_adv = torch.minimum(torch.maximum(x_adv, x - eps), x + eps)
        x_adv = torch.clamp(x_adv, -1.0, 1.0)

    return x_adv.detach()


def run_encoder_attack(
    image: np.ndarray,
    *,
    steps: int = 50,
    eps: float = 0.06,
    step_size: float | None = None,
    seed: int = 0,
    max_side: int | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Apply PhotoGuard Encoder attack and return ``(rgb_uint8, metrics)``.

    Parameters
    ----------
    image:
        HxWx3 uint8 RGB.
    steps:
        PGD iterations (higher = stronger / slower). Clamped to ``[1, 200]``.
    eps:
        L∞ radius in ``[-1, 1]`` VAE space (PhotoGuard demo uses ``0.06``).
    step_size:
        PGD step; defaults to ``min(eps * 0.35, 0.02)``.
    seed:
        RNG seed for the initial perturbation.
    max_side:
        Long-edge cap for the attack resolution; ``None`` → env default.
    """
    _validate_rgb(image)
    if not torch_installed():
        raise RuntimeError(
            "未安装对抗保护依赖。请执行: pip install -r requirements-adv.txt"
        )

    import torch

    steps = int(max(1, min(int(steps), 200)))
    eps = float(max(1e-4, min(float(eps), 0.25)))
    if step_size is None:
        step_size = min(eps * 0.35, 0.02)
    else:
        step_size = float(max(1e-5, min(float(step_size), eps)))

    side = int(max_side) if max_side is not None else adv_protect_max_side()
    device = resolve_device()
    t0 = time.perf_counter()

    work, _scale = _resize_long_edge(image, side)
    wh, ww = work.shape[:2]

    torch.manual_seed(int(seed) & 0xFFFFFFFF)
    if device == "cuda":
        torch.cuda.manual_seed_all(int(seed) & 0xFFFFFFFF)

    # uint8 RGB → NCHW float in [-1, 1]
    arr = work.astype(np.float32) / 127.5 - 1.0
    x = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(device)
    if device == "cuda":
        x = x.half()

    vae = _get_vae(device)
    with torch.enable_grad():
        x_adv = _pgd_encoder(
            x, vae, eps=eps, step_size=step_size, steps=steps, device=device
        )

    adv_small = (
        (x_adv[0].float().clamp(-1, 1).cpu().permute(1, 2, 0).numpy() + 1.0) * 127.5
    )
    adv_small = np.clip(np.rint(adv_small), 0, 255).astype(np.uint8)

    # Paste residual back to full resolution when we attacked a downscaled copy.
    if adv_small.shape[:2] != image.shape[:2]:
        residual = adv_small.astype(np.float32) - work.astype(np.float32)
        residual_up = cv2.resize(
            residual,
            (image.shape[1], image.shape[0]),
            interpolation=cv2.INTER_LINEAR,
        )
        out = np.clip(
            np.rint(image.astype(np.float32) + residual_up), 0, 255
        ).astype(np.uint8)
    else:
        out = adv_small

    elapsed = time.perf_counter() - t0
    mse = float(np.mean((out.astype(np.float64) - image.astype(np.float64)) ** 2))
    psnr = 99.0 if mse <= 1e-10 else float(10.0 * np.log10((255.0**2) / mse))

    metrics: dict[str, Any] = {
        "psnr": round(psnr, 2),
        "elapsed_sec": round(elapsed, 2),
        "device": device,
        "steps": steps,
        "eps": eps,
        "attack_size": [int(wh), int(ww)],
        "model_id": adv_protect_model_id(),
        "method": "photoguard_encoder",
    }
    return out, metrics
