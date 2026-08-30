"""PhotoGuard-style Diffusion attack (UNet path) — experimental / local only.

6GB-friendly design:
- Encode once (no grad) → PGD **in latent space** through UNet only → decode once.
- No VAE.encode in the PGD loop (that path OOMs / thrashing on 6GB laptops).
- Residual is mapped back to full-resolution RGB after decode.

MIT PhotoGuard complex-attack idea; does not guarantee closed-source editors.
"""

from __future__ import annotations

import gc
import time
from typing import Any

import cv2
import numpy as np

from core.adv_protect.config import adv_protect_max_side, adv_protect_model_id
from core.adv_protect.encoder import (
    _resize_long_edge,
    _validate_rgb,
    resolve_device,
    torch_installed,
)

_COMPONENTS: dict[str, Any] | None = None
_COMP_DEVICE: str | None = None
_COMP_MODEL_ID: str | None = None


def _clear_encoder_vae_cache() -> None:
    """Drop cached AutoencoderKL from encoder module to free VRAM."""
    import core.adv_protect.encoder as enc

    enc._VAE = None
    enc._VAE_DEVICE = None
    enc._VAE_MODEL_ID = None
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def release_diffusion_components() -> None:
    """Free cached diffusion weights (call between heavy runs if needed)."""
    global _COMPONENTS, _COMP_DEVICE, _COMP_MODEL_ID
    _COMPONENTS = None
    _COMP_DEVICE = None
    _COMP_MODEL_ID = None
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def _get_components(device: str) -> dict[str, Any]:
    global _COMPONENTS, _COMP_DEVICE, _COMP_MODEL_ID
    model_id = adv_protect_model_id()
    if (
        _COMPONENTS is not None
        and _COMP_DEVICE == device
        and _COMP_MODEL_ID == model_id
    ):
        return _COMPONENTS

    import torch
    from diffusers import AutoencoderKL, DDIMScheduler, UNet2DConditionModel
    from transformers import CLIPTextModel, CLIPTokenizer

    _clear_encoder_vae_cache()
    dtype = torch.float16 if device == "cuda" else torch.float32

    tokenizer = CLIPTokenizer.from_pretrained(model_id, subfolder="tokenizer")
    text_encoder = CLIPTextModel.from_pretrained(
        model_id, subfolder="text_encoder", torch_dtype=dtype
    )
    # Keep text encoder on CPU; only need one forward.
    text_encoder = text_encoder.to("cpu" if device == "cuda" else device)
    vae = AutoencoderKL.from_pretrained(
        model_id, subfolder="vae", torch_dtype=dtype
    ).to(device)
    unet = UNet2DConditionModel.from_pretrained(
        model_id, subfolder="unet", torch_dtype=dtype
    ).to(device)
    scheduler = DDIMScheduler.from_pretrained(model_id, subfolder="scheduler")

    vae.eval()
    unet.eval()
    text_encoder.eval()
    for mod in (vae, unet, text_encoder):
        for p in mod.parameters():
            p.requires_grad_(False)

    try:
        unet.enable_attention_slicing("max")
    except Exception:
        pass
    try:
        vae.enable_slicing()
    except Exception:
        pass

    _COMPONENTS = {
        "tokenizer": tokenizer,
        "text_encoder": text_encoder,
        "vae": vae,
        "unet": unet,
        "scheduler": scheduler,
        "dtype": dtype,
    }
    _COMP_DEVICE = device
    _COMP_MODEL_ID = model_id
    return _COMPONENTS


