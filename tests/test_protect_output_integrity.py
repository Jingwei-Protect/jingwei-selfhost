"""End-to-end: protect output must carry LSB + metadata; verify must read both."""

from __future__ import annotations

import io
import base64
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from api.routes.protect import _finalize_image_bytes
from core.compliance_metadata import read_compliance_metadata
from core.jingwei_protocol import JwManifest, embed_jw_watermark
from core.lsb_watermark import embed_lsb_watermark, extract_lsb_watermark
from core.pipeline import protect_image


def _img() -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.integers(30, 220, (256, 256, 3), dtype=np.uint8)


def test_finalize_png_carries_metadata_and_lsb() -> None:
    msg = "TestArtist | 2026-01-01"
    base = protect_image(
        _img(),
        level="standard",
        watermark_text=msg,
        delivery_mode=True,
        protection_mode="stealth",
    )
    manifest = JwManifest(artist="TestArtist", visible_badge=True)
    manifest.set_restriction(1 << 1, True)
    protected = embed_jw_watermark(base, manifest)
    protected = embed_lsb_watermark(protected, msg)

    status: list[str] = []
    raw, mime = _finalize_image_bytes(
        protected,
        output_format="png",
        embed_metadata=True,
        artist="TestArtist",
        status_msgs=status,
    )
    assert mime == "image/png"
    assert not any("失败" in s for s in status), status

    tmp = Path(tempfile.mktemp(suffix=".png"))
    tmp.write_bytes(raw)
    try:
        meta = read_compliance_metadata(tmp)
        assert meta.get("exif") or meta.get("iptc")

        arr = np.array(Image.open(io.BytesIO(raw)).convert("RGB"))
        assert extract_lsb_watermark(arr) == msg
    finally:
        tmp.unlink(missing_ok=True)


def test_verify_reads_metadata_from_raw_bytes() -> None:
    msg = "meta-check"
    img = _img()
    protected = embed_lsb_watermark(img, msg)
    status: list[str] = []
    raw, _ = _finalize_image_bytes(
        protected,
        output_format="png",
        embed_metadata=True,
        artist="MetaUser",
        status_msgs=status,
    )

    tmp = Path(tempfile.mktemp(suffix=".png"))
    tmp.write_bytes(raw)
    try:
        meta = read_compliance_metadata(tmp)
        exif = meta.get("exif") or {}
        iptc = meta.get("iptc") or {}
        assert exif.get("artist") == "MetaUser" or iptc.get("by_line") == "MetaUser"
    finally:
        tmp.unlink(missing_ok=True)


def test_jw_visible_badge_changes_pixels() -> None:
    from core.jingwei_protocol import apply_jw_visible_badge

    manifest = JwManifest(artist="BadgeUser", visible_badge=True)
    out = apply_jw_visible_badge(_img(), manifest)
    assert not np.array_equal(out, _img())


def _rgba_img() -> tuple[np.ndarray, np.ndarray]:
    """Return (HxWx3 RGB, HxW alpha) with a genuine transparent region."""
    rng = np.random.default_rng(99)
    rgb = rng.integers(30, 220, (256, 256, 3), dtype=np.uint8)
    alpha = np.full((256, 256), 255, dtype=np.uint8)
    alpha[100:200, 100:200] = 0
    return rgb, alpha


def test_rgba_png_preserves_alpha() -> None:
    """Transparent PNG in → PNG out should keep the alpha channel intact."""
    rgb, alpha = _rgba_img()
    status: list[str] = []
    raw, mime = _finalize_image_bytes(
        rgb,
        output_format="png",
        embed_metadata=False,
        artist="",
        status_msgs=status,
        alpha_channel=alpha,
    )
    assert mime == "image/png"
    out = Image.open(io.BytesIO(raw))
    assert out.mode == "RGBA", f"Expected RGBA, got {out.mode}"
    out_alpha = np.array(out)[:, :, 3]
    assert out_alpha[150, 150] == 0, "Center region should be transparent"
    assert out_alpha[50, 50] == 255, "Corner region should be opaque"


