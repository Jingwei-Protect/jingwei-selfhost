"""Anchor-rectified screenshot-robust JW channel.

Why
---
The frequency / QIM watermark layers (`core.jingwei_protocol`) decode only when
the pixel grid still matches embed time.  A screenshot resamples to an unknown
*continuous* scale, crops at an arbitrary offset and sometimes rotates slightly,
so the lattice drifts and decoding collapses ("一截图就完全读不到了").

This module adds a self-synchronising channel:

1. **Faint visible anchors** — four low-contrast center-surround fiducials are
   stamped on the luminance (Y) channel, at the four corners of an inner
   rectangle, so the matched-filter detector locks regardless of image colour.
2. **Canonical frame** — the four anchors *define* a coordinate system.  At
   verify time we detect them, solve a homography from the (scaled / cropped /
   rotated) screenshot back to a fixed canonical grid, and warp.  Scale, crop
   offset and rotation are fully undone — no blind scale sweep needed.
3. **Redundant low-frequency payload** — a compact record is written as a
   ``GRID×GRID`` mean-**chroma** (Cr) pattern between the anchors with heavy
   repetition + checksum, so JPEG re-encode and downscaling survive.  Chroma is
   chosen because the eye tolerates a far larger red-green shift than the same
   brightness shift, so the mark stays decode-survivable while hard to see.

The compact record carries the screenshot-critical core.  Two record layouts
share the same grid:
  * the declaration record (creation type + restriction flags), and
  * a 24-bit **traceability** record = a 16-bit fingerprint of (artist identity +
    timestamp), independent of the JW declaration (``embed_anchor_signature`` /
    ``verify_anchor_signature``).
A capacity sweep (social round-trip + screenshot) fixed 16 data bits as the
reliable ceiling, so the anchor stores only a digest; the full readable artist +
timestamp live in the existing frequency / LSB layers — no external storage.

Only requires numpy + opencv-python.
"""

from __future__ import annotations

import datetime
import hashlib

import cv2
import numpy as np

# ── Geometry ────────────────────────────────────────────────────────────
_INSET = 0.10            # anchor-center inset from each edge (fraction of W/H)
_GRID = 40               # payload cells per side between the anchors
_CANON = 800             # canonical warp size (px) for the inner grid region
_ANCHOR_MIN_EDGE = 128   # embed + detect both no-op below this (grid too coarse)
_ANCHOR_R_RATIO = 0.018  # anchor radius as fraction of image short side
                         # (smallest that keeps clean imgs 100% + textured ~85%
                         # under the screenshot sim; smaller collapses textured)


def anchor_size_ok(image: np.ndarray) -> bool:
    """True when the image is large enough for anchor embed / verify."""
    if image.ndim < 2:
        return False
    h, w = image.shape[:2]
    return min(h, w) >= _ANCHOR_MIN_EDGE

# ── Strength ────────────────────────────────────────────────────────────
# Anchors stay on luminance (needed for robust matched-filter detection).
# The PAYLOAD rides the Cr chroma channel: the eye is far less sensitive to a
# faint red-green shift than to the same brightness shift, so we can keep a
# decode-survivable amplitude while the mark is much harder to see.
_ANCHOR_DELTA = 38.0     # peak center-surround amplitude (busy/textured corners)
_ANCHOR_DELTA_MIN = 4.0  # amplitude used on flat corners (detection is easy there,
                         # and a faint blob there is what the eye notices most)
_ANCHOR_AMP_FLOOR = 2.5  # never go below this — a flat/bright corner still needs
                         # enough signal for the matched filter to lock
_ANCHOR_RING = 0.6       # negative-ring strength vs center (needed for the matched
                         # filter to reject content blobs — do not lower)
_ANCHOR_FADE = 0.55      # global anchor-amplitude multiplier. The improved
                         # detector decodes well below the old level, so anchors
                         # ride at ~55% strength — visibly fainter, social
                         # round-trip still 4/4 on every test image.
_ANCHOR_MATCH_SCALES = (0.8, 1.0, 1.25)  # radii (×r) tried by the matched filter
                         # so detection survives the unknown screenshot/social
                         # rescale; per-pixel max over scales is kept.
_ANCHOR_FEATHER = 0.18   # Gaussian feather of the disk/ring edge as a fraction of
                         # r (softens the hard edge the eye catches; the detector
                         # template is feathered identically so detection holds).
                         # 0.18 = max softening that keeps social round-trip 4/4
                         # on every test image, incl. the hardest texture one.
_PAYLOAD_DELTA = 6.0     # peak per-cell Cr (chroma) shift for payload bits
                         # (faintest full-frame amplitude that still survives a
                         # social round-trip on all test imgs; below 6 textured
                         # images cliff-dive. PSNR ~40 vs ~32 at the old 17.)
_PAYLOAD_FLOOR = 0.14    # min fraction of peak kept in flat regions
_SEAL_CR_DELTA = 16.0    # peak per-cell Cr (textured seal corner — texture hides it)
_SEAL_CR_MIN = 4.0       # per-cell Cr on a FLAT seal corner (faint, still decodes —
                         # a color block on a flat field is what the eye catches)
_SEAL_Y_DELTA = 3.0      # luma component on LIGHT corners (chroma does the work)
_SEAL_Y_DARK = 16.0      # luma component on NEAR-BLACK corners (chroma is lost)
_SEAL_FRAC = 0.22        # plate side as a fraction of the inner (anchor) rect
_SEAL_GRID = 12          # cells per side inside the seal (more votes/bit)
_SEAL_MARGIN = 0.035     # gap between plate and the corner/anchor (inner frac)
_SEAL_BORDER = 0.10      # border thickness as fraction of the plate side
_SEAL_CAP = 0.20         # caption-bar height as fraction of the plate side
_PN_SEED = 0x4A57        # fixed PN sequence seed (embed + decode must match)
_SEAL_PN_SEED = 0x7C19   # separate PN for the compact seal grid


def _pn_sequence(n: int) -> np.ndarray:
    """Fixed ±1 pseudo-random whitening sequence shared by embed and decode."""
    rng = np.random.default_rng(_PN_SEED)
    return rng.choice(np.array([-1.0, 1.0], dtype=np.float32), size=n)

# ── Record layout (16 bits) ─────────────────────────────────────────────
# Keep the screenshot-survivable record tiny so each bit is repeated across
# ~100 grid cells (SNR scales with cells-per-bit). The full manifest stays in
# the frequency / LSB layers; here we carry only the verify-critical core.
#   bits  0-3 : marker (0b1010)
#   bits  4-5 : creation (0=OC, 1=AI)
#   bits  6-11: restrictions (6 low bits)
#   bits 12-15: checksum (xor nibble of the first 12 bits)
_RECORD_BITS = 16
_MARKER_NIB = 0b1010


def _rgb_to_y(image: np.ndarray) -> np.ndarray:
    f = image.astype(np.float32)
    return 0.299 * f[:, :, 0] + 0.587 * f[:, :, 1] + 0.114 * f[:, :, 2]


def _add_luma(image: np.ndarray, dy: np.ndarray) -> np.ndarray:
    """Add a luminance delta map to an RGB image (chroma preserved)."""
    out = image.astype(np.float32) + dy[:, :, np.newaxis]
    return np.clip(out, 0, 255).astype(np.uint8)


def _rgb_to_cr(image: np.ndarray) -> np.ndarray:
    """Return the Cr (red-difference) chroma channel as float32."""
    ycc = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb)
    return ycc[:, :, 1].astype(np.float32)


def _add_luma_and_chroma(image: np.ndarray, dy: np.ndarray, dcr: np.ndarray) -> np.ndarray:
    """Add a luma delta (Y) and a chroma delta (Cr) to an RGB image."""
    ycc = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb).astype(np.float32)
    ycc[:, :, 0] = np.clip(ycc[:, :, 0] + dy, 0, 255)
    ycc[:, :, 1] = np.clip(ycc[:, :, 1] + dcr, 0, 255)
    return cv2.cvtColor(ycc.astype(np.uint8), cv2.COLOR_YCrCb2RGB)