def run_diffusion_attack(
    image: np.ndarray,
    *,
    steps: int = 20,
    eps: float = 0.08,
    step_size: float | None = None,
    seed: int = 0,
    max_side: int | None = None,
    unet_t: int = 400,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Latent-space PGD through UNet, then single VAE decode."""
    _validate_rgb(image)
    if not torch_installed():
        raise RuntimeError(
            "未安装对抗保护依赖。请执行: pip install -r requirements-adv.txt"
        )

    import torch

    steps = int(max(1, min(int(steps), 60)))
    # Latent eps is in VAE latent units (not pixel [0,1]).
    # Map pixel-ish eps ~0.06–0.12 → latent ~0.08–0.20.
    eps = float(max(1e-4, min(float(eps), 0.25)))
    latent_eps = float(eps) * 2.0
    if step_size is None:
        step_size = min(latent_eps * 0.2, 0.04)
    else:
        step_size = float(max(1e-5, min(float(step_size) * 2.0, latent_eps)))

    side = int(max_side) if max_side is not None else min(adv_protect_max_side(), 384)
    device = resolve_device()
    t0 = time.perf_counter()

    work, _ = _resize_long_edge(image, side)
    wh, ww = work.shape[:2]
    wh = max(64, wh - (wh % 8))
    ww = max(64, ww - (ww % 8))
    if (wh, ww) != work.shape[:2]:
        work = cv2.resize(work, (ww, wh), interpolation=cv2.INTER_AREA)

    torch.manual_seed(int(seed) & 0xFFFFFFFF)
    if device == "cuda":
        torch.cuda.manual_seed_all(int(seed) & 0xFFFFFFFF)
        torch.cuda.empty_cache()

    comps = _get_components(device)
    vae = comps["vae"].to(device)
    unet = comps["unet"].to(device)
    scheduler = comps["scheduler"]
    tokenizer = comps["tokenizer"]
    text_encoder = comps["text_encoder"]
    dtype = comps["dtype"]
    comps["vae"] = vae
    comps["unet"] = unet

    text_inputs = tokenizer(
        [""],
        padding="max_length",
        max_length=tokenizer.model_max_length,
        truncation=True,
        return_tensors="pt",
    )
    with torch.no_grad():
        # text_encoder may live on CPU
        te_device = next(text_encoder.parameters()).device
        text_embeds = text_encoder(text_inputs.input_ids.to(te_device))[0]
        text_embeds = text_embeds.to(device=device, dtype=dtype)

    arr = work.astype(np.float32) / 127.5 - 1.0
    x = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(device=device, dtype=dtype)

    with torch.no_grad():
        z0 = vae.encode(x).latent_dist.mean * vae.config.scaling_factor
        # Free VAE from GPU during UNet PGD to leave room.
        vae = vae.to("cpu")
        comps["vae"] = vae
        if device == "cuda":
            torch.cuda.empty_cache()

    t_val = int(max(1, min(int(unet_t), 999)))
    t_tensor = torch.tensor([t_val], device=device, dtype=torch.long)

    delta = (torch.rand_like(z0) * 2 * latent_eps - latent_eps).detach()
    z_adv = (z0 + delta).detach()

    print(f"  [diffusion] PGD steps={steps} side={wh}x{ww} device={device}", flush=True)
    for i in range(steps):
        actual_step = step_size * (1.0 - 0.4 * i / max(steps, 1))
        z_var = z_adv.detach().requires_grad_(True)
        noise = torch.randn_like(z_var)
        noisy = scheduler.add_noise(z_var, noise, t_tensor)
        pred = unet(noisy, t_tensor, encoder_hidden_states=text_embeds).sample
        # Drive noise prediction toward zero → corrupt denoising path.
        loss = torch.nn.functional.mse_loss(pred, torch.zeros_like(pred))
        (grad,) = torch.autograd.grad(loss, [z_var])
        z_adv = z_var - grad.detach().sign() * actual_step
        z_adv = torch.minimum(torch.maximum(z_adv, z0 - latent_eps), z0 + latent_eps)
        if (i + 1) % 4 == 0 or i == 0:
            print(f"  [diffusion] step {i + 1}/{steps} loss={float(loss.detach()):.4f}", flush=True)

    # Decode once.
    vae = comps["vae"].to(device)
    comps["vae"] = vae
    with torch.no_grad():
        latents = (z_adv / vae.config.scaling_factor).to(dtype=dtype)
        decoded = vae.decode(latents).sample
        adv_small = (
            (decoded[0].float().clamp(-1, 1).cpu().permute(1, 2, 0).numpy() + 1.0)
            * 127.5
        )
    adv_small = np.clip(np.rint(adv_small), 0, 255).astype(np.uint8)

    # Park VAE on CPU again so next call / encoder can reclaim VRAM.
    vae = vae.to("cpu")
    comps["vae"] = vae
    if device == "cuda":
        torch.cuda.empty_cache()

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
    return out, {
        "psnr": round(psnr, 2),
        "elapsed_sec": round(elapsed, 2),
        "device": device,
        "steps": steps,
        "eps": eps,
        "latent_eps": round(latent_eps, 4),
        "attack_size": [int(wh), int(ww)],
        "model_id": adv_protect_model_id(),
        "method": "photoguard_diffusion_latent_unet",
        "unet_t": t_val,
    }
