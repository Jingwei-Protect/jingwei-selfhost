"""Rasterize the ProvenPix HoloCard overlays onto RGB frames.

Matches ``frontend/src/holo-card/holo-card.css``:

* rest (``on=0``): the photograph is unchanged
* pointer: one rainbow foil streak (color-dodge), a soft glare, a thin spark
* no full-frame laser grating (that is ``live_glare``, a different effect)

Each exported frame is the card sitting on a desk: metal rim, perspective
tilt, and a moving shadow — the CSS 3D, not a full-bleed foil wipe.
"""

from __future__ import annotations

import math

import numpy as np


def _color_dodge(base: np.ndarray, blend: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    safe = np.clip(1.0 - blend, 1e-4, 1.0)
    dodged = np.clip(base / safe, 0.0, 1.0)
    a = alpha[..., None]
    return base * (1.0 - a) + dodged * a


def _soft_light(base: np.ndarray, blend: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    mixed = (1.0 - 2.0 * blend) * base * base + 2.0 * blend * base
    a = alpha[..., None]
    return base * (1.0 - a) + mixed * a


def _overlay(base: np.ndarray, blend: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    low = 2.0 * base * blend
    high = 1.0 - 2.0 * (1.0 - base) * (1.0 - blend)
    mixed = np.where(base < 0.5, low, high)
    a = alpha[..., None]
    return base * (1.0 - a) + mixed * a


def _projection(h: int, w: int, angle_deg: float) -> np.ndarray:
    """CSS linear-gradient axis: 0deg is up."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rad = math.radians(angle_deg)
    # CSS 0deg → negative Y
    axis_x = math.sin(rad)
    axis_y = -math.cos(rad)
    span = max(1.0, abs(w * axis_x) + abs(h * axis_y))
    return ((xx * axis_x + yy * axis_y) / span).astype(np.float32)


def _foil_layers(h: int, w: int, x: float, y: float) -> tuple[np.ndarray, np.ndarray]:
    angle = 118.0 + (x - 0.5) * 46.0
    proj = _projection(h, w, angle)
    # background-size 180% + position x*120% / y*120%
    shift = (x - 0.5) * 0.55 + (y - 0.5) * 0.25
    t = np.clip(proj - shift + 0.5, 0.0, 1.0)

    stops: list[tuple[float, float, tuple[float, float, float]]] = [
        (0.32, 0.00, (0.00, 0.00, 0.00)),
        (0.44, 0.05, (186 / 255, 230 / 255, 253 / 255)),
        (0.474, 1.00, (186 / 255, 230 / 255, 253 / 255)),
        (0.50, 1.00, (253 / 255, 230 / 255, 138 / 255)),
        (0.526, 1.00, (253 / 255, 164 / 255, 175 / 255)),
        (0.56, 0.05, (221 / 255, 214 / 255, 254 / 255)),
        (0.68, 0.00, (0.00, 0.00, 0.00)),
    ]
    rgb = np.zeros((h, w, 3), dtype=np.float32)
    alpha = np.zeros((h, w), dtype=np.float32)
    for i in range(len(stops) - 1):
        t0, a0, c0 = stops[i]
        t1, a1, c1 = stops[i + 1]
        if t1 <= t0:
            continue
        mask = (t >= t0) & (t <= t1)
        u = np.where(mask, (t - t0) / (t1 - t0), 0.0)
        alpha = np.where(mask, a0 + (a1 - a0) * u, alpha)
        for ch in range(3):
            rgb[:, :, ch] = np.where(mask, c0[ch] + (c1[ch] - c0[ch]) * u, rgb[:, :, ch])
    return rgb, alpha


def _glare_alpha(h: int, w: int, x: float, y: float) -> np.ndarray:
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = x * (w - 1), y * (h - 1)
    radius = 0.28 * max(h, w)
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(radius, 1.0)
    core = np.clip(1.0 - dist / 0.26, 0.0, 1.0)
    mid = np.clip(1.0 - dist / 0.52, 0.0, 1.0)
    return (0.72 * core + 0.12 * np.clip(mid - core, 0.0, 1.0)).astype(np.float32)


def _spark_alpha(h: int, w: int, y: float) -> np.ndarray:
    angle = 72.0 + (y - 0.5) * 28.0
    proj = _projection(h, w, angle)
    t = np.clip(proj + 0.5, 0.0, 1.0)
    band = np.clip(1.0 - np.abs(t - 0.50) / 0.015, 0.0, 1.0)
    fade = np.clip(1.0 - np.abs(t - 0.50) / 0.10, 0.0, 1.0)
    return (0.55 * band + 0.12 * fade).astype(np.float32)


def compose_holo_card(
    image: np.ndarray,
    *,
    x: float,
    y: float,
    on: float,
) -> np.ndarray:
    """Composite ProvenPix foil / glare / spark. ``on=0`` returns ``image``."""
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"image must be HxWx3 uint8, got {image.shape} {image.dtype}")
    strength = float(np.clip(on, 0.0, 1.0))
    if strength <= 1e-4:
        return image.copy()

    h, w = image.shape[:2]
    base = image.astype(np.float32) / 255.0
    px = float(np.clip(x, 0.0, 1.0))
    py = float(np.clip(y, 0.0, 1.0))

    foil_rgb, foil_a = _foil_layers(h, w, px, py)
    out = _color_dodge(base, foil_rgb, foil_a * (strength * 0.70))

    glare = _glare_alpha(h, w, px, py)
    white = np.ones((h, w, 3), dtype=np.float32)
    out = _soft_light(out, white, glare * strength)

    spark = _spark_alpha(h, w, py)
    out = _overlay(out, white, spark * (strength * 0.55))
    return np.clip(np.rint(out * 255.0), 0, 255).astype(np.uint8)


def _rotation(rx_deg: float, ry_deg: float) -> np.ndarray:
    rx = math.radians(rx_deg)
    ry = math.radians(ry_deg)
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    rot_x = np.array([[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]], dtype=np.float32)
    rot_y = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]], dtype=np.float32)
    return rot_y @ rot_x


def _project_card_quad(
    width: int,
    height: int,
    *,
    rx_deg: float,
    ry_deg: float,
    canvas_w: int,
    canvas_h: int,
    lift: float,
) -> np.ndarray:
    """Map card corners through the same rotateX / rotateY / perspective as CSS."""
    hw, hh = width / 2.0, height / 2.0
    corners = np.array(
        [[-hw, -hh, 0.0], [hw, -hh, 0.0], [hw, hh, 0.0], [-hw, hh, 0.0]],
        dtype=np.float32,
    )
    rotated = corners @ _rotation(rx_deg, ry_deg).T
    focal = 2.15 * max(width, height)
    rotated[:, 2] += focal + lift * 0.04 * focal
    z = np.clip(rotated[:, 2], 1e-3, None)
    u = focal * rotated[:, 0] / z + canvas_w / 2.0
    v = focal * rotated[:, 1] / z + canvas_h / 2.0
    return np.stack([u, v], axis=1).astype(np.float32)


def _rim_plate(face: np.ndarray, rim_px: int) -> np.ndarray:
    h, w = face.shape[:2]
    ph, pw = h + 2 * rim_px, w + 2 * rim_px
    yy, xx = np.mgrid[0:ph, 0:pw].astype(np.float32)
    t = np.clip((xx / max(pw - 1, 1) + yy / max(ph - 1, 1)) * 0.5, 0.0, 1.0)
    # Silver rim: #f8fafc → #94a3b8 → #e2e8f0 → #64748b
    c0 = np.array([248, 250, 252], dtype=np.float32)
    c1 = np.array([148, 163, 184], dtype=np.float32)
    c2 = np.array([226, 232, 240], dtype=np.float32)
    c3 = np.array([100, 116, 139], dtype=np.float32)
    plate = np.empty((ph, pw, 3), dtype=np.float32)
    for ch in range(3):
        a = np.where(t < 0.42, c0[ch] + (c1[ch] - c0[ch]) * (t / 0.42), 0.0)
        b = np.where(
            (t >= 0.42) & (t < 0.68),
            c1[ch] + (c2[ch] - c1[ch]) * ((t - 0.42) / 0.26),
            0.0,
        )
        c = np.where(t >= 0.68, c2[ch] + (c3[ch] - c2[ch]) * ((t - 0.68) / 0.32), 0.0)
        plate[:, :, ch] = a + b + c
    plate[rim_px : rim_px + h, rim_px : rim_px + w] = face.astype(np.float32)
    return np.clip(plate, 0, 255).astype(np.uint8)


def _rounded_mask(h: int, w: int, radius: int) -> np.ndarray:
    from PIL import Image, ImageDraw

    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=max(1, radius), fill=255)
    return np.array(mask, dtype=np.uint8)


def render_holo_card_scene(
    image: np.ndarray,
    *,
    x: float,
    y: float,
    on: float,
    rx_deg: float,
    ry_deg: float,
) -> np.ndarray:
    """Photograph on a rimmed card, perspective-tilted over a light desk."""
    import cv2

    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"image must be HxWx3 uint8, got {image.shape} {image.dtype}")
    face = compose_holo_card(image, x=x, y=y, on=on)
    fh, fw = face.shape[:2]
    rim = max(3, int(round(min(fh, fw) * 0.018)))
    plate = _rim_plate(face, rim)
    ph, pw = plate.shape[:2]
    radius = max(6, int(round(min(ph, pw) * 0.045)))
    mask = _rounded_mask(ph, pw, radius)

    pad = 0.24
    canvas_h = int(round(ph * (1.0 + pad * 2)))
    canvas_w = int(round(pw * (1.0 + pad * 2)))
    desk = np.full((canvas_h, canvas_w, 3), (232, 237, 243), dtype=np.uint8)

    lift = float(np.clip(on, 0.0, 1.0))
    dst = _project_card_quad(
        pw, ph, rx_deg=rx_deg, ry_deg=ry_deg, canvas_w=canvas_w, canvas_h=canvas_h, lift=lift,
    )
    src = np.array([[0, 0], [pw, 0], [pw, ph], [0, ph]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)

    shadow_shift = np.array(
        [(x - 0.5) * -0.055 * canvas_w, (0.45 - y) * 0.04 * canvas_h + 0.018 * canvas_h],
        dtype=np.float32,
    )
    shadow_dst = dst + shadow_shift
    shadow_m = cv2.getPerspectiveTransform(src, shadow_dst)
    blob = cv2.warpPerspective(
        np.full((ph, pw), 70, dtype=np.uint8),
        shadow_m,
        (canvas_w, canvas_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    blob = cv2.GaussianBlur(blob, (0, 0), max(3.0, min(canvas_w, canvas_h) * 0.018))
    shade = (blob.astype(np.float32) / 255.0)[..., None]
    desk = np.clip(desk.astype(np.float32) * (1.0 - 0.38 * shade), 0, 255).astype(np.uint8)

    warped = cv2.warpPerspective(
        plate, matrix, (canvas_w, canvas_h), flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT, borderValue=(232, 237, 243),
    )
    alpha = cv2.warpPerspective(
        mask, matrix, (canvas_w, canvas_h), flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT, borderValue=0,
    ).astype(np.float32) / 255.0
    out = desk.astype(np.float32) * (1.0 - alpha[..., None]) + warped.astype(np.float32) * alpha[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


def generate_holo_card_frames(
    image: np.ndarray,
    *,
    n_frames: int = 24,
) -> list[np.ndarray]:
    """Idle 3D rock, then a pointer tilt with one foil streak, then rest.

    First and last frames stay a physical card on the desk (no foil) so the
    Live still reads as a card, not a full-bleed photo.
    """
    if n_frames < 4:
        raise ValueError("n_frames must be at least 4")
    frames: list[np.ndarray] = []
    for i in range(n_frames):
        t = i / (n_frames - 1)
        idle_rx = 6.0 * math.cos(2.0 * math.pi * t)
        idle_ry = -8.0 * math.cos(2.0 * math.pi * t)
        # Middle of the clip is "pointer on"; ends stay idle-only.
        envelope = 0.0
        if 0.12 < t < 0.88:
            u = (t - 0.12) / 0.76
            envelope = math.sin(math.pi * u) ** 1.05
        x = 0.14 + 0.72 * t
        y = 0.24 + 0.52 * (0.5 - 0.5 * math.cos(math.pi * t))
        rx = idle_rx * (1.0 - envelope) + (0.5 - y) * 34.0 * envelope
        ry = idle_ry * (1.0 - envelope) + (x - 0.5) * 40.0 * envelope
        frames.append(
            render_holo_card_scene(image, x=x, y=y, on=envelope, rx_deg=rx, ry_deg=ry)
        )
    return frames

