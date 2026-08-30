"""Visible-layer-only edits — erase or add without touching invisible watermarks."""

from __future__ import annotations

import json
from typing import Any

import cv2
import numpy as np


def parse_add_points(raw: str | None) -> list[tuple[float, float]]:
    """Backward-compatible: parse placements without layer → displacement points."""
    placements = parse_add_placements(raw)
    return [(p["x"], p["y"]) for p in placements if p.get("layer", "displacement") == "displacement"]


def parse_add_placements(raw: str | None) -> list[dict[str, Any]]:
    """Parse JSON list of {layer, x, y, w?, h?} or legacy [x,y] arrays."""
    if not raw or not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("visible_add_points 不是合法 JSON") from exc
    if not isinstance(data, list):
        raise ValueError("visible_add_points 必须是数组")
    out: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            out.append({
                "layer": "displacement",
                "x": max(0.0, min(1.0, float(item[0]))),
                "y": max(0.0, min(1.0, float(item[1]))),
            })
        elif isinstance(item, dict) and "x" in item and "y" in item:
            layer = str(item.get("layer", "displacement"))
            entry: dict[str, Any] = {
                "layer": layer,
                "x": max(0.0, min(1.0, float(item["x"]))),
                "y": max(0.0, min(1.0, float(item["y"]))),
            }
            if "w" in item and item["w"] is not None:
                entry["w"] = max(0.02, min(1.0, float(item["w"])))
            if "h" in item and item["h"] is not None:
                entry["h"] = max(0.02, min(1.0, float(item["h"])))
            out.append(entry)
    return out