# ── Record codec ────────────────────────────────────────────────────────

def _int_to_bits(value: int, n: int) -> np.ndarray:
    return np.array([(value >> (n - 1 - i)) & 1 for i in range(n)], dtype=np.uint8)


def _bits_to_int(bits: np.ndarray) -> int:
    v = 0
    for b in bits:
        v = (v << 1) | int(b)
    return v


def _record_checksum(body: np.ndarray) -> int:
    v = _bits_to_int(body)
    return (v ^ (v >> 4) ^ (v >> 8)) & 0xF


def encode_anchor_record(creation: int, restrictions: int) -> np.ndarray:
    """Pack the verify-critical core into a 16-bit array."""
    body = np.concatenate([
        _int_to_bits(_MARKER_NIB, 4),
        _int_to_bits(creation & 0b11, 2),
        _int_to_bits(restrictions & 0b111111, 6),
    ])
    chk = _record_checksum(body)
    return np.concatenate([body, _int_to_bits(chk, 4)]).astype(np.uint8)


def decode_anchor_record(bits: np.ndarray) -> dict | None:
    """Decode a 16-bit array back to the core record, or None if invalid."""
    bits = np.asarray(bits, dtype=np.uint8)[:_RECORD_BITS]
    if bits.size < _RECORD_BITS:
        return None
    if _bits_to_int(bits[:4]) != _MARKER_NIB:
        return None
    body = bits[:12]
    if _record_checksum(body) != _bits_to_int(bits[12:16]):
        return None
    return {
        "creation": _bits_to_int(bits[4:6]),
        "restrictions": _bits_to_int(bits[6:12]),
    }


# ── Work-ID record (traceability anchor, independent of the JW declaration) ──
# The screenshot-survivable anchor reliably carries ~16 DATA bits (validated by
# a social-round-trip + screenshot capacity sweep: 16 data bits decoded 100% on
# every test image, while 20+ bits started failing). So the traceability anchor
# carries a compact 16-bit Work-ID and nothing else. The full artist identity
# and an exact timestamp live in the local registry (api side), keyed by this
# ID — the same soft-binding pattern C2PA/Content-Credentials use. This keeps
# the mark independent of the精卫 declaration: a user can track their own work
# without ever turning the JW declaration on.
#   bits  0-3 : marker (0b1010)
#   bits  4-19: 16-bit Work-ID
#   bits 20-23: 4-bit checksum (folds ALL 20 body bits)
_WORKID_BITS = 16
_WORKID_RECORD_BITS = 4 + _WORKID_BITS + 4  # 24 — the proven-reliable record size


def _fold_checksum4(body: np.ndarray) -> int:
    """4-bit checksum that XOR-folds every nibble of the body (covers all bits)."""
    v = _bits_to_int(body)
    c = 0
    while v:
        c ^= v & 0xF
        v >>= 4
    return c & 0xF


def encode_workid_record(work_id: int) -> np.ndarray:
    """Pack a 16-bit Work-ID into the 24-bit traceability record."""
    wid = int(work_id) & ((1 << _WORKID_BITS) - 1)
    body = np.concatenate([
        _int_to_bits(_MARKER_NIB, 4),
        _int_to_bits(wid, _WORKID_BITS),
    ])
    chk = _fold_checksum4(body)
    return np.concatenate([body, _int_to_bits(chk, 4)]).astype(np.uint8)


def decode_workid_record(bits: np.ndarray) -> dict | None:
    """Decode the 24-bit traceability record → {"work_id": int} or None."""
    bits = np.asarray(bits, dtype=np.uint8)[:_WORKID_RECORD_BITS]
    if bits.size < _WORKID_RECORD_BITS:
        return None
    if _bits_to_int(bits[:4]) != _MARKER_NIB:
        return None
    body = bits[:4 + _WORKID_BITS]
    if _fold_checksum4(body) != _bits_to_int(bits[4 + _WORKID_BITS:_WORKID_RECORD_BITS]):
        return None
    return {"work_id": _bits_to_int(bits[4:4 + _WORKID_BITS])}


def anchor_fingerprint(artist: str, created_at: str | int | None = None) -> int:
    """Derive a 16-bit fingerprint from artist identity + timestamp.

    No storage: the FULL artist string + exact timestamp are embedded directly in
    the invisible signature layers (LSB / frequency), which survive copy / resave
    / format change. A screenshot strips those, but this compact 16-bit digest
    rides the screenshot-robust anchor — enough to *verify* a claimed
    (artist, timestamp) pair, not to print it. It deliberately does not depend on
    the JW declaration, so tracking works with the declaration off.
    """
    a = (artist or "").strip().lower()
    t = "" if created_at is None else str(created_at).strip()
    digest = hashlib.sha256(f"jw-anchor\x1f{a}\x1f{t}".encode("utf-8")).digest()
    return int.from_bytes(digest[:2], "big") & ((1 << _WORKID_BITS) - 1)


# ── Tracking payload: 10-bit artist code + 6-bit year-month ─────────────────
# Chosen split for the 16-bit screenshot-survivable budget:
#   bits 6-15 (10) : artist code  — top 10 bits of sha256(artist) → ~1024 buckets
#   bits 0-5  ( 6) : year-month   — absolute month index mod 64 (sliding ~5.3y
#                    window; the decoder resolves it to the most recent matching
#                    real year-month at or before the verification time).
# A screenshot thus still yields "artist code + year-month"; the full readable
# name and exact timestamp remain in the invisible signature layers.
_ANCHOR_ARTIST_BITS = 10
_ANCHOR_YM_BITS = 6
_YM_BASE_YEAR = 2000  # arbitrary fixed base for the absolute month index


def artist_code(artist: str) -> int:
    """10-bit code identifying an artist string (same input → same code)."""
    a = (artist or "").strip().lower()
    digest = hashlib.sha256(f"jw-artist\x1f{a}".encode("utf-8")).digest()
    return int.from_bytes(digest[:2], "big") & ((1 << _ANCHOR_ARTIST_BITS) - 1)


def _to_datetime(when: str | int | float | None) -> datetime.datetime:
    if when is None:
        return datetime.datetime.now()
    if isinstance(when, (int, float)):
        return datetime.datetime.fromtimestamp(float(when))
    s = str(when).strip()
    try:
        return datetime.datetime.fromisoformat(s)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y-%m", "%Y/%m/%d"):
            try:
                return datetime.datetime.strptime(s, fmt)
            except ValueError:
                continue
    return datetime.datetime.now()


def _month_index(dt: datetime.datetime) -> int:
    return (dt.year - _YM_BASE_YEAR) * 12 + (dt.month - 1)


def encode_anchor_tracking(artist: str, when: str | int | float | None = None) -> int:
    """Compose the 16-bit tracking payload (artist code << 6 | year-month code)."""
    acode = artist_code(artist)
    ym = _month_index(_to_datetime(when)) % (1 << _ANCHOR_YM_BITS)
    return ((acode << _ANCHOR_YM_BITS) | ym) & ((1 << _WORKID_BITS) - 1)


def decode_anchor_tracking(work_id: int, ref: str | int | float | None = None) -> dict:
    """Split a 16-bit tracking payload → {"artist_code", "year", "month"}.

    The 6-bit month wraps every 64 months, so we resolve it to the most recent
    real year-month at or before ``ref`` (default: verification time)."""
    acode = (int(work_id) >> _ANCHOR_YM_BITS) & ((1 << _ANCHOR_ARTIST_BITS) - 1)
    ym = int(work_id) & ((1 << _ANCHOR_YM_BITS) - 1)
    ref_idx = _month_index(_to_datetime(ref))
    period = 1 << _ANCHOR_YM_BITS
    abs_idx = ref_idx - ((ref_idx - ym) % period)  # newest match ≤ ref
    return {
        "artist_code": acode,
        "year": _YM_BASE_YEAR + abs_idx // 12,
        "month": abs_idx % 12 + 1,
    }


