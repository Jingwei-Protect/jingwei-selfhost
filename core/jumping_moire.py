"""Jumping Moire — dual-band aperiodic moire interference (delivery protection).

Heuristic attack targeting the **VAE encoder** layer of img2img / inpainting
pipelines.  Two bands are injected simultaneously into the Y channel:

- **Low band (0.10-0.22 Nyquist):** survives resize-to-512/1024 preprocessing
  used by many cloud pipelines; slightly more visible, applied at lower opacity.
- **High band (0.30-0.45 Nyquist):** attacks detail-region VAE features before
  preprocessing resize; less perceptible to humans.

Spatial non-stationarity is enforced by partitioning the image into an N x N
grid of cells; each cell uses its own (f, theta, phi) triplet plus sub-pixel
jitter, so global notch filtering cannot remove the perturbation.

Only numpy and scipy are required; no deep-learning dependencies.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

_LOW_BAND: tuple[float, float] = (0.10, 0.22)
_HIGH_BAND: tuple[float, float] = (0.30, 0.45)
_LOW_OPACITY_RATIO: float = 0.5
_HIGH_OPACITY_RATIO: float = 1.0
_MAX_AMP: float = 25.0
_FEATHER_RATIO: float = 0.10
_JITTER_SIGMA: float = 0.6

_OPACITY_MIN: float = 0.0
_OPACITY_MAX: float = 0.30
_GRID_MIN: int = 4
_GRID_MAX: int = 16
_MIN_DIM: int = 64


def _validate_inputs(image: np.ndarray, opacity: float, region_grid_size: int) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    h, w = image.shape[:2]
    if h < _MIN_DIM or w < _MIN_DIM:
        raise ValueError(
            f"Image dimensions must be at least {_MIN_DIM}x{_MIN_DIM}, got {h}x{w}."
        )
    if not (_OPACITY_MIN <= opacity <= _OPACITY_MAX):
        raise ValueError(
            f"opacity must be in [{_OPACITY_MIN}, {_OPACITY_MAX}], got {opacity}."
        )
    if not (_GRID_MIN <= region_grid_size <= _GRID_MAX):
        raise ValueError(
            f"region_grid_size must be in [{_GRID_MIN}, {_GRID_MAX}], got {region_grid_size}."
        )


def _rgb_to_ycbcr(rgb: np.ndarray) -> np.ndarray:
    f = rgb.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = 128.0 - 0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 128.0 + 0.5 * r - 0.418688 * g - 0.081312 * b
    return np.stack([y, cb, cr], axis=-1)


def _ycbcr_to_rgb(ycbcr: np.ndarray) -> np.ndarray:
    y = ycbcr[..., 0]
    cb = ycbcr[..., 1] - 128.0
    cr = ycbcr[..., 2] - 128.0
    r = y + 1.402 * cr
    g = y - 0.344136 * cb - 0.714136 * cr
    b = y + 1.772 * cb
    out = np.stack([r, g, b], axis=-1)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def _fft_bandpass(field: np.ndarray, freq_min: float, freq_max: float) -> np.ndarray:
    h, w = field.shape
    fy = np.fft.fftfreq(h).reshape(-1, 1)
    fx = np.fft.fftfreq(w).reshape(1, -1)
    radius = np.sqrt(fy * fy + fx * fx)
    mask = (radius >= freq_min) & (radius <= freq_max)
    spec = np.fft.fft2(field) * mask
    return np.real(np.fft.ifft2(spec)).astype(np.float32)


def _cosine_window(length: int, feather: int) -> np.ndarray:
    w = np.ones(length, dtype=np.float32)
    if feather <= 0:
        return w
    ramp = 0.5 * (1.0 - np.cos(np.pi * (np.arange(feather) + 1) / (feather + 1)))
    w[:feather] = ramp
    w[-feather:] = ramp[::-1]
    return w


def _generate_moire_field(
    h: int,
    w: int,
    freq_min: float,
    freq_max: float,
    region_grid_size: int,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)

    y_edges = np.linspace(0, h, region_grid_size + 1, dtype=np.int32)
    x_edges = np.linspace(0, w, region_grid_size + 1, dtype=np.int32)

    jitter_u = gaussian_filter(
        rng.standard_normal((h, w)).astype(np.float32), sigma=_JITTER_SIGMA
    )
    jitter_v = gaussian_filter(
        rng.standard_normal((h, w)).astype(np.float32), sigma=_JITTER_SIGMA
    )
    jitter_amp = 1.0 / freq_max * 0.15
    jitter_u *= jitter_amp / max(1e-6, float(np.std(jitter_u)))
    jitter_v *= jitter_amp / max(1e-6, float(np.std(jitter_v)))

    accumulator = np.zeros((h, w), dtype=np.float32)
    weight = np.zeros((h, w), dtype=np.float32)

    for i in range(region_grid_size):
        y0, y1 = int(y_edges[i]), int(y_edges[i + 1])
        for j in range(region_grid_size):
            x0, x1 = int(x_edges[j]), int(x_edges[j + 1])
            ch = y1 - y0
            cw = x1 - x0
            if ch <= 0 or cw <= 0:
                continue

            f1 = float(rng.uniform(freq_min, freq_max))
            theta1 = float(rng.uniform(0.0, np.pi))
            phi1 = float(rng.uniform(0.0, 2.0 * np.pi))
            delta_theta = float(rng.uniform(np.deg2rad(0.5), np.deg2rad(2.0)))
            delta_f = float(rng.normal(0.0, 0.01))
            f2 = max(freq_min * 0.8, f1 + delta_f)
            theta2 = theta1 + delta_theta
            phi2 = float(rng.uniform(0.0, 2.0 * np.pi))

            ys, xs = np.meshgrid(
                np.arange(ch, dtype=np.float32),
                np.arange(cw, dtype=np.float32),
                indexing="ij",
            )
            ju = jitter_u[y0:y1, x0:x1]
            jv = jitter_v[y0:y1, x0:x1]
            u = xs + ju
            v = ys + jv

            k1 = 2.0 * np.pi * f1
            k2 = 2.0 * np.pi * f2
            g1 = np.sin(k1 * (u * np.cos(theta1) + v * np.sin(theta1)) + phi1)
            g2 = np.sin(k2 * (u * np.cos(theta2) + v * np.sin(theta2)) + phi2)
            moire_cell = (g1 + g2).astype(np.float32)

            feather = max(1, int(round(min(ch, cw) * _FEATHER_RATIO)))
            wy = _cosine_window(ch, min(feather, ch // 2))
            wx = _cosine_window(cw, min(feather, cw // 2))
            cell_w = wy[:, None] * wx[None, :]

            accumulator[y0:y1, x0:x1] += moire_cell * cell_w
            weight[y0:y1, x0:x1] += cell_w

    weight = np.where(weight > 1e-6, weight, 1.0)
    field = accumulator / weight

    field = _fft_bandpass(field, freq_min, freq_max)

    max_abs = float(np.max(np.abs(field)))
    if max_abs > 1e-8:
        field = field / max_abs
    return field.astype(np.float32)


_MAX_COMPUTE_DIM = 1024


def apply_jumping_moire(
    image: np.ndarray,
    *,
    opacity: float = 0.15,
    region_grid_size: int = 8,
    seed: int = 42,
) -> np.ndarray:
    """Inject dual-band aperiodic moire interference into an RGB image.

    For images larger than 1024px on either axis, the moire field is
    computed at reduced resolution and upscaled.  The frequency ratios
    are preserved so the perturbation remains equally effective.

    Parameters
    ----------
    image:
        uint8 RGB, shape (H, W, 3), with H, W >= 64.
    opacity:
        Overall injection strength in [0.0, 0.30].
    region_grid_size:
        N (in N x N grid).  Range [4, 16].  Default 8 -> 64 cells.
    seed:
        Deterministic seed for per-cell parameters and jitter fields.

    Returns
    -------
    np.ndarray
        uint8 RGB, same shape as input.
    """
    _validate_inputs(image, opacity, region_grid_size)

    h, w = image.shape[:2]
    ycbcr = _rgb_to_ycbcr(image)
    y = ycbcr[..., 0]

    need_downscale = h > _MAX_COMPUTE_DIM or w > _MAX_COMPUTE_DIM
    if need_downscale:
        scale = _MAX_COMPUTE_DIM / max(h, w)
        ch = max(64, int(h * scale))
        cw = max(64, int(w * scale))
    else:
        ch, cw = h, w

    low_field = _generate_moire_field(
        ch, cw, _LOW_BAND[0], _LOW_BAND[1], region_grid_size, seed
    )
    high_field = _generate_moire_field(
        ch, cw, _HIGH_BAND[0], _HIGH_BAND[1], region_grid_size, seed + 1
    )

    combined = low_field * _LOW_OPACITY_RATIO + high_field * _HIGH_OPACITY_RATIO
    max_abs = float(np.max(np.abs(combined)))
    if max_abs > 1e-8:
        combined = combined / max_abs

    if need_downscale:
        import cv2
        combined = cv2.resize(
            combined, (w, h), interpolation=cv2.INTER_LINEAR
        )

    y_new = y + opacity * _MAX_AMP * combined
    ycbcr_new = ycbcr.copy()
    ycbcr_new[..., 0] = np.clip(y_new, 0.0, 255.0)
    return _ycbcr_to_rgb(ycbcr_new)
