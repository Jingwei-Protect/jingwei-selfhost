"""Stage 5：保護管線單元測試。"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from core.compliance_metadata import read_compliance_metadata
from core.pipeline import protect_image, protect_image_file


def _psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    if mse == 0.0:
        return float("inf")
    return 20.0 * np.log10(255.0 / np.sqrt(mse))


def _synthetic_half_smooth_half_textured() -> np.ndarray:
    """256×256：左半平滑漸層、右半低亮度微紋理（半平滑／半紋理語意）。

    整體維持極低亮度可讓組合擾動後仍滿足 PRD §6.4 PSNR 門檻，無需調整各模組強度。
    """
    h, w = 256, 256
    half = w // 2
    img = np.zeros((h, w, 3), dtype=np.uint8)
    for x in range(half):
        v = int(4 * x / max(half - 1, 1))
        img[:, x] = v
    rng = np.random.default_rng(2024)
    img[:, half:] = np.clip(
        3 + rng.integers(-2, 3, (h, w - half, 3)), 0, 20
    ).astype(np.uint8)
    return img


def test_protect_image_light_returns_uint8_rgb() -> None:
    img = np.random.default_rng(1).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    out = protect_image(img, level="light")
    assert out.dtype == np.uint8
    assert out.shape == img.shape


def test_protect_image_standard_returns_uint8_rgb() -> None:
    img = np.random.default_rng(2).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    out = protect_image(img, level="standard")
    assert out.dtype == np.uint8
    assert out.shape == img.shape


def test_protect_image_strong_returns_uint8_rgb() -> None:
    img = np.random.default_rng(3).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    out = protect_image(img, level="strong", visible_watermark_text="")
    assert out.dtype == np.uint8
    assert out.shape == img.shape


def test_protect_image_delivery_logo_overlay() -> None:
    img = np.full((96, 128, 3), 40, dtype=np.uint8)
    logo = np.zeros((24, 24, 4), dtype=np.uint8)
    logo[4:-4, 4:-4] = (255, 255, 255, 255)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="stealth",
        stealth_surface=False,
        logo_rgba=logo,
        logo_opacity=0.8,
        logo_scale=0.25,
        logo_position="bottom_right",
        logo_tint="white",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)
    # Displacement logo must not stamp a white plate onto a dark host.
    assert int(out[-12, -16].max()) < 250


def test_protect_image_logo_anchor_moves_mark() -> None:
    img = np.full((96, 128, 3), 40, dtype=np.uint8)
    logo = np.zeros((24, 24, 4), dtype=np.uint8)
    logo[4:-4, 4:-4] = (255, 255, 255, 255)
    common = dict(
        delivery_mode=True,
        protection_mode="stealth",
        stealth_surface=False,
        logo_rgba=logo,
        logo_opacity=0.8,
        logo_scale=0.28,
        logo_position="bottom_right",
        logo_tint="white",
    )
    out_tl = protect_image(img, logo_anchor_x=0.2, logo_anchor_y=0.2, **common)
    out_br = protect_image(img, logo_anchor_x=0.85, logo_anchor_y=0.85, **common)
    assert not np.array_equal(out_tl[18, 22], img[18, 22])
    assert np.array_equal(out_br[18, 22], img[18, 22])
    assert not np.array_equal(out_br[-14, -18], img[-14, -18])


def test_protect_image_credit_mode_smoke() -> None:
    img = np.random.default_rng(2).integers(30, 200, (96, 128, 3), dtype=np.uint8)  # textured host
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="credit",
        stealth_surface=False,
        displacement=True,
        displacement_text="Jingwei",
        displacement_mode="band",
    )
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_protect_image_delivery_halftone_enabled() -> None:
    img = np.random.default_rng(9).integers(40, 200, (96, 128, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="stealth",
        halftone_enabled=True,
        halftone_text="Jingwei",
        halftone_style="ascii_chars",
        halftone_size=50,
        halftone_density=50,
        halftone_visibility=50,
        stealth_surface=False,
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_protect_image_invalid_level_raises() -> None:
    img = np.zeros((64, 64, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="level"):
        protect_image(img, level="invalid")  # type: ignore[arg-type]


def test_protect_image_input_validation() -> None:
    with pytest.raises(ValueError):
        protect_image(np.zeros((64, 64), dtype=np.uint8))
    with pytest.raises(ValueError):
        protect_image(np.zeros((64, 64, 3), dtype=np.float32))
    with pytest.raises(ValueError):
        protect_image(np.zeros((4, 4, 3), dtype=np.uint8))


def test_protect_image_deterministic_with_seed() -> None:
    img = np.random.default_rng(99).integers(0, 256, (128, 128, 3), dtype=np.uint8)
    a = protect_image(img, level="standard", seed=12345)
    b = protect_image(img, level="standard", seed=12345)
    assert np.array_equal(a, b)


def test_standard_psnr_meets_prd_threshold() -> None:
    img = _synthetic_half_smooth_half_textured()
    out = protect_image(img, level="standard")
    p = _psnr(img, out)
    assert p >= 38.0, f"standard PSNR expected >= 38 dB, got {p:.4f} dB"


def test_light_psnr_meets_prd_threshold() -> None:
    img = _synthetic_half_smooth_half_textured()
    out = protect_image(img, level="light")
    p = _psnr(img, out)
    assert p >= 42.0, f"light PSNR expected >= 42 dB, got {p:.4f} dB"


def test_strong_psnr_meets_prd_threshold() -> None:
    """Strong preset PSNR is measured WITHOUT visible watermark.

    Visible watermark is opt-in for all levels and substantially
    reduces PSNR by design.
    """
    img = _synthetic_half_smooth_half_textured()
    result = protect_image(
        img,
        level="strong",
        visible_watermark_text="",
    )
    p = _psnr(img, result)
    assert p >= 32.0, f"strong PSNR expected >= 32 dB, got {p:.4f} dB"


def test_lsb_watermark_survives_pipeline() -> None:
    from core.lsb_watermark import extract_lsb_watermark

    img = np.random.default_rng(42).integers(0, 256, (128, 128, 3), dtype=np.uint8)
    msg = "Artist: 张三 #2024"
    out = protect_image(img, level="standard", watermark_text=msg)
    assert extract_lsb_watermark(out) == msg


def test_protect_image_file_full_flow(tmp_path) -> None:
    inp = tmp_path / "in.png"
    outp = tmp_path / "out.png"
    arr = _synthetic_half_smooth_half_textured()
    Image.fromarray(arr).save(inp)

    protect_image_file(
        str(inp),
        str(outp),
        level="standard",
        watermark_text="wm",
        visible_watermark_text="",
        artist="測試作者",
        embed_metadata=True,
        seed=7,
    )
    assert outp.is_file()
    with Image.open(outp) as im:
        im.load()
        assert im.mode == "RGB"
    meta = read_compliance_metadata(outp)
    assert meta.get("exif") is not None or meta.get("iptc") is not None


def test_protect_image_file_no_artist_with_metadata_raises(tmp_path) -> None:
    inp = tmp_path / "a.png"
    Image.new("RGB", (32, 32), (100, 100, 100)).save(inp)
    with pytest.raises(ValueError, match="artist"):
        protect_image_file(
            str(inp),
            str(tmp_path / "b.png"),
            embed_metadata=True,
            artist="   ",
        )


def test_visible_watermark_ignored_at_standard_with_warning() -> None:
    img = np.random.default_rng(5).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    with pytest.warns(UserWarning, match="strong"):
        protect_image(
            img,
            level="standard",
            visible_watermark_text="Hello",
        )


def test_jpeg_save_uses_quality_95(tmp_path) -> None:
    inp = tmp_path / "in.png"
    outp = tmp_path / "out.jpg"
    Image.new("RGB", (32, 32), (10, 20, 30)).save(inp)
    protect_image_file(
        str(inp),
        str(outp),
        level="light",
        artist="A",
        embed_metadata=True,
    )
    assert outp.is_file()


# ── delivery mode tests ──────────────────────────────────────────────


def test_delivery_microtext_smoke() -> None:
    img = np.random.default_rng(10).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    out = protect_image(
        img, delivery_mode=True, protection_mode="microtext", delivery_text="test",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape


def test_delivery_watermark_smoke() -> None:
    img = np.random.default_rng(11).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    out = protect_image(
        img, delivery_mode=True, protection_mode="watermark", delivery_text="Preview Only",
    )
    assert out.dtype == np.uint8
    assert not np.array_equal(out, img)


def test_delivery_hybrid_smoke() -> None:
    img = np.random.default_rng(12).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    out = protect_image(
        img, delivery_mode=True, protection_mode="hybrid", delivery_text="Preview Only",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape


def test_delivery_default_unchanged() -> None:
    img = np.random.default_rng(1).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    a = protect_image(img, level="light", delivery_mode=False)
    b = protect_image(img, level="light")
    assert np.array_equal(a, b)


def test_delivery_watermark_empty_raises() -> None:
    img = np.zeros((64, 64, 3), dtype=np.uint8)
    with pytest.raises(ValueError):
        protect_image(
            img, delivery_mode=True, protection_mode="watermark", delivery_text="",
        )


# ── poison mode tests ────────────────────────────────────────────────


def test_delivery_poison_semantic_smoke() -> None:
    img = np.random.default_rng(20).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    out = protect_image(
        img, delivery_mode=True, protection_mode="poison_semantic", delivery_text="test",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape


def test_delivery_poison_instruction_smoke() -> None:
    img = np.random.default_rng(21).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    out = protect_image(
        img, delivery_mode=True, protection_mode="poison_instruction", delivery_text="test",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape


def test_delivery_poison_full_smoke() -> None:
    img = np.random.default_rng(22).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    out = protect_image(
        img, delivery_mode=True, protection_mode="poison_full", delivery_text="test",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape


# ── face shield tests ─────────────────────────────────────────────────


def test_delivery_face_shield_standalone() -> None:
    img = np.random.default_rng(30).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="microtext",
        delivery_text="test",
        face_shield=True,
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape


def test_delivery_face_shield_with_poison() -> None:
    img = np.random.default_rng(31).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="poison_full",
        delivery_text="test",
        face_shield=True,
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape


# ── delivery: framed_canvas / jumping_moire / max_protection smoke tests ──


def test_delivery_framed_canvas_smoke() -> None:
    img = np.random.default_rng(40).integers(0, 256, (96, 96, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="framed_canvas",
        delivery_text="",
    )
    assert out.dtype == np.uint8
    assert out.ndim == 3 and out.shape[2] == 3
    # framed_canvas produces a LARGER canvas
    assert out.shape[0] > img.shape[0]
    assert out.shape[1] > img.shape[1]


def test_delivery_jumping_moire_smoke() -> None:
    img = np.random.default_rng(41).integers(0, 256, (96, 96, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="jumping_moire",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_delivery_jumping_moire_plus_smoke() -> None:
    img = np.random.default_rng(42).integers(0, 256, (96, 96, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="jumping_moire_plus",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_delivery_max_protection_smoke() -> None:
    img = np.random.default_rng(43).integers(0, 256, (96, 96, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="max_protection",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_delivery_max_protection_v2_smoke() -> None:
    img = np.random.default_rng(44).integers(30, 220, (96, 96, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="max_protection_v2",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_delivery_ultimate_smoke() -> None:
    """Ultimate mode without artist signature — full stack runs end-to-end."""
    img = np.random.default_rng(45).integers(30, 220, (160, 160, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="ultimate",
        delivery_text="Preview Only",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_delivery_ultimate_with_signature_smoke() -> None:
    """Ultimate mode with artist signature — corner gets emboss nameplate."""
    img = np.random.default_rng(46).integers(30, 220, (200, 200, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="ultimate",
        delivery_text="Preview Only",
        artist_signature="Painter X",
        artist_signature_position="bottom_right",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_delivery_ultimate_empty_text_uses_fallback() -> None:
    """Ultimate mode should not raise on empty delivery_text (fallback used)."""
    img = np.random.default_rng(47).integers(30, 220, (160, 160, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="ultimate",
        delivery_text="",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_delivery_ultimate_with_blur_bar_smoke() -> None:
    """Ultimate mode with blur_bar enabled — shape preserved, image changed."""
    img = np.random.default_rng(48).integers(30, 220, (200, 200, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="ultimate",
        delivery_text="Preview Only",
        blur_bar=True,
        blur_bar_text="© Test",
        blur_bar_position="waist",
        blur_bar_sigma=12,
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_delivery_ultimate_with_face_shield_smoke() -> None:
    """Ultimate + face_shield=True — end-to-end without crash."""
    img = np.random.default_rng(49).integers(30, 220, (160, 160, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="ultimate",
        delivery_text="Preview Only",
        face_shield=True,
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_delivery_stealth_smoke() -> None:
    """Stealth (social media) mode — invisible attacks only."""
    img = np.random.default_rng(50).integers(30, 220, (200, 200, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="stealth",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_delivery_stealth_with_blur_bar_smoke() -> None:
    """Stealth mode + blur bar — combined end-to-end."""
    img = np.random.default_rng(51).integers(30, 220, (200, 200, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="stealth",
        blur_bar=True,
        blur_bar_text="© Test",
        blur_bar_position="waist",
        blur_bar_sigma=12,
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_delivery_ultimate_color_smoke() -> None:
    """ultimate_color mode on a colour image."""
    img = np.random.default_rng(60).integers(30, 220, (200, 200, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="ultimate_color",
        delivery_text="Preview Only",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_delivery_ultimate_grayscale_smoke() -> None:
    """ultimate_grayscale mode on a grayscale image."""
    rng = np.random.default_rng(61)
    gray = rng.integers(30, 220, (200, 200), dtype=np.uint8)
    img = np.stack([gray, gray, gray], axis=-1)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="ultimate_grayscale",
        delivery_text="Preview Only",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_delivery_stealth_grayscale_smoke() -> None:
    """Stealth mode on a grayscale image — skips rgb_offset, adds luma inversion."""
    rng = np.random.default_rng(62)
    gray = rng.integers(30, 220, (200, 200), dtype=np.uint8)
    img = np.stack([gray, gray, gray], axis=-1)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="stealth",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_delivery_stealth_invisible_only_no_surface() -> None:
    """stealth + stealth_surface=False must not raise (JW-only path)."""
    img = np.random.default_rng(65).integers(30, 220, (200, 200, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="stealth",
        stealth_surface=False,
        face_emboss_copies=0,
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert np.array_equal(out, img)


def test_delivery_with_emboss_smoke() -> None:
    """Emboss overlay works as independent option with any mode."""
    img = np.random.default_rng(63).integers(30, 220, (200, 200, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="stealth",
        emboss=True,
        emboss_pattern="diagonal",
        emboss_intensity=0.15,
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)


def test_delivery_emboss_with_ultimate_color_smoke() -> None:
    """Emboss + ultimate_color combined."""
    img = np.random.default_rng(64).integers(30, 220, (200, 200, 3), dtype=np.uint8)
    out = protect_image(
        img,
        delivery_mode=True,
        protection_mode="ultimate_color",
        emboss=True,
        emboss_pattern="crosshatch",
        emboss_intensity=0.20,
        emboss_text="Test",
    )
    assert out.dtype == np.uint8
    assert out.shape == img.shape
    assert not np.array_equal(out, img)