# ── Anchor stamping ─────────────────────────────────────────────────────

def _anchor_centers(w: int, h: int) -> np.ndarray:
    """Return the 4 anchor centers (px) as TL, TR, BR, BL (clockwise)."""
    x0, x1 = _INSET * w, (1 - _INSET) * w
    y0, y1 = _INSET * h, (1 - _INSET) * h
    return np.array(
        [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float32
    )


def _anchor_amps_at(image: np.ndarray, cx: float, cy: float,
                    r: float) -> tuple[float, float]:
    """Separate amplitudes for the anchor's bright CENTER and dark RING.

    The matched filter is amplitude-invariant, so a *flat* corner locks even at a
    low amplitude. The base amplitude follows local texture: low on smooth fields
    (where a faint blob is most noticed and detection is easy) and full on busy
    fields (which both demand more signal and hide the mark).

    On top of that the center and ring are damped **asymmetrically by background
    luma**, because the visible half differs with the backdrop:
      * **dark field** → the bright *center* glows like a little lamp; damp the
        CENTER. The dark ring stays — it is invisible on dark content and carries
        the detection signal.
      * **bright/pale field** → the dark *ring* is the "soap-bubble" eyesore;
        damp the RING (gated by flatness, since busy bright content hides it).
        The bright center stays — on a pale field it clips toward white and is
        far less visible, and it carries the detection signal.
    Bright (mean>158) and dark (mean<96) ranges never overlap, so at most ONE
    half is ever damped; the other keeps full base amplitude. The symmetric
    detector template still correlates positively with a center- or ring-heavy
    stamp, so detection holds.
    """
    h, w = image.shape[:2]
    r_out = int(r * 1.9)
    x0 = max(0, int(cx - r_out)); x1 = min(w, int(cx + r_out) + 1)
    y0 = max(0, int(cy - r_out)); y1 = min(h, int(cy + r_out) + 1)
    region = _rgb_to_y(image[y0:y1, x0:x1])
    std = float(region.std()) if region.size else 0.0
    mean = float(region.mean()) if region.size else 128.0
    texture = float(np.clip(std / 14.0, 0.0, 1.0))  # ~14 luma std → full strength
    base = _ANCHOR_DELTA_MIN + (_ANCHOR_DELTA - _ANCHOR_DELTA_MIN) * texture
    flat = 1.0 - texture
    bright = float(np.clip((mean - 158.0) / 97.0, 0.0, 1.0))   # 0 @<=158, 1 @255
    dark = float(np.clip((96.0 - mean) / 96.0, 0.0, 1.0))      # 0 @>=96, 1 @0
    center = base * (1.0 - 0.88 * dark)
    ring = base * _ANCHOR_RING * (1.0 - 0.80 * bright * flat)
    center = max(_ANCHOR_AMP_FLOOR, center)
    ring = max(_ANCHOR_AMP_FLOOR * _ANCHOR_RING, ring)
    # Global fade: the stronger detector (high-pass + multi-scale matched filter
    # + fixed-inset fallback, see _matched_response / extract) keeps decoding far
    # below the old amplitude, so we trade that headroom for a much fainter mark.
    return center * _ANCHOR_FADE, ring * _ANCHOR_FADE


def _center_surround_stamp(dy: np.ndarray, cx: float, cy: float, r: float,
                           center_amp: float = _ANCHOR_DELTA,
                           ring_amp: float | None = None) -> None:
    """Add a faint center-surround (positive disk + negative ring) onto dy.

    ``center_amp`` and ``ring_amp`` are set independently so the bright disk and
    dark ring can be damped asymmetrically by background luma (see
    ``_anchor_amps_at``). If ``ring_amp`` is omitted it falls back to the fixed
    symmetric ratio.
    """
    if ring_amp is None:
        ring_amp = center_amp * _ANCHOR_RING
    h, w = dy.shape
    r_out = r * 1.9
    x0 = max(0, int(cx - r_out)); x1 = min(w, int(cx + r_out) + 1)
    y0 = max(0, int(cy - r_out)); y1 = min(h, int(cy + r_out) + 1)
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    patch = np.zeros_like(dist)
    patch[dist <= r] = center_amp
    ring = (dist > r) & (dist <= r_out)
    patch[ring] = -ring_amp
    # Feather the hard disk/ring edges: a crisp boundary is what the eye locks
    # onto (worst on dark fields). The detector template gets the SAME blur so
    # the matched filter stays aligned.
    patch = cv2.GaussianBlur(patch, (0, 0), sigmaX=max(0.6, r * _ANCHOR_FEATHER))
    dy[y0:y1, x0:x1] += patch


def _payload_cell_mask(region: str) -> np.ndarray:
    """Boolean (GRID×GRID) map of which cells carry payload, by region mode.

    Shared by embed and decode so the global PN/bit indexing stays consistent.
      * ``full`` — whole inner rectangle (max redundancy, max coverage).
      * ``band`` — bottom strip only; the main artwork above stays untouched.
      * ``seal`` — a small bottom-right square ("stamp"); rest fully clean.
    """
    m = np.zeros((_GRID, _GRID), dtype=bool)
    if region == "band":
        m[int(_GRID * 0.76):, :] = True
    elif region == "seal":
        s = max(6, int(_GRID * 0.34))
        m[_GRID - s:, _GRID - s:] = True
    else:  # full
        m[:] = True
    return m


def _payload_grid_delta(w: int, h: int, payload_bits: np.ndarray,
                        region: str = "full", amp: float | None = None) -> np.ndarray:
    """Build a spread-spectrum chroma-delta map carrying payload bits.

    Each cell i encodes bit ``i % n`` as ``±amp``, multiplied by a fixed ±1 PN
    value.  Because the PN flips signs pseudo-randomly, smooth image content
    averages out at decode while the payload (which used the same PN) reinforces
    — a large processing gain at very low per-cell amplitude.  Cells outside the
    selected ``region`` are left at zero (the decode skips them too).
    """
    amp = _PAYLOAD_DELTA if amp is None else amp
    dy = np.zeros((h, w), dtype=np.float32)
    x0, x1 = _INSET * w, (1 - _INSET) * w
    y0, y1 = _INSET * h, (1 - _INSET) * h
    n = payload_bits.size
    pn = _pn_sequence(_GRID * _GRID)
    cell_on = _payload_cell_mask(region)
    k = 0
    for r in range(_GRID):
        cy0 = int(round(y0 + (y1 - y0) * r / _GRID))
        cy1 = int(round(y0 + (y1 - y0) * (r + 1) / _GRID))
        for c in range(_GRID):
            cx0 = int(round(x0 + (x1 - x0) * c / _GRID))
            cx1 = int(round(x0 + (x1 - x0) * (c + 1) / _GRID))
            if cell_on[r, c]:
                bsign = 1.0 if int(payload_bits[k % n]) else -1.0
                dy[cy0:cy1, cx0:cx1] += bsign * pn[k] * amp
            k += 1
    return dy


def _seal_pn(n: int) -> np.ndarray:
    rng = np.random.default_rng(_SEAL_PN_SEED)
    return rng.choice(np.array([-1.0, 1.0], dtype=np.float32), size=n)


def _seal_geom() -> dict[str, tuple[float, float, float, float]]:
    """Seal layout in *inner-rect-normalised* coords (0..1 within anchor rect).

    Same fractions are used at embed (mapped to image px) and decode (mapped to
    the square canonical frame), so the data grid always lines up.  The plate is
    inset from the corner by a margin so it never collides with the BR anchor.
    """
    p, m = _SEAL_FRAC, _SEAL_MARGIN
    pu1 = 1.0 - m; pu0 = pu1 - p
    pv1 = 1.0 - m; pv0 = pv1 - p
    b = _SEAL_BORDER * p
    cap = _SEAL_CAP * p
    return {
        "plate": (pu0, pv0, pu1, pv1),
        "data": (pu0 + b, pv0 + b, pu1 - b, pv1 - b - cap),
        "cap": (pu0 + b, pv1 - b - cap, pu1 - b, pv1 - b),
    }


def _inner_px(u: float, v: float, w: int, h: int) -> tuple[int, int]:
    """Map inner-rect-normalised (u,v) to image pixel coords."""
    span = 1.0 - 2.0 * _INSET
    return int(round((_INSET + u * span) * w)), int(round((_INSET + v * span) * h))


def _seal_data_rect_px(w: int, h: int) -> tuple[int, int, int, int]:
    du0, dv0, du1, dv1 = _seal_geom()["data"]
    x0, y0 = _inner_px(du0, dv0, w, h)
    x1, y1 = _inner_px(du1, dv1, w, h)
    return x0, y0, x1, y1


def _seal_feather(w: int, h: int) -> np.ndarray:
    """Soft [0,1] window over the data rect: ~1 inside, tapering to 0 at the
    edges so the stamp has no hard square boundary (no frame, no label)."""
    x0, y0, x1, y1 = _seal_data_rect_px(w, h)
    m = np.zeros((h, w), dtype=np.float32)
    m[y0:y1, x0:x1] = 1.0
    # Feather only the outer rim (~half a cell) so interior cell seams stay crisp.
    sigma = max(2.0, (x1 - x0) / _SEAL_GRID * 0.5)
    return cv2.GaussianBlur(m, (0, 0), sigmaX=sigma)


def _seal_luma_amp(image: np.ndarray) -> float:
    """Adaptive luma amplitude for the seal, by the seal region's brightness.

    Chroma cannot be represented on near-black pixels (a Cr shift round-trips
    back to black), so a chroma-only seal vanishes on dark backgrounds.  We add
    just enough luma to carry the bits where the corner is dark, and almost none
    where it is light (there chroma alone hides the mark)."""
    h, w = image.shape[:2]
    x0, y0, x1, y1 = _seal_data_rect_px(w, h)
    ym = float(_rgb_to_y(image[y0:y1, x0:x1]).mean())
    # ym >= 140 (light) → small luma; ym <= 30 (near-black) → strong luma.
    t = float(np.clip((140.0 - ym) / 110.0, 0.0, 1.0))
    return _SEAL_Y_DELTA + (_SEAL_Y_DARK - _SEAL_Y_DELTA) * t


def _seal_cr_amp(image: np.ndarray) -> float:
    """Adaptive chroma amplitude for the seal, by the seal region's texture.

    The decode is sign-based (amplitude-invariant), so on a FLAT corner the grid
    decodes from a tiny Cr shift — and a flat field is exactly where a colour
    block is most visible. So we use a faint chroma there and the full amplitude
    only on busy corners, where detail both hides the grid and demands more
    signal."""
    h, w = image.shape[:2]
    x0, y0, x1, y1 = _seal_data_rect_px(w, h)
    region = _rgb_to_y(image[y0:y1, x0:x1])
    std = float(region.std()) if region.size else 0.0
    t = float(np.clip(std / 14.0, 0.0, 1.0))   # ~14 luma std → full strength
    return _SEAL_CR_MIN + (_SEAL_CR_DELTA - _SEAL_CR_MIN) * t


def _stamp_seal(dy: np.ndarray, dcr: np.ndarray, bits: np.ndarray,
                image: np.ndarray) -> None:
    """Stamp the compact seal grid into the data sub-rect (luma+chroma).

    The same sign pattern goes into BOTH channels so decode can combine them:
    chroma carries it on light images, luma on dark ones."""
    h, w = dy.shape
    x0, y0, x1, y1 = _seal_data_rect_px(w, h)
    g = _SEAL_GRID
    pn = _seal_pn(g * g)
    n = bits.size
    y_amp = _seal_luma_amp(image)
    cr_amp = _seal_cr_amp(image)
    k = 0
    for r in range(g):
        cy0 = int(round(y0 + (y1 - y0) * r / g))
        cy1 = int(round(y0 + (y1 - y0) * (r + 1) / g))
        for c in range(g):
            cx0 = int(round(x0 + (x1 - x0) * c / g))
            cx1 = int(round(x0 + (x1 - x0) * (c + 1) / g))
            v = (1.0 if int(bits[k % n]) else -1.0) * pn[k]
            dcr[cy0:cy1, cx0:cx1] += v * cr_amp
            dy[cy0:cy1, cx0:cx1] += v * y_amp
            k += 1


def _grid_high_pass(chan: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> np.ndarray:
    """Per-cell mean of ``chan`` over the data rect, high-passed vs neighbours."""
    g = _SEAL_GRID
    means = np.zeros((g, g), dtype=np.float32)
    for r in range(g):
        ry0 = int(round(y0 + (y1 - y0) * r / g)); ry1 = int(round(y0 + (y1 - y0) * (r + 1) / g))
        for c in range(g):
            rx0 = int(round(x0 + (x1 - x0) * c / g)); rx1 = int(round(x0 + (x1 - x0) * (c + 1) / g))
            means[r, c] = float(chan[ry0:ry1, rx0:rx1].mean())
    bg = cv2.GaussianBlur(means, (0, 0), sigmaX=1.5)
    return (means - bg).ravel()


def _seal_decode(canon_img: np.ndarray) -> tuple[np.ndarray, float]:
    """Decode the seal record (bits, confidence) from the canonical frame.

    Chroma and luma each carry the same sign pattern. We PN-despread EACH
    channel separately and majority-vote per bit, then sum the two votes. PN
    despreading cancels image content in both channels, so a content-heavy but
    signal-free channel contributes ~0 — the channel that actually holds the
    mark (chroma on light corners, luma on dark) decides the sign.
    """
    cs = canon_img.shape[0]
    du0, dv0, du1, dv1 = _seal_geom()["data"]
    x0 = int(round(du0 * cs)); x1 = int(round(du1 * cs))
    y0 = int(round(dv0 * cs)); y1 = int(round(dv1 * cs))
    pn = _seal_pn(_SEAL_GRID * _SEAL_GRID)
    nbits = _RECORD_BITS
    total = np.zeros(nbits, dtype=np.float64)
    mag = 0.0
    for chan, amp in ((_rgb_to_cr(canon_img), _SEAL_CR_DELTA),
                      (_rgb_to_y(canon_img), _SEAL_Y_DARK)):
        hi = _grid_high_pass(chan, x0, y0, x1, y1)
        despread = hi * pn[:hi.size]
        acc = np.zeros(nbits, dtype=np.float64)
        cnt = np.zeros(nbits, dtype=np.float64)
        for i in range(hi.size):
            bi = i % nbits
            acc[bi] += despread[i]; cnt[bi] += 1
        avg = acc / np.maximum(cnt, 1)
        total += avg / amp          # normalise by embed amplitude, then sum
        mag += float(np.mean(np.abs(avg)) / amp)
    bits = (total > 0).astype(np.uint8)
    return bits, float(np.clip(mag, 0.0, 1.0))


def _texture_mask(image: np.ndarray) -> np.ndarray:
    """Per-pixel [~0,1] map: ~1 in busy mid-tone regions, ~0 in flat/dark/bright.

    Two human-vision facts drive this:
      * **Texture masking** — color noise hides in busy detail but stands out on
        flat fields, so we damp where local luma std is low.
      * **Luminance masking** — a faint chroma block is very visible on a near
        *black* field (and on blown-out highlights), so we also damp the very
        dark and very bright pixels.
    The payload therefore concentrates in textured mid-tones, where the eye
    cannot separate it from real detail — and there is plenty of it to decode.
    """
    y = _rgb_to_y(image)
    mean = cv2.GaussianBlur(y, (0, 0), sigmaX=3.0)
    mean_sq = cv2.GaussianBlur(y * y, (0, 0), sigmaX=3.0)
    std = np.sqrt(np.clip(mean_sq - mean * mean, 0.0, None))
    texture = np.clip(std / 10.0, 0.0, 1.0)  # ~10 luma std → full strength

    # Luminance window: damp only the *near-black* background, where a faint
    # chroma block is most visible, without starving mid-dark textured detail.
    dark = np.clip((mean - 4.0) / 16.0, 0.0, 1.0)
    luma_win = _PAYLOAD_FLOOR + (1.0 - _PAYLOAD_FLOOR) * dark

    mask = (_PAYLOAD_FLOOR + (1.0 - _PAYLOAD_FLOOR) * texture) * luma_win
    return mask.astype(np.float32)


def embed_anchor_watermark(image: np.ndarray, payload_bits: np.ndarray,
                           region: str = "full") -> np.ndarray:
    """Stamp faint luma anchors + a redundant chroma-grid payload (RGB uint8).

    The payload rides the Cr chroma channel (low human sensitivity → less
    visible); the four corner anchors stay on luma so the matched-filter
    detector locks regardless of the image's colours.

    ``region`` controls where the payload lives:
      * ``full`` — spread over the whole inner rectangle (default; max robust).
      * ``band`` — confined to a bottom strip; the main artwork stays clean.
      * ``seal`` — a small, deliberately-visible bottom-right stamp; the rest of
        the artwork is untouched.
    """
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Input must be uint8 HxWx3 RGB.")
    h, w = image.shape[:2]
    if min(h, w) < _ANCHOR_MIN_EDGE:
        return image.copy()

    bits = np.asarray(payload_bits, dtype=np.uint8)
    dy = np.zeros((h, w), dtype=np.float32)

    if region == "seal":
        # A compact, soft corner stamp — no frame, no label. Its OWN coarse data
        # grid (big cells survive JPEG/resample even when small) is feathered at
        # the edges so it fades into the artwork instead of showing a hard block.
        dcr = np.zeros((h, w), dtype=np.float32)
        _stamp_seal(dy, dcr, bits, image)
        soft = _seal_feather(w, h)
        dcr *= soft
        dy *= soft
        dcr = cv2.GaussianBlur(dcr, (0, 0), sigmaX=0.8)
        dy = cv2.GaussianBlur(dy, (0, 0), sigmaX=0.8)
        r = max(6.0, _ANCHOR_R_RATIO * min(h, w))
        for cx, cy in _anchor_centers(w, h):
            ca, ra = _anchor_amps_at(image, cx, cy, r)
            _center_surround_stamp(dy, cx, cy, r, ca, ra)
        return _add_luma_and_chroma(image, dy, dcr)
    elif region == "band":
        dcr = _payload_grid_delta(w, h, bits, region=region, amp=_SEAL_CR_DELTA)
        dlu = _payload_grid_delta(w, h, bits, region=region, amp=_SEAL_Y_DELTA)
        dcr = cv2.GaussianBlur(dcr, (0, 0), sigmaX=0.8)
        dy += cv2.GaussianBlur(dlu, (0, 0), sigmaX=0.8)
    else:
        dcr = _payload_grid_delta(w, h, bits, region=region)
        # Hide color blocks in texture: damp the chroma payload in flat regions
        # (most visible, least needed) and keep full strength in busy regions.
        # Scaling only changes MAGNITUDE (>=0), so the bit SIGN — and the
        # sign-based decode — is preserved; dense repetition tolerates low SNR.
        dcr *= _texture_mask(image)
        dcr = cv2.GaussianBlur(dcr, (0, 0), sigmaX=1.0)

    r = max(6.0, _ANCHOR_R_RATIO * min(h, w))
    for cx, cy in _anchor_centers(w, h):
        ca, ra = _anchor_amps_at(image, cx, cy, r)
        _center_surround_stamp(dy, cx, cy, r, ca, ra)

    return _add_luma_and_chroma(image, dy, dcr)


# ── Anchor detection + rectification ────────────────────────────────────

def _anchor_template(r: float) -> np.ndarray:
    """Synthetic center-surround template matching the stamped fiducial shape."""
    r_out = r * 1.9
    size = int(2 * r_out) + 1
    c = size / 2.0
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    dist = np.sqrt((xx - c) ** 2 + (yy - c) ** 2)
    t = np.zeros((size, size), dtype=np.float32)
    t[dist <= r] = 1.0
    t[(dist > r) & (dist <= r_out)] = -_ANCHOR_RING
    # Match the feather applied to the stamped fiducial (see _center_surround_stamp).
    t = cv2.GaussianBlur(t, (0, 0), sigmaX=max(0.6, r * _ANCHOR_FEATHER))
    return t


def _matched_response(gray: np.ndarray, r: float) -> np.ndarray:
    """Shape-matched (not magnitude) correlation with the fiducial template.

    ``TM_CCOEFF_NORMED`` rejects high-contrast content edges that don't share the
    disk-plus-ring shape, so the faint anchors win over busy image texture.

    Two boosts let us keep locking onto FAINT anchors:
      * **High-pass prefilter** — subtract a blurred copy to suppress the smooth
        image content the anchor is buried under, lifting the faint mark's
        relative response (a local whitening step).
      * **Multi-scale** — a screenshot/social re-encode resamples to an unknown
        scale, so the anchor's apparent radius drifts. We match at a few radii
        and keep the per-pixel max, so the lock survives that scale drift.
    """
    g = gray.astype(np.float32)
    hp = g - cv2.GaussianBlur(g, (0, 0), sigmaX=max(1.0, r * 1.6))
    full = None
    for scale in _ANCHOR_MATCH_SCALES:
        rr = max(4.0, r * scale)
        tmpl = _anchor_template(rr)
        resp = cv2.matchTemplate(hp, tmpl, cv2.TM_CCOEFF_NORMED)
        pad_y = (gray.shape[0] - resp.shape[0]) // 2
        pad_x = (gray.shape[1] - resp.shape[1]) // 2
        lvl = np.zeros_like(g)
        lvl[pad_y:pad_y + resp.shape[0], pad_x:pad_x + resp.shape[1]] = resp
        full = lvl if full is None else np.maximum(full, lvl)
    return full


def _peak_in_region(resp: np.ndarray, y0: int, y1: int, x0: int, x1: int) -> tuple[float, float, float]:
    """Return (x, y, value) of the max response within a sub-window.

    The location is refined to sub-pixel via a local response-weighted centroid
    around the argmax, which tightens homography accuracy.
    """
    sub = resp[y0:y1, x0:x1]
    idx = int(np.argmax(sub))
    ry, rx = np.unravel_index(idx, sub.shape)
    peak_val = float(sub[ry, rx])

    win = 4
    wy0 = max(0, ry - win); wy1 = min(sub.shape[0], ry + win + 1)
    wx0 = max(0, rx - win); wx1 = min(sub.shape[1], rx + win + 1)
    patch = sub[wy0:wy1, wx0:wx1].copy()
    patch = np.maximum(patch - patch.min(), 0.0)
    if patch.sum() > 1e-6:
        yy, xx = np.mgrid[wy0:wy1, wx0:wx1].astype(np.float32)
        cx = float((xx * patch).sum() / patch.sum())
        cy = float((yy * patch).sum() / patch.sum())
    else:
        cx, cy = float(rx), float(ry)
    return float(x0 + cx), float(y0 + cy), peak_val


def _nms_peaks(resp: np.ndarray, r: float, thresh: float = 0.12) -> np.ndarray:
    """All NMS local maxima above ``thresh`` as (x, y, val), sorted by val."""
    k = max(3, int(r * 1.2) | 1)
    dil = cv2.dilate(resp, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    peaks_mask = (resp >= dil) & (resp > thresh)
    ys, xs = np.nonzero(peaks_mask)
    if xs.size == 0:
        return np.empty((0, 3), dtype=np.float32)
    vals = resp[ys, xs]
    order = np.argsort(vals)[::-1]
    return np.stack([xs[order], ys[order], vals[order]], axis=1).astype(np.float32)


def _corner_candidate_groups(resp: np.ndarray, r: float,
                             per_corner: int = 6) -> list[np.ndarray]:
    """Top-N matched peaks within each of the 4 (generous) corner regions.

    One anchor lives in each corner, so we later try the cross-product (one
    pick per corner). Generous 48% regions tolerate crop/scale shifts while
    still isolating each anchor from busy content in the opposite corners.
    """
    h, w = resp.shape
    peaks = _nms_peaks(resp, r)
    if peaks.shape[0] == 0:
        return []
    qy, qx = int(h * 0.48), int(w * 0.48)
    regions = [
        (0, qy, 0, qx), (0, qy, w - qx, w),
        (h - qy, h, w - qx, w), (h - qy, h, 0, qx),
    ]
    expected = [
        (_INSET * w, _INSET * h), ((1 - _INSET) * w, _INSET * h),
        ((1 - _INSET) * w, (1 - _INSET) * h), (_INSET * w, (1 - _INSET) * h),
    ]
    px, py = peaks[:, 0], peaks[:, 1]
    groups: list[np.ndarray] = []
    for (y0, y1, x0, x1), (ex, ey) in zip(regions, expected):
        inside = (px >= x0) & (px < x1) & (py >= y0) & (py < y1)
        region_peaks = peaks[inside]
        if region_peaks.shape[0] == 0:
            return []
        grp = region_peaks[:per_corner]
        # Guarantee the peak nearest the expected inset position is a candidate
        # even if busy content outranks it (the textured-image failure mode).
        dists = np.hypot(region_peaks[:, 0] - ex, region_peaks[:, 1] - ey)
        near = region_peaks[int(np.argmin(dists))]
        if not np.any(np.all(grp[:, :2] == near[:2], axis=1)):
            grp = np.concatenate([grp, near[None, :]], axis=0)
        groups.append(grp)
    return groups


def _order_quad(pts: np.ndarray) -> np.ndarray:
    """Order 4 points as TL, TR, BR, BL."""
    c = pts.mean(axis=0)
    ang = np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0])
    # Start from top-left-ish (angle near -3π/4) going clockwise.
    idx = np.argsort(ang)
    p = pts[idx]
    # Rotate so the point with smallest (x+y) is first (TL).
    s = p[:, 0] + p[:, 1]
    start = int(np.argmin(s))
    return np.roll(p, -start, axis=0)


def _quad_score(quad: np.ndarray, conf: float, img_area: float, img_aspect: float,
                w: int, h: int) -> float:
    """Score a candidate quad by area + parallelogram-ness + aspect + response,
    plus a soft prior that corners sit near the canonical inset layout."""
    diag_err = np.linalg.norm((quad[0] + quad[2]) - (quad[1] + quad[3]))
    x = quad[:, 0]; y = quad[:, 1]
    area = 0.5 * abs(
        x[0] * y[1] - x[1] * y[0] + x[1] * y[2] - x[2] * y[1]
        + x[2] * y[3] - x[3] * y[2] + x[3] * y[0] - x[0] * y[3]
    )
    if area < 0.20 * img_area:
        return -1.0
    side = np.sqrt(area)
    para = 1.0 / (1.0 + diag_err / max(1.0, side))
    top = np.linalg.norm(quad[1] - quad[0])
    bot = np.linalg.norm(quad[2] - quad[3])
    left = np.linalg.norm(quad[3] - quad[0])
    right = np.linalg.norm(quad[2] - quad[1])
    wmean = (top + bot) / 2.0
    hmean = (left + right) / 2.0
    if hmean < 1.0:
        return -1.0
    quad_aspect = wmean / hmean
    aspect_match = 1.0 / (1.0 + abs(np.log((quad_aspect + 1e-6) / img_aspect)))
    # Soft position prior: corners near the canonical inset layout (TL..BL).
    # Tolerant enough for mild crop/scale; decisive when anchors are in place.
    expected = np.array([
        [_INSET * w, _INSET * h], [(1 - _INSET) * w, _INSET * h],
        [(1 - _INSET) * w, (1 - _INSET) * h], [_INSET * w, (1 - _INSET) * h],
    ], dtype=np.float32)
    diag = float(np.hypot(w, h))
    pos_err = float(np.mean(np.linalg.norm(quad - expected, axis=1))) / diag
    pos_prior = float(np.exp(-pos_err / 0.18))
    return (area / img_area) * (para ** 2) * aspect_match * (0.5 + conf) * (0.4 + pos_prior)


def _select_anchor_quad(groups: list[np.ndarray], w: int, h: int) -> np.ndarray | None:
    """Cross-product over corner groups (one pick per corner) → best rectangle."""
    if len(groups) != 4:
        return None
    from itertools import product

    img_area = float(w * h)
    img_aspect = w / float(h)
    best = None
    best_score = -1.0
    for tl, tr, br, bl in product(*groups):
        pts = np.array([tl[:2], tr[:2], br[:2], bl[:2]], dtype=np.float32)
        quad = _order_quad(pts)
        conf = float((tl[2] + tr[2] + br[2] + bl[2]) / 4.0)
        score = _quad_score(quad, conf, img_area, img_aspect, w, h)
        if score > best_score:
            best_score = score
            best = quad
    return best


def _inset_refined_quad(resp: np.ndarray, w: int, h: int, r: float) -> np.ndarray:
    """Quad built by refining the matched response at the CANONICAL inset corners.

    A social round-trip (resize + re-encode, no crop) keeps the full frame, so
    the anchors stay at their original relative inset. Locking locally at those
    known positions is near-free and extremely robust — it carries decoding even
    when the anchors are faded too far for the blind global search to pick them
    out of the content. Useless when the image is cropped (→ the global search
    quad covers that case); both are tried as candidates at decode.
    """
    exp = _anchor_centers(w, h)
    out = exp.copy().astype(np.float32)
    win = max(4, int(r * 2.0))
    for i, (px, py) in enumerate(exp):
        x0 = max(0, int(px - win)); x1 = min(w, int(px + win) + 1)
        y0 = max(0, int(py - win)); y1 = min(h, int(py + win) + 1)
        rx, ry, _ = _peak_in_region(resp, y0, y1, x0, x1)
        out[i] = [rx, ry]
    return out


def _lattice_search_quads(
    resp: np.ndarray, w: int, h: int, r: float, k: int = 32
) -> list[np.ndarray]:
    """Find the anchor rectangle as one object instead of four ranked corners.

    ``_corner_candidate_groups`` keeps the top ``per_corner`` matched peaks per
    corner. On busy content that ranking fails badly: on a textured photo the
    true anchor can sit at rank ~300 of ~640 peaks, because fur produces
    hundreds of stronger disk-plus-ring responses. Raising the cut is not an
    option, as the quad search is a cross-product over the groups.

    The four anchors are not independent though — they are the corners of a
    rectangle inset from the frame, so a symmetric crop shifts and rescales them
    together while preserving aspect. Searching (centre, half-width) directly
    and scoring by the *weakest* of the four corners exploits that: texture has
    to conspire at four specific places at once to beat a real anchor, which is
    far less likely than beating it at one.

    Scoring by the weakest corner narrows the field but does not win outright:
    on fur the best-scoring rectangle still lands ~30px off, while the decoder
    needs roughly 10px. So several high-scoring rectangles are returned rather
    than one. The record's marker and checksum reject a wrong lock, which is
    what makes trying alternatives cheap and safe rather than a false-positive
    risk.

    Returns up to ``k`` quads as TL, TR, BR, BL, best-scoring first.
    """
    tol = max(2, int(round(r * 0.3)))
    pooled = cv2.dilate(
        resp, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * tol + 1, 2 * tol + 1))
    )
    base_aspect = h / float(w)

    def _corners(cx, cy, a, fac: float, deg: float):
        """The four rotated corner coordinates, broadcast over the parameter grid."""
        b = a * base_aspect * fac
        t = np.deg2rad(deg)
        ct, st = np.cos(t), np.sin(t)
        out = []
        for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            ox, oy = dx * a, dy * b
            out.append((cx + ox * ct - oy * st, cy + ox * st + oy * ct))
        return out

    def _score(cxs: np.ndarray, cys: np.ndarray, halves: np.ndarray, fac: float,
               deg: float, sharp: bool = False):
        # The coarse pass reads the dilated map so a 4px grid can still find a
        # peak; the fine pass must read the raw response, or the pooling radius
        # becomes a floor on localisation accuracy and the decoder needs better
        # precision than that floor allows.
        src = resp if sharp else pooled
        cx = cxs[:, None, None].astype(np.float32)
        cy = cys[None, :, None].astype(np.float32)
        a = halves[None, None, :].astype(np.float32)
        corners = _corners(cx, cy, a, fac, deg)
        shape = np.broadcast_shapes(*[c[0].shape for c in corners],
                                    *[c[1].shape for c in corners])
        ok = np.ones(shape, dtype=bool)
        vals = []
        for xf, yf in corners:
            xb = np.broadcast_to(xf, shape)
            yb = np.broadcast_to(yf, shape)
            ok &= (xb >= 0) & (xb <= w - 1) & (yb >= 0) & (yb <= h - 1)
            vals.append(
                src[
                    np.clip(np.round(yb), 0, h - 1).astype(np.int32),
                    np.clip(np.round(xb), 0, w - 1).astype(np.int32),
                ]
            )
        # Second-weakest corner, not the weakest. Anchors fade unevenly: on the
        # textured photo one corner reads 0.27 while the opposite pair reads
        # 0.66+, and scoring on the single weakest lets that one faint corner
        # push the true rectangle below coincidental ones. Requiring three
        # strong corners keeps the discrimination without that sensitivity.
        s = np.partition(np.stack(vals, axis=0), 1, axis=0)[1]
        return np.where(ok, s, -1.0)

    # Uncropped the half-width is (0.5 - _INSET)·w; cropping by f raises the
    # ratio to (0.5 - _INSET)/(1 - f), so this span covers crops to about 25%.
    lo, hi = (0.5 - _INSET) * w * 0.92, (0.5 - _INSET) * w / 0.75
    pool: list[tuple[float, float, float, float, float, float]] = []
    for fac in (0.92, 1.0, 1.09):
        for deg in (-2.0, -1.0, 0.0, 1.0, 2.0):
            cxs = np.arange(0.38 * w, 0.62 * w + 1, 4)
            cys = np.arange(0.38 * h, 0.62 * h + 1, 4)
            halves = np.arange(lo, hi + 1, 4)
            if cxs.size == 0 or cys.size == 0 or halves.size == 0:
                continue
            s = _score(cxs, cys, halves, fac, deg)
            flat = s.ravel()
            take = min(flat.size, 200)
            idx = np.argpartition(flat, -take)[-take:]
            for i in idx:
                if flat[i] <= 0.0:
                    continue
                ix, iy, ia = np.unravel_index(int(i), s.shape)
                pool.append(
                    (float(flat[i]), float(cxs[ix]), float(cys[iy]),
                     float(halves[ia]), fac, deg)
                )

    if not pool:
        return []
    pool.sort(key=lambda t: -t[0])

    # Suppress near-duplicates in parameter space so the k slots hold genuinely
    # different rectangles instead of one peak sampled k times.
    picked: list[tuple[float, float, float, float, float, float]] = []
    for cand in pool:
        if all(
            abs(cand[1] - p[1]) >= 8 or abs(cand[2] - p[2]) >= 8
            or abs(cand[3] - p[3]) >= 8 or cand[5] != p[5]
            for p in picked
        ):
            picked.append(cand)
        if len(picked) >= k:
            break

    out: list[np.ndarray] = []
    for _, cx0, cy0, a0, fac, deg0 in picked:
        cxs = np.arange(cx0 - 5, cx0 + 5.5, 1.0)
        cys = np.arange(cy0 - 5, cy0 + 5.5, 1.0)
        halves = np.arange(a0 - 5, a0 + 5.5, 1.0)
        best_fine = None
        best_v = -np.inf
        # The coarse angle step is 1 degree, which leaves up to half a degree of
        # residual tilt — enough corner error on a 900px frame to miss the grid.
        for deg in (deg0 - 0.5, deg0, deg0 + 0.5):
            s = _score(cxs, cys, halves, fac, deg, sharp=True)
            i = int(np.argmax(s))
            if float(s.flat[i]) > best_v:
                best_v = float(s.flat[i])
                ix, iy, ia = np.unravel_index(i, s.shape)
                best_fine = (float(cxs[ix]), float(cys[iy]), float(halves[ia]), deg)
        if best_fine is None:
            continue
        cx, cy, a, deg = best_fine
        out.append(
            np.array(
                [
                    [float(x), float(y)]
                    for x, y in _corners(np.float32(cx), np.float32(cy), np.float32(a), fac, deg)
                ],
                dtype=np.float32,
            )
        )
    return out