def test_rgba_jpeg_drops_alpha() -> None:
    """JPEG output always discards alpha without crashing."""
    rgb, alpha = _rgba_img()
    status: list[str] = []
    raw, mime = _finalize_image_bytes(
        rgb,
        output_format="jpg",
        embed_metadata=False,
        artist="",
        status_msgs=status,
        alpha_channel=alpha,
    )
    assert mime == "image/jpeg"
    out = Image.open(io.BytesIO(raw))
    assert out.mode == "RGB"


def test_jw_footer_strip_appends_strip() -> None:
    """Footer strip should expand the image height and be mostly white."""
    from core.jingwei_protocol import apply_jw_footer_strip

    assets = Path(__file__).resolve().parents[1] / "core" / "assets"
    assert (assets / "jingwei-logo.png").is_file(), "Footer logo must ship with backend"

    rgb = _img()
    h, w = rgb.shape[:2]
    manifest = JwManifest(artist="FooterUser", visible_badge=False)
    manifest.set_restriction(1 << 1, True)
    out = apply_jw_footer_strip(rgb, manifest)
    assert out.ndim == 3
    assert out.shape[1] == w
    assert out.shape[0] > h
    strip_region = out[h:, :, :]
    mean_brightness = strip_region.mean()
    assert mean_brightness > 200, f"Footer strip should be mostly white, got mean={mean_brightness}"


def test_jw_footer_strip_rgba() -> None:
    """Footer strip with alpha should return RGBA with opaque footer."""
    from core.jingwei_protocol import apply_jw_footer_strip

    rgb, alpha = _rgba_img()
    h, w = rgb.shape[:2]
    manifest = JwManifest(artist="FooterRGBA", visible_badge=False)
    out = apply_jw_footer_strip(rgb, manifest, alpha_channel=alpha)
    assert out.shape[2] == 4, "Should return RGBA"
    assert out.shape[0] > h
    footer_alpha = out[h:, :, 3]
    assert (footer_alpha == 255).all(), "Footer region alpha must be fully opaque"
    body_alpha = out[:h, :, 3]
    assert body_alpha[150, 150] == 0, "Transparent region should be preserved"


def test_jw_footer_strip_scales_for_large_images() -> None:
    """Footer height should scale with image height, not hit a tiny fixed cap."""
    from core.jingwei_protocol import apply_jw_footer_strip

    rgb = np.zeros((2400, 3200, 3), dtype=np.uint8)
    rgb[:, :] = (180, 190, 200)
    manifest = JwManifest(artist="ScaleUser", visible_badge=False)
    out = apply_jw_footer_strip(rgb, manifest)
    strip_h = out.shape[0] - rgb.shape[0]
    ratio = strip_h / rgb.shape[0]
    assert strip_h > 200, f"Expected proportional footer, got {strip_h}px"
    assert 0.10 <= ratio <= 0.12, f"Footer ratio out of range: {ratio:.3f}"


def test_jw_footer_strip_ratio_consistent_across_sizes() -> None:
    """Branding band keeps ~10.8% of reference height for similar-aspect inputs."""
    from core.jingwei_protocol import apply_jw_footer_strip

    manifest = JwManifest(artist="RatioUser", visible_badge=False)
    ratios: list[float] = []
    for h, w in ((900, 1200), (2400, 3200), (4800, 3600)):
        rgb = np.full((h, w, 3), 200, dtype=np.uint8)
        out = apply_jw_footer_strip(rgb, manifest)
        ratios.append((out.shape[0] - h) / h)
    assert max(ratios) - min(ratios) < 0.015, ratios


def test_jw_footer_strip_wide_panorama_stays_readable() -> None:
    """Wide panoramas size the footer from short edge (~10.8%), matching square exports."""
    from core.jingwei_protocol import apply_jw_footer_strip

    rgb = np.full((800, 6000, 3), 200, dtype=np.uint8)
    manifest = JwManifest(artist="WideUser", visible_badge=False)
    out = apply_jw_footer_strip(rgb, manifest)
    strip_h = out.shape[0] - rgb.shape[0]
    assert strip_h >= 80, f"Wide panorama footer too thin: {strip_h}px"
    assert abs(strip_h / 800 - 0.108) < 0.015


