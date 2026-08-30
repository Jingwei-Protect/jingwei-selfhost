"""Protect API JSON safety (PSNR inf)."""

from __future__ import annotations

import math

from api.routes.protect import _json_safe_metrics


def test_json_safe_metrics_replaces_inf_psnr() -> None:
    out = _json_safe_metrics({"psnr": float("inf"), "ssim": 1.0, "max_diff": 0, "mean_diff": 0.0})
    assert out["psnr"] is None
    assert math.isfinite(out["ssim"])