# Floor on decoded anchor amplitude. Set between the strongest observed false
# positive (0.16) and the weakest genuine recovery (0.35, JPEG Q40).
_MIN_ANCHOR_CONFIDENCE = 0.25

_DETECT_MAX_EDGE = 1600  # cap matched-filter resolution. matchTemplate cost grows
                         # ~ area · template², so full-res detection on large art
                         # (4096² → ~20s) dominates both the embed self-check and
                         # verify. The anchor lattice is large and matched at
                         # multiple scales, so detecting on a downscaled copy and
                         # scaling the quad back is just as reliable at a fraction
                         # of the cost; the full-res image is still used to decode.


def _anchor_quad_candidates(image: np.ndarray) -> list[np.ndarray]:
    """Ordered candidate anchor quads: the blind global-search quad first (handles
    crop / heavy geometry), then the fixed-inset fallback (handles un-cropped
    social at very low amplitude). The decoder tries each; the record checksum
    rejects any wrong lock, so extra candidates never cause false positives.
    """
    if image.ndim != 3:
        return []
    H, W = image.shape[:2]
    if min(H, W) < _ANCHOR_MIN_EDGE:
        return []
    gray_full = _rgb_to_y(image)
    # Detection (matchTemplate) runs on a resolution-capped copy; quad coords are
    # scaled back to full-image pixels so the caller still rectifies at full res.
    longest = max(H, W)
    scale = 1.0
    if longest > _DETECT_MAX_EDGE:
        scale = _DETECT_MAX_EDGE / float(longest)
        gw = max(_ANCHOR_MIN_EDGE, int(round(W * scale)))
        gh = max(_ANCHOR_MIN_EDGE, int(round(H * scale)))
        gray = cv2.resize(gray_full, (gw, gh), interpolation=cv2.INTER_AREA)
    else:
        gray = gray_full
    h, w = gray.shape[:2]
    r = max(6.0, _ANCHOR_R_RATIO * min(h, w))
    resp = _matched_response(gray, r)
    cands: list[np.ndarray] = []
    groups = _corner_candidate_groups(resp, r)
    quad = _select_anchor_quad(groups, w, h)
    if quad is not None:
        cands.append(_refine_quad(resp, quad, r))
    cands.append(_inset_refined_quad(resp, w, h, r))
    # Last: the whole-rectangle search, which carries cropped busy content where
    # the per-corner ranking drops the real anchor. Appended rather than
    # inserted so detect_anchors() keeps returning the established quad.
    # Both the raw rectangle and a peak-snapped version of it: the rigid model
    # can sit a few px off, which is enough to fail the grid decode, and the
    # matched filter localises the true anchor to within ~6px once we are close
    # enough for the refine window to reach it. Snapping can also drag a good
    # rectangle onto a fur peak, so neither version supersedes the other.
    for lat in _lattice_search_quads(resp, w, h, r):
        cands.append(lat)
        cands.append(_refine_quad(resp, lat, r))
    if scale != 1.0 and cands:
        inv = 1.0 / scale
        cands = [c.astype(np.float32) * inv for c in cands]
    return cands