def load_erase_mask_png(data: bytes, target_h: int, target_w: int) -> np.ndarray:
    """Load grayscale erase mask, resize to target, return float32 in [0, 1]."""
    arr = np.frombuffer(data, dtype=np.uint8)
    decoded = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if decoded is None:
        raise ValueError("无法读取可见层擦除遮罩")
    if decoded.shape[0] != target_h or decoded.shape[1] != target_w:
        decoded = cv2.resize(decoded, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
    return (decoded.astype(np.float32) / 255.0).clip(0.0, 1.0)


def _blend_patch(body: np.ndarray, patch: np.ndarray, x0: int, y0: int, feather: int = 8) -> np.ndarray:
    ph, pw = patch.shape[:2]
    h, w = body.shape[:2]
    x0 = max(0, min(x0, w - pw))
    y0 = max(0, min(y0, h - ph))
    region = body[y0:y0 + ph, x0:x0 + pw].astype(np.float32)
    alpha = np.ones((ph, pw), dtype=np.float32)
    if feather > 0:
        alpha = cv2.GaussianBlur(alpha, (0, 0), sigmaX=feather, sigmaY=feather)
        alpha = np.clip(alpha, 0, 1)
    a3 = alpha[:, :, np.newaxis]
    blended = region * (1.0 - a3) + patch.astype(np.float32) * a3
    out = body.copy()
    out[y0:y0 + ph, x0:x0 + pw] = np.clip(blended, 0, 255).astype(np.uint8)
    return out


def _apply_emboss_at(body: np.ndarray, cx: float, cy: float, opts: dict[str, Any]) -> np.ndarray:
    from core.emboss_texture import apply_emboss_texture

    h, w = body.shape[:2]
    ps = max(48, int(min(h, w) * float(opts.get("patch_ratio", 0.22))))
    x0 = int(np.clip(cx * w - ps / 2, 0, w - ps))
    y0 = int(np.clip(cy * h - ps / 2, 0, h - ps))
    patch = apply_emboss_texture(
        body[y0:y0 + ps, x0:x0 + ps].copy(),
        pattern=str(opts.get("pattern", "diagonal")),
        emboss_strength=opts.get("strength"),
        text=str(opts.get("text", "")),
        text_density=str(opts.get("text_density", "dense")),
        seed=int(opts.get("seed", 42)),
    )
    return _blend_patch(body, patch, x0, y0)


def _apply_face_emboss_at(body: np.ndarray, cx: float, cy: float, opts: dict[str, Any]) -> np.ndarray:
    from core.face_emboss_lock import apply_face_emboss_lock

    h, w = body.shape[:2]
    ps = max(48, int(min(h, w) * float(opts.get("patch_ratio", 0.28))))
    x0 = int(np.clip(cx * w - ps / 2, 0, w - ps))
    y0 = int(np.clip(cy * h - ps / 2, 0, h - ps))
    patch = apply_face_emboss_lock(
        body[y0:y0 + ps, x0:x0 + ps].copy(),
        shift_px=int(opts.get("shift", 12)),
        opacity=float(opts.get("opacity", 0.25)),
        seed=int(opts.get("seed", 42)),
        emboss_text=str(opts.get("text", "")),
        n_copies=1,
        patch_ratio=0.45,
        center_roi=True,
    )
    return _blend_patch(body, patch, x0, y0, feather=10)


def _apply_blur_placement(body: np.ndarray, placement: dict[str, Any], blur_opts: dict[str, Any]) -> np.ndarray:
    from core.blur_bar import apply_blur_bar, apply_blur_bar_from_mask

    h, w = body.shape[:2]
    layer_w = float(placement.get("w") or blur_opts.get("width_ratio", 0.28))
    layer_h = float(placement.get("h") or blur_opts.get("height_ratio", 0.07))
    if placement.get("w") and placement.get("h"):
        mask = np.zeros((h, w), dtype=np.float32)
        x0 = int(placement["x"] * w)
        y0 = int(placement["y"] * h)
        bw = max(8, int(layer_w * w))
        bh = max(8, int(layer_h * h))
        x0 = max(0, min(x0, w - bw))
        y0 = max(0, min(y0, h - bh))
        mask[y0:y0 + bh, x0:x0 + bw] = 1.0
        return apply_blur_bar_from_mask(
            body, mask,
            text=str(blur_opts.get("text", "")),
            blur_sigma=int(blur_opts.get("sigma", 12)),
            seed=int(blur_opts.get("seed", 42)),
        )
    return apply_blur_bar(
        body,
        text=str(blur_opts.get("text", "")),
        position="custom",
        x_ratio=float(placement["x"]),
        y_ratio=float(placement["y"]),
        width_ratio=layer_w,
        height_ratio=layer_h,
        blur_sigma=int(blur_opts.get("sigma", 12)),
        seed=int(blur_opts.get("seed", 42)),
    )


def apply_visible_edits(
    original: np.ndarray,
    full: np.ndarray,
    invisible_core: np.ndarray,
    *,
    erase_mask: np.ndarray | None = None,
    add_placements: list[dict[str, Any]] | None = None,
    add_blur_mask: np.ndarray | None = None,
    displacement: dict[str, Any] | None = None,
    blur_opts: dict[str, Any] | None = None,
    emboss_opts: dict[str, Any] | None = None,
    face_emboss_opts: dict[str, Any] | None = None,
) -> np.ndarray:
    """Compose final image: erase visible effects via mask, optionally add stamps."""
    if original.ndim != 3 or original.shape[2] != 3:
        raise ValueError("original must be HxWx3 RGB")
    h, w = original.shape[:2]

    body_full = full[:h, :w, :3] if full.shape[0] >= h else full[:, :, :3]
    body_invisible = (
        invisible_core[:h, :w, :3]
        if invisible_core.shape[0] >= h
        else invisible_core[:, :, :3]
    )

    if erase_mask is not None:
        if erase_mask.shape[:2] != (h, w):
            erase_mask = cv2.resize(erase_mask, (w, h), interpolation=cv2.INTER_LINEAR)
        erase_mask = cv2.GaussianBlur(erase_mask, (0, 0), sigmaX=6, sigmaY=6)
        erase_mask = np.clip(erase_mask, 0.0, 1.0).astype(np.float32)
        m3 = erase_mask[:, :, np.newaxis]
        blended = (
            body_full.astype(np.float32) * (1.0 - m3)
            + body_invisible.astype(np.float32) * m3
        )
        edge = (erase_mask > 0.08) & (erase_mask < 0.92)
        if np.any(edge):
            full_luma = (
                0.299 * body_full[:, :, 0]
                + 0.587 * body_full[:, :, 1]
                + 0.114 * body_full[:, :, 2]
            ).astype(np.float32)
            blend_luma = (
                0.299 * blended[:, :, 0]
                + 0.587 * blended[:, :, 1]
                + 0.114 * blended[:, :, 2]
            )
            delta_luma = (full_luma - blend_luma) * erase_mask * edge.astype(np.float32)
            for c, weight in enumerate((0.299, 0.587, 0.114)):
                blended[:, :, c] += delta_luma * weight
        body = np.clip(blended, 0, 255).astype(np.uint8)
    else:
        body = body_full.copy()

    if add_placements:
        seed_base = int((displacement or {}).get("seed", 42))
        for i, placement in enumerate(add_placements):
            layer = placement.get("layer", "displacement")
            cx, cy = float(placement["x"]), float(placement["y"])
            if layer == "displacement" and displacement and displacement.get("text", "").strip():
                from core.displacement_watermark import apply_displacement_single_at

                # One box = one word rendered exactly at the box center, so the
                # on-screen dashed box maps 1:1 to where the text lands. (The old
                # band path auto-picked 3 extra rows and ignored X, so the boxes
                # never matched the result.)
                body = apply_displacement_single_at(
                    body,
                    text=displacement["text"].strip(),
                    shift_px=int(displacement.get("shift", 10)),
                    font_size_ratio=float(displacement.get("font_ratio", 0.15)),
                    seed=seed_base + 1000 + i,
                    shadow_enabled=bool(displacement.get("shadow", True)),
                    shadow_strength=float(displacement.get("shadow_strength", 0.35)),
                    anchor_x=cx,
                    anchor_y=cy,
                )
            elif layer == "blur_bar" and blur_opts:
                body = _apply_blur_placement(body, placement, blur_opts)
            elif layer == "emboss" and emboss_opts:
                opts = {**emboss_opts, "seed": int(emboss_opts.get("seed", 42)) + i}
                body = _apply_emboss_at(body, cx, cy, opts)
            elif layer == "face_emboss" and face_emboss_opts:
                opts = {**face_emboss_opts, "seed": int(face_emboss_opts.get("seed", 42)) + i}
                body = _apply_face_emboss_at(body, cx, cy, opts)

    if add_blur_mask is not None and blur_opts:
        from core.blur_bar import apply_blur_bar_from_mask

        body = apply_blur_bar_from_mask(
            body, add_blur_mask,
            text=str(blur_opts.get("text", "")),
            blur_sigma=int(blur_opts.get("sigma", 12)),
            seed=int(blur_opts.get("seed", 42)) + 500,
        )

    if full.shape[0] > h:
        footer = full[h:, :, :3]
        return np.vstack([body, footer])
    return body