def test_jw_footer_crop_still_extracts_invisible_watermark() -> None:
    """Cropping the visible footer must not remove JW payload from main canvas."""
    from core.jingwei_protocol import (
        JwManifest,
        apply_jw_footer_strip,
        embed_jw_watermark,
        extract_jw_watermark,
    )

    rgb = _img()
    h, w = rgb.shape[:2]
    manifest = JwManifest(artist="CropTest", visible_badge=False)
    manifest.set_restriction(1 << 0, True)
    protected = embed_jw_watermark(rgb, manifest)
    with_footer = apply_jw_footer_strip(protected, manifest)
    cropped = with_footer[:h, :w, :3]

    result = extract_jw_watermark(cropped)
    assert result.get("found"), f"JW must survive footer crop: {result}"
    assert result.get("artist") == "CropTest"


def test_flat_illustration_jw_protect_verify_roundtrip() -> None:
    """Flat-color art (e.g. cartoon) must remain JW-verifiable after protect."""
    import io
    import base64

    from fastapi.testclient import TestClient
    from api.main import app

    flat = np.zeros((900, 900, 3), dtype=np.uint8)
    flat[:, :, 0] = 180
    flat[200:700, 150:750] = [240, 230, 220]
    flat[100:500, 100:500] = [200, 120, 80]
    buf = io.BytesIO()
    Image.fromarray(flat).save(buf, format="PNG")

    client = TestClient(app)
    data = {
        "mode": "stealth",
        "watermark_text": "Jingwei",
        "auto_timestamp": "true",
        "artist": "Jingwei",
        "embed_metadata": "true",
        "output_format": "png",
        "jw_enabled": "true",
        "jw_embed_priority": "auto",
        "jw_creation": "OC",
        "jw_restrictions": "NO-TR,NO-ED",
        "jw_badge": "false",
        "jw_footer_strip": "true",
    }
    res = client.post(
        "/api/protect",
        files={"image": ("flat.png", buf.getvalue(), "image/png")},
        data=data,
    )
    body = res.json()
    assert body.get("ok") is True
    assert body.get("jw_applied") is True
    assert body.get("jw_embed_priority") == "auto"
    assert body.get("jw_embed_method") in ("invisible", "lsb")
    raw = base64.b64decode(body["image"].split(",", 1)[1])
    out_arr = np.array(Image.open(io.BytesIO(raw)).convert("RGB"))
    oh, ow = flat.shape[:2]
    cmp_region = out_arr[:oh, :ow]
    ref = flat
    diff = np.abs(cmp_region.astype(np.int16) - ref.astype(np.int16))
    k = 41
    kernel = np.ones((k, k), dtype=np.uint8)
    interior_max = 0
    for color in np.unique(ref.reshape(-1, 3), axis=0)[:12]:
        mask = np.all(ref == color, axis=2).astype(np.uint8)
        interior = cv2.erode(mask, kernel).astype(bool)
        if interior.sum() < 500:
            continue
        interior_max = max(interior_max, int(diff[interior].max()))
    assert interior_max <= 8, f"flat interior max delta too high: {interior_max}"
    verify = client.post(
        "/api/verify",
        files={"image": ("out.png", raw, "image/png")},
    ).json()
    assert verify["jw"]["found"], verify["jw"]


def test_protect_png_embeds_srgb_icc_even_with_metadata() -> None:
    """Exported PNG should carry sRGB ICC (and keep it after EXIF tEXt embed)."""
    import io
    import base64

    from fastapi.testclient import TestClient
    from api.main import app

    flat = np.full((128, 128, 3), [120, 180, 220], dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(flat).save(buf, format="PNG")

    client = TestClient(app)
    res = client.post(
        "/api/protect",
        files={"image": ("flat.png", buf.getvalue(), "image/png")},
        data={
            "mode": "stealth",
            "artist": "ColorTest",
            "embed_metadata": "true",
            "output_format": "png",
            "jw_enabled": "true",
            "jw_creation": "OC",
            "jw_footer_strip": "false",
        },
    )
    body = res.json()
    assert body.get("ok") is True
    raw = base64.b64decode(body["image"].split(",", 1)[1])
    with Image.open(io.BytesIO(raw)) as im:
        icc = im.info.get("icc_profile")
    assert icc and len(icc) > 100, "protect PNG should embed sRGB ICC profile"