def detect_anchors(image: np.ndarray) -> np.ndarray | None:
    """Detect the 4 anchor centers; return TL,TR,BR,BL (px) or None.

    Global fiducial search: shape-matched response → NMS candidate peaks →
    choose the 4 that form the largest near-parallelogram.  No assumption about
    where the anchors sit, so arbitrary crop / scale / rotation are tolerated.
    """
    cands = _anchor_quad_candidates(image)
    return cands[0] if cands else None


def _refine_quad(resp: np.ndarray, quad: np.ndarray, r: float) -> np.ndarray:
    """Sub-pixel refine each corner via a response-weighted centroid."""
    h, w = resp.shape
    win = max(3, int(r))
    out = quad.copy().astype(np.float32)
    for i, (px, py) in enumerate(quad):
        x0 = max(0, int(px - win)); x1 = min(w, int(px + win) + 1)
        y0 = max(0, int(py - win)); y1 = min(h, int(py + win) + 1)
        rx, ry, _ = _peak_in_region(resp, y0, y1, x0, x1)
        out[i] = [rx, ry]
    return out


def rectify_inner(image: np.ndarray, anchors: np.ndarray, canon: int = _CANON) -> np.ndarray:
    """Warp the anchor quad to a canonical square covering the payload grid."""
    dst = np.array(
        [[0, 0], [canon, 0], [canon, canon], [0, canon]], dtype=np.float32
    )
    m = cv2.getPerspectiveTransform(anchors.astype(np.float32), dst)
    return cv2.warpPerspective(image, m, (canon, canon), flags=cv2.INTER_AREA)


