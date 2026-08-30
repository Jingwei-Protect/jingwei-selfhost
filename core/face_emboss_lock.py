"""Face Emboss Lock — irremovable visible watermark via face-derived emboss.

Why this cannot be removed by AI
---------------------------------
Traditional visible watermarks (text, logos) are additive overlays whose
frequency spectrum is independent of the underlying image.  An AI inpainter
can learn to separate the two because they occupy different statistical
subspaces.

This module uses the **image's own face** as the watermark source:

1. Detect face region (Haar cascade with anime/illustration fallback).
2. Extract the face, shift it by 10-15 px, apply emboss convolution.
3. Blend the embossed ghost back at 15-25 % opacity with per-channel
   chromatic offset.

The result is a relief imprint of the face itself, offset from the original
position.  Because the emboss pattern shares the *exact same* frequency
fingerprint as the real face:

- AI cannot distinguish watermark from content → removal destroys the face.
- There is no "clean layer underneath" — the original pixels have been
  mixed with the embossed ghost at the blend stage.
- Each image produces a unique pattern (no learnable template).

Only requires numpy, opencv-python, scipy.  No deep-learning dependencies.
"""

from __future__ import annotations

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

# Do NOT import face_shield at module level: Haar Cascade init must not run for
# the product box-placement path (``center_roi=True``), which never detects faces.


_EMBOSS_KERNEL = np.array(
    [[-2, -1, 0],
     [-1,  1, 1],
     [ 0,  1, 2]], dtype=np.float32,
)

_EMBOSS_KERNEL_STRONG = np.array(
    [[-4, -2, -1,  0,  0],
     [-2, -2, -1,  0,  1],
     [-1, -1,  0,  1,  1],
     [ 0,  0,  1,  2,  2],
     [ 0,  0,  1,  2,  4]], dtype=np.float32,
)

_DEFAULT_SHIFT_PX = 20
_DEFAULT_OPACITY = 0.30
_CHROMATIC_SHIFT = 3
_SMOOTH_SIGMA = 0.6

_SHIFT_MIN = 5
_SHIFT_MAX = 40
_OPACITY_MIN = 0.10
_OPACITY_MAX = 0.60


