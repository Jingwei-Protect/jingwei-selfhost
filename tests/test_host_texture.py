"""Host texture measurement and strength calibration."""

from __future__ import annotations

import numpy as np
import pytest

from core.host_texture import (
    best_host,
    calibrate_strength,
    conspicuity,
    gradient_magnitude,
    mark_amplitude,
    region_texture,
    texture_map,
)


def _flat(h: int = 120, w: int = 160, value: int = 128) -> np.ndarray:
    return np.full((h, w, 3), value, dtype=np.uint8)


def _noisy(h: int = 120, w: int = 160, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 255, (h, w, 3), dtype=np.uint8)


def test_flat_image_has_no_gradient() -> None:
    assert gradient_magnitude(_flat()).max() == pytest.approx(0.0)


def test_noise_reads_as_more_textured_than_flat() -> None:
    assert gradient_magnitude(_noisy()).mean() > gradient_magnitude(_flat()).mean() + 10


def test_texture_map_keeps_frame_shape() -> None:
    img = _noisy()
    assert texture_map(img, 20, 40).shape == img.shape[:2]


def test_best_host_finds_the_textured_half() -> None:
    img = _flat(120, 200)
    rng = np.random.default_rng(1)
    img[:, 100:] = rng.integers(0, 255, (120, 100, 3), dtype=np.uint8)

    x, _y, texture = best_host(img, 20, 40, centrality=None)
    assert x >= 100
    assert texture > 20


def test_best_host_keeps_the_box_inside_the_frame() -> None:
    x, y, _ = best_host(_noisy(120, 160), 20, 40, centrality=None)
    assert 0 <= x <= 160 - 40
    assert 0 <= y <= 120 - 20


def test_best_host_rejects_a_mark_larger_than_the_frame() -> None:
    with pytest.raises(ValueError):
        best_host(_flat(50, 50), 60, 20)


def test_centrality_pulls_the_choice_inward() -> None:
    """The busiest patch sits at the edge; a quieter one sits dead centre.

    Unweighted the edge should win on texture alone. Weighted the centre should
    win despite carrying less, which is the whole point of the bias: the subject
    is worth marking even where the background is busier.
    """
    img = _flat(200, 400)
    rng = np.random.default_rng(2)
    img[80:120, 10:70] = rng.integers(0, 255, (40, 60, 3), dtype=np.uint8)
    img[80:120, 170:230] = rng.integers(60, 195, (40, 60, 3), dtype=np.uint8)

    edge_x, _, edge_texture = best_host(img, 40, 60, centrality=None)
    centre_x, _, centre_texture = best_host(img, 40, 60, centrality=0.30)

    assert edge_x < 100, "unweighted search should take the busier edge patch"
    assert centre_x > 100, "centrality should pull the choice to the middle"
    assert centre_texture < edge_texture


def test_region_texture_reads_zero_on_flat_colour() -> None:
    region = np.zeros((120, 160), dtype=bool)
    region[40:80, 40:120] = True
    assert region_texture(_flat(), region) == pytest.approx(0.0)


def test_mark_amplitude_scales_with_the_change() -> None:
    clean = _flat()
    region = np.zeros((120, 160), dtype=bool)
    region[40:80, 40:120] = True

    faint = clean.copy()
    faint[region] = 118
    strong = clean.copy()
    strong[region] = 88

    assert mark_amplitude(clean, faint, region) == pytest.approx(10.0, abs=1.0)
    assert mark_amplitude(clean, strong, region) == pytest.approx(40.0, abs=1.0)


def test_conspicuity_is_infinite_on_a_flat_host() -> None:
    clean = _flat()
    region = np.zeros((120, 160), dtype=bool)
    region[40:80, 40:120] = True
    marked = clean.copy()
    marked[region] = 100

    assert conspicuity(clean, marked, region) == float("inf")


def test_conspicuity_ignores_an_unmarked_flat_host() -> None:
    clean = _flat()
    region = np.zeros((120, 160), dtype=bool)
    region[40:80, 40:120] = True
    assert conspicuity(clean, clean, region) == 0.0


def test_same_amplitude_is_less_conspicuous_on_texture() -> None:
    region = np.zeros((120, 160), dtype=bool)
    region[40:80, 40:120] = True

    flat = _flat()
    busy = _noisy()
    on_flat = flat.astype(np.int16).copy()
    on_busy = busy.astype(np.int16).copy()
    on_flat[region] -= 20
    on_busy[region] -= 20
    on_flat = np.clip(on_flat, 0, 255).astype(np.uint8)
    on_busy = np.clip(on_busy, 0, 255).astype(np.uint8)

    assert conspicuity(busy, on_busy, region) < conspicuity(flat, on_flat, region)


def test_calibration_hits_the_target_amplitude() -> None:
    clean = _flat()
    region = np.zeros((120, 160), dtype=bool)
    region[40:80, 40:120] = True

    def render(strength: float) -> np.ndarray:
        out = clean.astype(np.float64).copy()
        out[region] *= 1.0 - strength
        return np.clip(out, 0, 255).astype(np.uint8)

    strength, _img, amp = calibrate_strength(render, clean, region, 32.0)
    assert amp == pytest.approx(32.0, abs=1.0)
    assert 0.0 < strength < 1.0


def test_calibration_reports_overshoot_when_the_floor_is_too_strong() -> None:
    """Displacement alone can exceed the target on a busy host."""
    clean = _flat()
    region = np.zeros((120, 160), dtype=bool)
    region[40:80, 40:120] = True

    def render(strength: float) -> np.ndarray:
        out = clean.astype(np.float64).copy()
        out[region] -= 50.0 + 40.0 * strength
        return np.clip(out, 0, 255).astype(np.uint8)

    strength, _img, amp = calibrate_strength(render, clean, region, 10.0)
    assert strength == 0.0
    assert amp > 10.0