def _read_grid_bits(canon_img: np.ndarray) -> np.ndarray:
    """Read GRID×GRID cell-mean Cr → per-cell bit estimate (relative to neighbours)."""
    gray = _rgb_to_cr(canon_img)
    cell = canon_img.shape[0] / _GRID
    means = np.zeros((_GRID, _GRID), dtype=np.float32)
    for r in range(_GRID):
        y0 = int(round(r * cell)); y1 = int(round((r + 1) * cell))
        for c in range(_GRID):
            x0 = int(round(c * cell)); x1 = int(round((c + 1) * cell))
            means[r, c] = float(gray[y0:y1, x0:x1].mean())
    # Remove low-frequency image content: compare each cell to a blurred field.
    bg = cv2.GaussianBlur(means, (0, 0), sigmaX=2.0)
    hi = means - bg
    return hi.ravel()


def _decode_from_quad(image: np.ndarray, anchors: np.ndarray,
                      region: str, nbits: int = _RECORD_BITS,
                      decoder=decode_anchor_record) -> dict | None:
    """Rectify by the given anchor quad and decode the record (None if invalid).

    ``nbits``/``decoder`` select the record layout: the default 16-bit
    creation/restrictions record, or the 24-bit Work-ID record for the
    traceability anchor (``_WORKID_RECORD_BITS`` + ``decode_workid_record``).
    """
    try:
        canon = rectify_inner(image, anchors)
    except cv2.error:
        return None

    if region == "seal":
        bits, confidence = _seal_decode(canon)
        rec = decode_anchor_record(bits)
        if rec is None:
            return None
        rec["confidence"] = confidence
        rec["channel"] = "anchor"
        return rec

    hi = _read_grid_bits(canon)
    pn = _pn_sequence(_GRID * _GRID)[:hi.size]
    cell_on = _payload_cell_mask(region).ravel()[:hi.size]
    n_cells = hi.size
    # De-whiten with the PN sequence, then majority-vote each record bit across
    # its repeated (active) cells. PN de-correlates residual image content → it
    # cancels; cells outside the payload region are skipped.
    despread = hi * pn
    acc = np.zeros(nbits, dtype=np.float64)
    cnt = np.zeros(nbits, dtype=np.float64)
    for i in range(n_cells):
        if not cell_on[i]:
            continue
        bi = i % nbits
        acc[bi] += despread[i]
        cnt[bi] += 1
    avg = acc / np.maximum(cnt, 1)
    bits = (avg > 0).astype(np.uint8)
    rec = decoder(bits)
    if rec is None:
        return None
    norm = _SEAL_CR_DELTA if region == "band" else _PAYLOAD_DELTA
    confidence = float(np.clip(np.mean(np.abs(avg)) / norm, 0.0, 1.0))
    rec["confidence"] = confidence
    rec["channel"] = "anchor"
    return rec