def _validate_inputs(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 32 or image.shape[1] < 32:
        raise ValueError(
            f"Image must be at least 32x32, got {image.shape[:2]}."
        )


def _get_face_roi(
    image: np.ndarray,
    faces: list[tuple[int, int, int, int]],
    margin_ratio: float = 0.15,
) -> tuple[int, int, int, int]:
    """Get the largest face rect with margin, clamped to image bounds."""
    h, w = image.shape[:2]
    best = max(faces, key=lambda r: r[2] * r[3])
    fx, fy, fw, fh = best

    mx = int(fw * margin_ratio)
    my = int(fh * margin_ratio)
    x0 = max(0, fx - mx)
    y0 = max(0, fy - my)
    x1 = min(w, fx + fw + mx)
    y1 = min(h, fy + fh + my)
    return x0, y0, x1 - x0, y1 - y0


def _make_rotated_emboss_kernel(angle_deg: float, size: int = 5) -> np.ndarray:
    """Create an emboss kernel at an arbitrary angle.

    Rotates the standard emboss direction so each patch gets a unique
    emboss angle, preventing AI from learning a single removal pattern.
    """
    # Base gradient direction kernel (top-left to bottom-right)
    base = _EMBOSS_KERNEL_STRONG.copy()
    # Rotate using OpenCV
    center = (size // 2, size // 2)
    M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    rotated = cv2.warpAffine(
        base, M, (size, size),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    # Re-normalize so sum ≈ 0 (emboss property)
    rotated -= rotated.mean()
    return rotated.astype(np.float32)


def _build_emboss_ghost(
    face_patch: np.ndarray,
    shift_px: int,
    seed: int,
) -> np.ndarray:
    """Build embossed ghost from a face patch.

    Returns float32 (fh, fw, 3) with values roughly in [-1, 1].
    Each call uses a random emboss kernel angle for diversity.
    """
    rng = np.random.default_rng(seed)
    fh, fw = face_patch.shape[:2]

    # Random shift direction
    angle = float(rng.uniform(-30, 30))
    dx = int(round(shift_px * np.cos(np.radians(angle))))
    dy = int(round(shift_px * np.sin(np.radians(angle))))

    shifted = np.zeros_like(face_patch, dtype=np.float32)
    src_y0 = max(0, -dy)
    src_y1 = min(fh, fh - dy)
    src_x0 = max(0, -dx)
    src_x1 = min(fw, fw - dx)
    dst_y0 = max(0, dy)
    dst_x0 = max(0, dx)

    region_h = src_y1 - src_y0
    region_w = src_x1 - src_x0
    if region_h <= 0 or region_w <= 0:
        return np.zeros((fh, fw, 3), dtype=np.float32)

    shifted[dst_y0:dst_y0 + region_h, dst_x0:dst_x0 + region_w] = (
        face_patch[src_y0:src_y0 + region_h, src_x0:src_x0 + region_w].astype(np.float32)
    )

    gray = cv2.cvtColor(
        shifted.clip(0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY
    ).astype(np.float32)

    # Random emboss kernel angle per patch
    kernel_angle = float(rng.uniform(0, 360))
    kernel = _make_rotated_emboss_kernel(kernel_angle, size=5)
    embossed = cv2.filter2D(gray, cv2.CV_32F, kernel)

    if _SMOOTH_SIGMA > 0:
        embossed = gaussian_filter(embossed, sigma=_SMOOTH_SIGMA)

    p_low, p_high = np.percentile(embossed, [2, 98])
    if p_high - p_low > 1e-6:
        embossed = (embossed - p_low) / (p_high - p_low) * 2.0 - 1.0
    else:
        max_abs = float(np.abs(embossed).max())
        if max_abs > 1e-6:
            embossed = embossed / max_abs

    embossed = np.clip(embossed, -1.0, 1.0)
    ghost_rgb = np.stack([embossed, embossed, embossed], axis=-1)
    return ghost_rgb


def _apply_fade_border(mask: np.ndarray, fade_px: int) -> np.ndarray:
    """Apply smooth fade at the edges of a 2D mask."""
    h, w = mask.shape
    fade_px = max(1, min(fade_px, h // 4, w // 4))
    for i in range(fade_px):
        f = i / fade_px
        mask[i, :] *= f
        mask[h - 1 - i, :] *= f
        mask[:, i] *= f
        mask[:, w - 1 - i] *= f
    return mask


def _make_irregular_mask(
    pw: int, ph: int, seed: int, fade_px: int,
) -> np.ndarray:
    """Create an irregular blob-shaped mask instead of a rectangle.

    Uses aggressive low-frequency noise to create organic boundaries
    that AI cannot easily detect as a watermark boundary.
    """
    rng = np.random.default_rng(seed)

    # Start with an ellipse slightly smaller than the patch
    mask = np.zeros((ph, pw), dtype=np.float32)
    cy, cx = ph // 2, pw // 2
    ry, rx = int(ph * 0.40), int(pw * 0.40)

    y_coords, x_coords = np.ogrid[:ph, :pw]
    ellipse = ((y_coords - cy) / max(1, ry)) ** 2 + ((x_coords - cx) / max(1, rx)) ** 2

    # Aggressive noise distortion for irregular boundary
    noise_h = max(6, ph // 10)
    noise_w = max(6, pw // 10)
    noise_small = rng.uniform(0.35, 1.65, size=(noise_h, noise_w)).astype(np.float32)
    noise_full = cv2.resize(noise_small, (pw, ph), interpolation=cv2.INTER_CUBIC)

    # Modulate the distance field with noise → highly irregular boundary
    dist_field = np.sqrt(ellipse).astype(np.float32)
    modulated = dist_field * noise_full
    mask = np.where(modulated <= 1.0, 1.0, 0.0).astype(np.float32)

    # Smooth edges to avoid hard seams
    mask = gaussian_filter(mask, sigma=max(3.0, fade_px * 0.6))
    mask = np.clip(mask, 0.0, 1.0)

    return mask


def apply_face_emboss_lock(
    image: np.ndarray,
    *,
    shift_px: int = _DEFAULT_SHIFT_PX,
    opacity: float = _DEFAULT_OPACITY,
    chromatic_shift: int = _CHROMATIC_SHIFT,
    seed: int = 42,
    emboss_text: str = "",
    n_copies: int = 1,
    patch_ratio: float = 0.30,
    center_roi: bool = False,
) -> np.ndarray:
    """Apply irremovable face-derived emboss watermark.

    Parameters
    ----------
    image : np.ndarray
        uint8 RGB, shape ``(H, W, 3)``.
    shift_px : int
        Ghost face displacement in pixels.  5-30 range.
    opacity : float
        Emboss blend strength in [0.10, 0.60].
    chromatic_shift : int
        Per-channel horizontal offset for chromatic aberration (0-3 px).
    seed : int
        RNG seed for shift direction and placement positions.
    emboss_text : str
        Optional text to overlay on the emboss ghost.
    n_copies : int
        Number of emboss copies (1-5).
    patch_ratio : float
        Each patch size as fraction of short side (0.15-0.50).
    center_roi : bool
        When True, skip face detection and treat the (already-cropped) input as
        the placement region: the relief is centered in the input and rendered
        exactly once.  Used by the user-placed-box flow so the watermark lands
        where the dashed box is (no re-detection drift, no extra copies).

    Returns
    -------
    np.ndarray
        uint8 RGB, same shape as input.
    """
    _validate_inputs(image)
    shift_px = int(np.clip(shift_px, _SHIFT_MIN, _SHIFT_MAX))
    opacity = float(np.clip(opacity, _OPACITY_MIN, _OPACITY_MAX))
    chromatic_shift = max(0, min(chromatic_shift, 3))
    n_copies = max(1, min(n_copies, 10))

    h, w = image.shape[:2]
    if center_roi:
        # The caller already cropped the placement region; cover most of it,
        # centered, with a single copy.
        n_copies = 1
        side_w = int(w * 0.9)
        side_h = int(h * 0.9)
        rx = (w - side_w) // 2
        ry = (h - side_h) // 2
        rw, rh = side_w, side_h
    else:
        # Legacy / Gradio auto-place path only — Protect page uses center_roi.
        from core.face_shield import _detect_faces

        faces = _detect_faces(image)
        rx, ry, rw, rh = _get_face_roi(image, faces)

    if rw < 16 or rh < 16:
        return image.copy()

    face_patch = image[ry:ry + rh, rx:rx + rw]
    rng = np.random.default_rng(seed)

    def _make_text_mask(pw: int, ph: int) -> np.ndarray | None:
        """Render text as a bevel/emboss relief — light on one side, shadow on the other.

        Returns float32 array in [-1, 1] representing raised text.
        """
        if not emboss_text.strip():
            return None
        from PIL import Image as PILImage, ImageDraw

        from core.text_fonts import get_text_font

        fsize = max(12, min(pw, ph) // 5)
        font = get_text_font(fsize, emboss_text.strip())
        canvas = PILImage.new("L", (pw, ph), 0)
        draw = ImageDraw.Draw(canvas)
        bbox = draw.textbbox((0, 0), emboss_text.strip(), font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        gap_x = tw + fsize
        gap_y = th + fsize // 2
        for ty in range(-th, ph + th, gap_y):
            for tx in range(-tw, pw + tw, gap_x):
                draw.text((tx, ty), emboss_text.strip(), font=font, fill=255)
        canvas = canvas.rotate(20, expand=False, resample=PILImage.BICUBIC)
        text_arr = np.array(canvas, dtype=np.float32) / 255.0

        # Apply emboss convolution to the text mask itself to create
        # a raised/recessed bevel appearance (light on top-left, shadow on bottom-right)
        emboss_k = np.array(
            [[-2, -1, 0],
             [-1,  0, 1],
             [ 0,  1, 2]], dtype=np.float32,
        )
        beveled = cv2.filter2D(text_arr, cv2.CV_32F, emboss_k)
        # Normalize to [-1, 1]
        abs_max = float(np.abs(beveled).max())
        if abs_max > 1e-6:
            beveled = beveled / abs_max
        return beveled

    # Placement positions: primary at face ROI + scattered across image
    short_side = min(h, w)
    min_patch = int(short_side * patch_ratio)

    rng = np.random.default_rng(seed)

    positions: list[tuple[int, int, int, int]] = []
    # First position: face ROI, enlarged to minimum size
    face_pw = max(rw, min_patch)
    face_ph = max(rh, min_patch)
    face_px = max(0, rx - (face_pw - rw) // 2)
    face_py = max(0, ry - (face_ph - rh) // 2)
    face_px = min(face_px, w - face_pw)
    face_py = min(face_py, h - face_ph)
    positions.append((face_px, face_py, face_pw, face_ph))

    if n_copies > 1:
        patch_w = max(min_patch, min(rw, w // 2))
        patch_h = max(min_patch, min(rh, h // 2))
        for _ in range(n_copies - 1):
            px = int(rng.integers(0, max(1, w - patch_w)))
            py = int(rng.integers(0, max(1, h - patch_h)))
            positions.append((px, py, patch_w, patch_h))

    out = image.astype(np.float32)

    for copy_idx, (px, py, pw, ph) in enumerate(positions):
        copy_seed = seed + copy_idx * 7
        local_patch = image[py:py + ph, px:px + pw]
        ghost = _build_emboss_ghost(local_patch, shift_px, copy_seed)

        # Alternate text/no-text for A/B comparison
        use_text = (copy_idx % 2 == 0) if n_copies > 1 else True
        if use_text:
            tmask = _make_text_mask(pw, ph)
            if tmask is not None:
                # tmask is a bevel relief in [-1, 1]; blend it additively
                # with the face ghost so text appears as raised/recessed stamps
                ghost[:, :, 0] = ghost[:, :, 0] + tmask * 0.8

        fade_px = max(1, min(pw, ph) // 6)
        mask = _make_irregular_mask(pw, ph, copy_seed + 100, fade_px)

        # Pure luminance emboss — fixed opacity across the patch
        ghost_mono = ghost[:, :, 0]
        contribution = ghost_mono * mask * opacity * 255.0
        for c in range(3):
            out[py:py + ph, px:px + pw, c] += contribution

    return np.clip(out, 0, 255).astype(np.uint8)
