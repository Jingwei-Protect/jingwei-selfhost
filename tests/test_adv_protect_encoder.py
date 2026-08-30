"""Unit tests for PhotoGuard Encoder helpers (no GPU required for most cases)."""

from __future__ import annotations

import os

import numpy as np
import pytest

from core.adv_protect.config import adv_protect_enabled
from core.adv_protect.encoder import run_encoder_attack, torch_installed


def test_adv_protect_enabled_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_ADV_PROTECT", "0")
    assert adv_protect_enabled() is False
    monkeypatch.setenv("ENABLE_ADV_PROTECT", "true")
    assert adv_protect_enabled() is True


def test_run_encoder_rejects_bad_shape() -> None:
    with pytest.raises((ValueError, TypeError)):
        run_encoder_attack(np.zeros((32, 32), dtype=np.uint8))


def test_run_encoder_rejects_tiny_rgb() -> None:
    with pytest.raises(ValueError, match="64"):
        run_encoder_attack(np.zeros((32, 32, 3), dtype=np.uint8))


@pytest.mark.skipif(not torch_installed(), reason="torch not installed")
def test_run_encoder_smoke_one_step() -> None:
    """Optional smoke: set ADV_PROTECT_SMOKE=1 to allow slow/download-heavy run."""
    if os.environ.get("ADV_PROTECT_SMOKE", "0").strip() not in ("1", "true", "yes"):
        pytest.skip("set ADV_PROTECT_SMOKE=1 to run encoder smoke test")
    img = np.random.default_rng(0).integers(0, 256, size=(96, 96, 3), dtype=np.uint8)
    out, metrics = run_encoder_attack(img, steps=1, eps=0.06, seed=0, max_side=96)
    assert out.shape == img.shape
    assert out.dtype == np.uint8
    assert "psnr" in metrics
    assert metrics["steps"] == 1