def extract_anchor_watermark(image: np.ndarray, region: str = "full",
                             nbits: int = _RECORD_BITS,
                             decoder=decode_anchor_record) -> dict | None:
    """Detect anchors, rectify, and decode the redundant record. None if absent.

    ``region`` must match the value used at embed time (``full``/``band``/``seal``).
    ``nbits``/``decoder`` select the record layout (default creation/restrictions,
    or the 24-bit Work-ID record via :func:`extract_anchor_id`).

    Tries each candidate anchor quad (blind global search + fixed-inset fallback)
    and returns the first that yields a checksum-valid record, so faded anchors
    that the global search can't pin down are still recovered on un-cropped social
    round-trips. The record's marker+checksum makes a wrong lock self-rejecting.
    """
    best = None
    for anchors in _anchor_quad_candidates(image):
        rec = _decode_from_quad(image, anchors, region, nbits=nbits, decoder=decoder)
        if rec is None:
            continue
        if best is None or rec.get("confidence", 0.0) > best.get("confidence", 0.0):
            best = rec
    if best is None:
        return None
    # The record's 24 bits are not enough on their own. Measured on unmarked
    # images under random crop/rotate/scale/JPEG, checksum-valid records appear
    # in 1.25% of frames with only two candidates and 12.5% once the search is
    # widened, because each candidate is an independent roll. Those spurious
    # records all read back weak (<=0.16) while genuine ones read 0.35+, so the
    # amplitude floor is what separates them. Claiming an unmarked image carries
    # someone's mark is the one failure that would void the scheme's evidence
    # value, so recall is traded away here rather than precision.
    if best.get("confidence", 0.0) < _MIN_ANCHOR_CONFIDENCE:
        return None
    return best


