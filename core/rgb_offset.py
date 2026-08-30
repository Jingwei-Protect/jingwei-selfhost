"""RGB channel offset - cross-attention layer attack (delivery protection).

Shifts the R and B channels by a small spatial offset while keeping G fixed.
The result is a subtle "3D color fringe" effect (similar to an uncalibrated
print head) that is mostly tolerable to a human viewer.

Why this targets the cross-attention layer:
- A diffusion / VLM cross-attention layer locates objects by aligning
  color-coherent regions: text token ``"hair"`` attends to where R, G, B
  jointly form the colour signature of hair.
- If R-hair sits N px right and B-hair sits N px left of G-hair, the
  attention map cannot collapse onto a single coherent region.

The transform is fully deterministic: same shifts -> same output.  The
``seed`` parameter is accepted for API symmetry but is not used.

Only numpy is required.
"""

from __future__ import annotations

import numpy as np

_MAX_ABS_SHIFT: int = 8


def _validate_inputs(
    image: np.ndarray,
    r_shift: tuple[int, int],
    b_shift: tuple[int, int],
) -> None:
    if image.dtype != np.uint8:
        raise ValueError(f"Input dtype must be uint8, got {image.dtype}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Input must be HxWx3 RGB, got shape {image.shape}.")
    if image.shape[0] < 8 or image.shape[1] < 8:
        raise ValueError(
            f"Image dimensions must be at least 8x8, got {image.shape[:2]}."
        )
    for name, shift in (("r_shift", r_shift), ("b_shift", b_shift)):
        if (
            not isinstance(shift, tuple)
            or len(shift) != 2
            or not all(isinstance(v, (int, np.integer)) for v in shift)
        ):
            raise ValueError(f"{name} must be a (dx, dy) tuple of ints, got {shift!r}.")


def _clamp_shift(shift: tuple[int, int]) -> tuple[int, int]:
    dx = int(np.clip(shift[0], -_MAX_ABS_SHIFT, _MAX_ABS_SHIFT))
    dy = int(np.clip(shift[1], -_MAX_ABS_SHIFT, _MAX_ABS_SHIFT))
    return dx, dy


def _shift_channel(channel: np.ndarray, shift: tuple[int, int]) -> np.ndarray:
    """Shift a 2-D channel by (dx, dy), zeroing the wrapped border pixels."""
    dx, dy = shift
    if dx == 0 and dy == 0:
        return channel.copy()

    rolled = np.roll(channel, shift=(dy, dx), axis=(0, 1))
    if dy > 0:
        rolled[:dy, :] = 0
    elif dy < 0:
        rolled[dy:, :] = 0
    if dx > 0:
        rolled[:, :dx] = 0
    elif dx < 0:
        rolled[:, dx:] = 0
    return rolled


def apply_rgb_offset(
    image: np.ndarray,
    *,
    r_shift: tuple[int, int] = (2, 0),
    b_shift: tuple[int, int] = (-2, 0),
    seed: int = 42,
    detail_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Shift R and B channels by small offsets to disrupt cross-attention alignment.

    Parameters
    ----------
    image:
        uint8 RGB, shape (H, W, 3).
    r_shift, b_shift:
        ``(dx, dy)`` pixel offsets for the R and B channels.  Each component is
        clamped to ``[-8, 8]``.
    seed:
        Accepted for API symmetry; the transform itself is fully deterministic.
    detail_mask:
        Optional float32 (H, W) mask in [0,1].  When provided, the channel
        shift is blended with the original using this mask: full shift on
        edges/textures (mask=1), no shift on flat areas (mask=0).

    Returns
    -------
    np.ndarray
        uint8 RGB, same shape as input.
    """
    del seed
    _validate_inputs(image, r_shift, b_shift)

    rs = _clamp_shift(r_shift)
    bs = _clamp_shift(b_shift)

    r_shifted = _shift_channel(image[..., 0], rs)
    g = image[..., 1].copy()
    b_shifted = _shift_channel(image[..., 2], bs)

    if detail_mask is not None:
        m = detail_mask.astype(np.float32)
        r = (image[..., 0].astype(np.float32) * (1.0 - m)
             + r_shifted.astype(np.float32) * m)
        b = (image[..., 2].astype(np.float32) * (1.0 - m)
             + b_shifted.astype(np.float32) * m)
        return np.stack([
            np.clip(r, 0, 255).astype(np.uint8),
            g,
            np.clip(b, 0, 255).astype(np.uint8),
        ], axis=-1)

    return np.stack([r_shifted, g, b_shifted], axis=-1)
