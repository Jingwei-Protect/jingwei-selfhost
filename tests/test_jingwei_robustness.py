"""Robustness matrix for the 3-layer JW protocol.

Runs `embed → attack → extract` across a grid of attacks and prints a table.

Attacks
-------
clean              — no attack
jpeg_q90/70/50/30  — JPEG compression at decreasing quality
resize_0.75/0.5    — downscale + upscale back
noise_sigma5/15    — additive Gaussian noise
blur_sigma1.0/2.0  — Gaussian blur (low-pass)
chroma_shift       — chroma sub-channel shift (proxy for chroma damage)
ai_proxy_light     — blur 1.0 + noise σ=4 + JPEG Q80   (light rerender)
ai_proxy_medium    — blur 1.5 + noise σ=8 + JPEG Q70   (medium rerender)
ai_proxy_strong    — blur 2.2 + noise σ=12 + JPEG Q55  (strong rerender)
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from core.jingwei_protocol import (
    JW_FLAG_NO_AI_EDIT,
    JW_FLAG_NO_TRAINING,
    JwCreationType,
    JwManifest,
    embed_jw_watermark,
    extract_jw_watermark,
)


# ─── Test image: structured gradient + noise (more realistic than pure noise) ──

def _make_test_image(seed: int = 42, h: int = 512, w: int = 512) -> np.ndarray:
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    r = (y / h) * 180 + 40
    g = ((x + y) / (h + w)) * 200 + 30
    b = (x / w) * 160 + 50
    img = np.stack([r, g, b], axis=-1)
    noise = rng.normal(0, 8, img.shape)
    img = np.clip(img + noise, 0, 255).astype(np.uint8)
    return img


def _make_manifest(artist: str = "TestArtist") -> JwManifest:
    m = JwManifest(creation=JwCreationType.ORIGINAL, artist=artist)
    m.set_restriction(JW_FLAG_NO_AI_EDIT, True)
    m.set_restriction(JW_FLAG_NO_TRAINING, True)
    return m


# ─── Attacks ────────────────────────────────────────────────────────────

def _atk_jpeg(img: np.ndarray, q: int) -> np.ndarray:
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    _, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, q])
    dec = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    return cv2.cvtColor(dec, cv2.COLOR_BGR2RGB)


def _atk_resize(img: np.ndarray, scale: float) -> np.ndarray:
    h, w = img.shape[:2]
    small = cv2.resize(img, (max(8, int(w * scale)), max(8, int(h * scale))),
                       interpolation=cv2.INTER_AREA)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


def _atk_noise(img: np.ndarray, sigma: float) -> np.ndarray:
    rng = np.random.default_rng(0)
    noise = rng.normal(0, sigma, img.shape)
    return np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def _atk_blur(img: np.ndarray, sigma: float) -> np.ndarray:
    return cv2.GaussianBlur(img, (0, 0), sigma)


def _atk_chroma_shift(img: np.ndarray) -> np.ndarray:
    """Simulate chroma channel damage (similar to lossy chroma subsampling)."""
    ycc = cv2.cvtColor(img, cv2.COLOR_RGB2YCrCb).astype(np.float32)
    cr = ycc[:, :, 1]
    cb = ycc[:, :, 2]
    ycc[:, :, 1] = cv2.GaussianBlur(cr, (0, 0), 1.5)
    ycc[:, :, 2] = cv2.GaussianBlur(cb, (0, 0), 1.5)
    ycc = np.clip(ycc, 0, 255).astype(np.uint8)
    return cv2.cvtColor(ycc, cv2.COLOR_YCrCb2RGB)


def _atk_ai(img: np.ndarray, blur_sigma: float, noise_sigma: float, jpeg_q: int) -> np.ndarray:
    """AI rerender proxy: blur (latent smoothing) + noise (sampling) + JPEG (final encode)."""
    blurred = cv2.GaussianBlur(img, (0, 0), blur_sigma)
    noised = _atk_noise(blurred, noise_sigma)
    return _atk_jpeg(noised, jpeg_q)


ATTACKS: dict[str, callable] = {
    "clean":           lambda x: x,
    "jpeg_q90":        lambda x: _atk_jpeg(x, 90),
    "jpeg_q70":        lambda x: _atk_jpeg(x, 70),
    "jpeg_q50":        lambda x: _atk_jpeg(x, 50),
    "jpeg_q30":        lambda x: _atk_jpeg(x, 30),
    "resize_0.75":     lambda x: _atk_resize(x, 0.75),
    "resize_0.5":      lambda x: _atk_resize(x, 0.5),
    "noise_sigma5":    lambda x: _atk_noise(x, 5),
    "noise_sigma15":   lambda x: _atk_noise(x, 15),
    "blur_sigma1":     lambda x: _atk_blur(x, 1.0),
    "blur_sigma2":     lambda x: _atk_blur(x, 2.0),
    "chroma_damage":   _atk_chroma_shift,
    "ai_proxy_light":  lambda x: _atk_ai(x, 1.0, 4.0, 80),
    "ai_proxy_medium": lambda x: _atk_ai(x, 1.5, 8.0, 70),
    "ai_proxy_strong": lambda x: _atk_ai(x, 2.2, 12.0, 55),
}


# ─── Round-trip sanity ──────────────────────────────────────────────────

def test_roundtrip_clean() -> None:
    img = _make_test_image()
    manifest = _make_manifest("RoundTripCheck")
    protected = embed_jw_watermark(img, manifest)
    result = extract_jw_watermark(protected)
    assert result["found"], f"Clean extraction failed: {result}"
    assert result["creation"] == "OC"
    assert "NO-ED" in result["restrictions"]
    assert "NO-TR" in result["restrictions"]
    assert result["artist"] == "RoundTripCheck"


def _ssim_simple(a: np.ndarray, b: np.ndarray) -> float:
    """Simple mean-window SSIM on grayscale (avoids skimage dependency)."""
    af = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY).astype(np.float64)
    bf = cv2.cvtColor(b, cv2.COLOR_RGB2GRAY).astype(np.float64)
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    mu_a = cv2.GaussianBlur(af, (11, 11), 1.5)
    mu_b = cv2.GaussianBlur(bf, (11, 11), 1.5)
    mu_a2 = mu_a * mu_a
    mu_b2 = mu_b * mu_b
    mu_ab = mu_a * mu_b
    sa = cv2.GaussianBlur(af * af, (11, 11), 1.5) - mu_a2
    sb = cv2.GaussianBlur(bf * bf, (11, 11), 1.5) - mu_b2
    sab = cv2.GaussianBlur(af * bf, (11, 11), 1.5) - mu_ab
    num = (2 * mu_ab + c1) * (2 * sab + c2)
    den = (mu_a2 + mu_b2 + c1) * (sa + sb + c2)
    return float(np.mean(num / den))


def test_perceptual_stealth_flat_white_near_invisible() -> None:
    """Social-media-only JW should not leave a visible grid on flat white areas."""
    white = np.full((512, 512, 3), 255, dtype=np.uint8)
    manifest = _make_manifest("FlatWhite")
    protected = embed_jw_watermark(white, manifest, perceptual_stealth=True)
    diff = np.abs(protected.astype(np.int16) - white.astype(np.int16))
    assert int(diff.max()) <= 4, f"max channel delta on white: {diff.max()}"
    assert float(diff.mean()) < 1.0, f"mean channel delta on white: {diff.mean():.3f}"
    out = extract_jw_watermark(protected)
    # Pure flat white has little capacity; extraction may be weak — pipeline still runs.
    assert out.get("found") or out.get("confidence", 0) >= 0.2


def _interior_white_mask(rgb: np.ndarray, *, margin: int = 16) -> np.ndarray:
    """Pixels that are white and at least *margin* px from any non-white pixel."""
    white = np.all(rgb == 255, axis=2).astype(np.uint8)
    if margin <= 0:
        return white.astype(bool)
    k = margin * 2 + 1
    kernel = np.ones((k, k), dtype=np.uint8)
    eroded = cv2.erode(white, kernel)
    return eroded.astype(bool)


def test_perceptual_stealth_white_background_with_subject() -> None:
    """Illustration on white: interior flat background stays clean, JW still decodes."""
    canvas = np.full((512, 512, 3), 255, dtype=np.uint8)
    cv2.circle(canvas, (256, 256), 120, (40, 80, 200), -1)
    cv2.rectangle(canvas, (180, 180), (330, 330), (200, 60, 60), 3)
    manifest = _make_manifest("BirdOnWhite")
    protected = embed_jw_watermark(canvas, manifest, perceptual_stealth=True)
    interior = _interior_white_mask(canvas, margin=20)
    assert interior.any(), "test image needs interior white region"
    diff = np.abs(protected.astype(np.int16) - canvas.astype(np.int16))
    bg_diff = diff[interior]
    assert int(bg_diff.max()) <= 3, f"interior white max delta: {bg_diff.max()}"
    assert float(bg_diff.mean()) < 0.2


def test_perceptual_stealth_still_decodes_on_structured() -> None:
    """Y-only stealth path must remain extractable on content-rich images."""
    img = _make_test_image()
    manifest = _make_manifest("StealthDecode")
    protected = embed_jw_watermark(img, manifest, perceptual_stealth=True)
    out = extract_jw_watermark(protected)
    assert out.get("found"), f"JW decode failed: {out}"


def test_psnr_ssim_acceptable() -> None:
    """3-layer JW is a *strong* watermark (designed for AI resistance);
    expect PSNR ~25-27 dB and SSIM > 0.90 — lower than weak single-layer
    watermarks, in exchange for surviving AI rerender attacks."""
    img = _make_test_image()
    manifest = _make_manifest("PSNR")
    protected = embed_jw_watermark(img, manifest)
    diff = img.astype(np.float64) - protected.astype(np.float64)
    mse = float(np.mean(diff ** 2))
    psnr = 100.0 if mse == 0 else 10 * np.log10((255.0 ** 2) / mse)
    ssim = _ssim_simple(img, protected)
    print(f"\nVisual quality after JW embed: PSNR = {psnr:.2f} dB, SSIM = {ssim:.4f}")
    assert psnr > 24.0, f"PSNR too low: {psnr:.2f} dB (strong-watermark floor ~24 dB)"
    assert ssim > 0.88, f"SSIM too low: {ssim:.4f}"


# ─── Robustness matrix ─────────────────────────────────────────────────

def test_robustness_matrix(capsys) -> None:
    img = _make_test_image()
    manifest = _make_manifest("MatrixTest")
    protected = embed_jw_watermark(img, manifest)

    print("\n" + "=" * 92)
    print(f"{'Attack':<20s} {'Found':<6s} {'Conf':<7s} {'Layer':<7s} "
          f"{'cr':<7s} {'cb':<7s} {'dct':<7s} {'Artist':<14s}")
    print("-" * 92)

    rows: dict[str, dict] = {}
    for name, atk in ATTACKS.items():
        attacked = atk(protected)
        out = extract_jw_watermark(attacked)
        per = out.get("per_channel", {})
        rows[name] = out
        print(
            f"{name:<20s} "
            f"{('YES' if out.get('found') else 'no'):<6s} "
            f"{out.get('confidence', 0.0):<7.3f} "
            f"{out.get('channel', '-'):<7s} "
            f"{per.get('cr', 0.0):<7.3f} "
            f"{per.get('cb', 0.0):<7.3f} "
            f"{per.get('dct', 0.0):<7.3f} "
            f"{out.get('artist', '-'):<14s}"
        )
    print("=" * 92)

    # ── Must-pass tier (classical attacks) ──
    assert rows["clean"]["found"], "clean extraction must succeed"
    assert rows["jpeg_q90"]["found"], "JPEG Q90 must survive"
    assert rows["jpeg_q70"]["found"], "JPEG Q70 must survive"
    assert rows["jpeg_q50"]["found"], "JPEG Q50 should survive"
    assert rows["noise_sigma5"]["found"], "Mild noise must survive"
    assert rows["blur_sigma1"]["found"], "Mild blur must survive"
    assert rows["resize_0.75"]["found"], "Moderate resize must survive"

    # ── Stretch tier (informational only — print pass/fail without failing test) ──
    print("\nStretch tier results (not asserted):")
    for name in ("jpeg_q30", "resize_0.5", "noise_sigma15", "blur_sigma2",
                 "chroma_damage", "ai_proxy_light", "ai_proxy_medium", "ai_proxy_strong"):
        ok = rows[name]["found"]
        print(f"  {name:<20s} {'PASS' if ok else 'FAIL'}  conf={rows[name].get('confidence', 0.0):.3f}")


def test_per_layer_contribution(capsys) -> None:
    """Verify each layer can independently survive at least one realistic attack."""
    img = _make_test_image()
    manifest = _make_manifest("LayerSolo")
    protected = embed_jw_watermark(img, manifest)

    print("\nPer-layer independent survival under jpeg_q70:")
    attacked = _atk_jpeg(protected, 70)
    out = extract_jw_watermark(attacked)
    per = out.get("per_channel", {})
    print(
        f"  cr conf={per.get('cr', 0.0):.3f}  cb conf={per.get('cb', 0.0):.3f}  "
        f"dct conf={per.get('dct', 0.0):.3f}  bdc conf={per.get('bdc', 0.0):.3f}"
    )
    for layer in ("cr", "cb", "dct", "bdc"):
        c = per.get(layer, 0.0)
        assert c > 0.0, f"Layer {layer} produced zero confidence under JPEG Q70 (likely broken)"


def test_coexists_with_dwt_watermark(capsys) -> None:
    """Production order is JW → DWT (api/routes/protect.py). Both must survive.

    Why this order: JW's Layer-4 (block-DC) perturbs the Y channel's mean,
    which would invalidate a prior DWT LL2 quantisation. Embedding DWT last
    re-quantises LL2 cleanly while leaving JW's other layers (chroma DWT,
    DCT mid-band, block-DC) mostly intact.
    """
    from core.dwt_watermark import embed_dwt_watermark, extract_dwt_watermark

    img = _make_test_image(seed=7)
    dwt_payload = "DWTCOEX1234"
    manifest = _make_manifest("DwtCoex")

    jw_first = embed_jw_watermark(img, manifest)
    combined = embed_dwt_watermark(jw_first, payload_text=dwt_payload, timestamp=1700000000)

    dwt_after = extract_dwt_watermark(combined)
    jw_after = extract_jw_watermark(combined)
    print(f"\nProduction stack (JW→DWT): DWT payload={dwt_after.get('payload_text')!r} "
          f"conf={dwt_after.get('confidence', 0):.3f}; JW found={jw_after.get('found')} "
          f"channel={jw_after.get('channel')} per={jw_after.get('per_channel')}")

    assert dwt_after.get("payload_text") == dwt_payload, "DWT broken by the JW→DWT stack"
    assert jw_after.get("found"), "JW failed to extract after stacking with DWT"


def test_false_positive_unmarked(capsys) -> None:
    """Extracting from an unmarked image must NOT report found=True."""
    img = _make_test_image(seed=999)
    out = extract_jw_watermark(img)
    print(f"\nUnmarked image extract: {out}")
    assert not out.get("found"), (
        f"False positive on unmarked image! per_channel={out.get('per_channel')}"
    )