def embed_anchor_id(image: np.ndarray, work_id: int, region: str = "full") -> np.ndarray:
    """Embed a traceability anchor carrying a 16-bit Work-ID (JW-independent).

    The Work-ID resolves, via the registry, to the artist identity + exact
    timestamp (+ optional declaration). Use ``extract_anchor_id`` to recover it.
    """
    return embed_anchor_watermark(image, encode_workid_record(work_id), region=region)


def extract_anchor_id(image: np.ndarray, region: str = "full") -> dict | None:
    """Recover the Work-ID traceability record ({"work_id", "confidence", ...})."""
    return extract_anchor_watermark(
        image, region=region, nbits=_WORKID_RECORD_BITS, decoder=decode_workid_record
    )


def embed_anchor_signature(image: np.ndarray, artist: str,
                           created_at: str | int | None = None,
                           region: str = "full") -> np.ndarray:
    """Embed a screenshot-robust anchor carrying the 16-bit tracking payload
    (10-bit artist code + 6-bit year-month). Self-contained — no registry. Pair
    with the invisible signature layers, which hold the full readable artist +
    exact timestamp; this digest is what still survives a screenshot."""
    payload = encode_anchor_tracking(artist, created_at)
    return embed_anchor_watermark(image, encode_workid_record(payload), region=region)


def read_anchor_tracking(image: np.ndarray, region: str = "full",
                         ref: str | int | float | None = None,
                         known_artist: str | None = None) -> dict | None:
    """Recover the tracking anchor → {artist_code, year, month, confidence, ...}.

    If ``known_artist`` is given (e.g. the artist string decoded from a surviving
    signature layer, or the verifier's account), we also report whether its code
    matches the anchor's — turning the bare code into a confirmed identity.
    Returns None when no anchor is present.
    """
    rec = extract_anchor_id(image, region=region)
    if rec is None:
        return None
    info = decode_anchor_tracking(rec["work_id"], ref=ref)
    info["confidence"] = rec.get("confidence", 0.0)
    info["raw"] = rec["work_id"]
    if known_artist is not None:
        info["artist_matches"] = (artist_code(known_artist) == info["artist_code"])
    return info
