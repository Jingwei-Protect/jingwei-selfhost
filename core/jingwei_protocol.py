"""
Jingwei Protocol — three-layer redundant watermark for AI-resistant detection.

Why three layers
----------------
A single-band DWT watermark survives JPEG and screenshots, but is wiped by
AI rerender (img2img / diffusion inpaint) because the model regenerates pixels
in latent space. To raise the cost of total removal, JW embeds the same
256-bit payload into three independent frequency / channel locations:

  L1. Cr-channel LL2 DWT  (delta=60)  — robust to JPEG, screenshot, resize
  L2. Cb-channel LL2 DWT  (delta=60)  — independent chroma, second chance
  L3. Y-channel 8x8 DCT mid-band pair (strength=30) — robust to local edits;
      uses the (3,2) / (4,1) coefficient pair (zigzag mid-frequency).

Extraction tries each layer independently. ANY layer that decodes a valid
payload (marker + checksum or JW prefix) counts as a hit. If no single layer
decodes alone, a confidence-weighted bit-majority vote across layers is
attempted as a last-resort fusion.

Encoding strategy:
  JW manifest → 24-char ASCII payload → 256-bit array → embedded in all three.
"""

from __future__ import annotations

import hashlib
import struct
import time
import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable, Literal

import cv2
import numpy as np
import pywt

JW_MANIFEST_VERSION = 1
_JW_PREFIX = "JW1"

_WAVELET = "haar"
_DWT_LEVEL = 2
_DELTA = 60.0   # Higher delta for chroma channels (JPEG subsamples chroma 4:2:0)
_DCT_STRENGTH = 22.0  # Y-channel 8x8 DCT mid-band coefficient pair gap (PSNR-tuned)
_PAYLOAD_BITS = 256
_MIN_REPEATS = 3
_MARKER = 0x4A  # 'J'
_MAX_TEXT_LEN = 24
_MIN_CONFIDENCE = 0.45

# DCT mid-band coefficient pair (zigzag positions ~7 and ~8 — mid frequency)
_DCT_C1 = (3, 2)
_DCT_C2 = (4, 1)

# Layer-4: scale-invariant block-DC quantisation on the Y channel.
# A fixed N×N grid (independent of image dimensions) means cell averages
# survive arbitrary linear rescaling — the screenshot-killer attack vector
# for the LL2/DCT layers.
_L4_GRID = 24            # 24×24 = 576 cells → 256-bit payload tiled 2.25×
_L4_DELTA = 4.0          # ±2 grayscale shift per cell → near-invisible on flat areas
_L4_MIN_CELL_PIXELS = 4  # require ≥ 4×4 cell footprint
_L4_FEATHER_RATIO = 0.18 # smooth cell boundary (fraction of cell side)
_L4_SKIP_VAR_BELOW = 6.0 # skip near-uniform cells (large flat white areas)

# Visible badge / footer symbol ink (always monochrome)
_BADGE_INK = (26, 26, 26, 255)
_BADGE_INK_ON_DARK = (255, 255, 255, 255)
_BADGE_LUMA_THRESHOLD = 140.0

# Flat-region detector — blocks with Y variance below this count as "flat".
_FLAT_BLOCK_VAR = 8.0
# Fraction of flat 8×8 blocks above which chroma DWT tiers are skipped.
_FLAT_RATIO_CHROMA_BLOCK = 0.55
_FLAT_RATIO_FULL_BLOCK = 0.35

# Y-LL2 DWT deltas used at embed time (profiles) and at extract (multi-try).
_Y_DWT_EXTRACT_DELTAS = (18.0, 28.0, 30.0, 35.0, 60.0)


@dataclass(frozen=True)
class JwEmbedProfile:
    """Strength ladder for JW embed — higher tiers trade visibility for decode reliability."""

    name: str
    chroma_dwt: Literal["none", "cr", "both"] = "none"
    chroma_delta: float = _DELTA
    y_ll2: bool = False
    y_ll2_delta: float = 30.0
    dct_strength: float = 10.0
    l4_delta: float = 2.0
    l4_skip: float = 20.0
    dct_skip: float = 24.0


JW_PROFILE_STEALTH = JwEmbedProfile(name="stealth")
JW_PROFILE_Y_BOOST = JwEmbedProfile(
    name="y_boost",
    dct_strength=14.0,
    l4_delta=3.0,
    l4_skip=12.0,
    dct_skip=14.0,
)
# Gentler Y-boost for flat illustrations — fewer L4 cells touched, less grid/dim.
JW_PROFILE_Y_BOOST_FLAT = JwEmbedProfile(
    name="y_boost",
    dct_strength=12.0,
    l4_delta=2.5,
    l4_skip=18.0,
    dct_skip=18.0,
)
JW_PROFILE_TEXTURE_BOOST = JwEmbedProfile(
    name="texture_boost",
    dct_strength=16.0,
    l4_delta=3.5,
    l4_skip=8.0,
    dct_skip=10.0,
)
JW_PROFILE_TEXTURE_MAX = JwEmbedProfile(
    name="texture_max",
    dct_strength=18.0,
    l4_delta=4.0,
    l4_skip=4.0,
    dct_skip=6.0,
)
JW_PROFILE_CR_TEXTURE = JwEmbedProfile(
    name="cr_texture",
    chroma_dwt="cr",
    chroma_delta=28.0,
    dct_strength=16.0,
    l4_delta=3.5,
    l4_skip=8.0,
    dct_skip=10.0,
)
JW_PROFILE_Y_LL2 = JwEmbedProfile(
    name="y_ll2",
    y_ll2=True,
    y_ll2_delta=24.0,
    dct_strength=14.0,
    l4_delta=3.0,
    l4_skip=8.0,
    dct_skip=10.0,
)
JW_PROFILE_CR_SINGLE = JwEmbedProfile(
    name="cr_single",
    chroma_dwt="cr",
    chroma_delta=35.0,
    y_ll2=True,
    y_ll2_delta=24.0,
    dct_strength=18.0,
    l4_delta=3.5,
    l4_skip=6.0,
    dct_skip=8.0,
)
JW_PROFILE_FULL = JwEmbedProfile(
    name="full",
    chroma_dwt="both",
    chroma_delta=_DELTA,
    dct_strength=_DCT_STRENGTH,
    l4_delta=_L4_DELTA,
    l4_skip=_L4_SKIP_VAR_BELOW,
    dct_skip=0.0,
)


class JwEmbedPriority(str, Enum):
    """Embed strength ladder selector (legacy values map to AUTO)."""

    AUTO = "auto"
    COLOR = "color"
    BALANCED = "balanced"
    VERIFY = "verify"


class JwCreationType(str, Enum):
    ORIGINAL = "OC"
    AI_ASSISTED = "AI"


def parse_jw_embed_priority(value: str | None) -> JwEmbedPriority:
    raw = (value or "").strip().lower()
    for member in JwEmbedPriority:
        if raw == member.value:
            return member
    return JwEmbedPriority.AUTO


def build_jw_embed_ladder(
    flat_ratio: float,
    priority: JwEmbedPriority,
) -> list[JwEmbedProfile]:
    """Return ordered texture-first JW profiles, capped by image flatness.

    Flat/mixed images stop at lighter tiers (faster, less visible); rich art
    may use stronger tiers. Never includes whole-image Y-LL2 grid profiles.
    """
    _ = priority  # legacy color/balanced/verify all use AUTO ladder

    if flat_ratio >= _FLAT_RATIO_CHROMA_BLOCK:
        return [JW_PROFILE_STEALTH, JW_PROFILE_Y_BOOST_FLAT]

    ladder: list[JwEmbedProfile] = [
        JW_PROFILE_STEALTH,
        JW_PROFILE_Y_BOOST,
        JW_PROFILE_TEXTURE_BOOST,
    ]
    if flat_ratio >= _FLAT_RATIO_FULL_BLOCK:
        return ladder

    ladder.append(JW_PROFILE_TEXTURE_MAX)
    ladder.append(JW_PROFILE_CR_TEXTURE)
    return ladder


JW_FLAG_NO_TRAINING = 1 << 0
JW_FLAG_NO_AI_EDIT = 1 << 1
JW_FLAG_NO_REMOVAL = 1 << 2
JW_FLAG_NO_REMIX = 1 << 3
JW_FLAG_NO_COMMERCIAL = 1 << 4

JW_FLAG_LABELS: dict[int, str] = {
    JW_FLAG_NO_TRAINING: "NO-TR",
    JW_FLAG_NO_AI_EDIT: "NO-ED",
    JW_FLAG_NO_REMOVAL: "NO-RM",
    JW_FLAG_NO_REMIX: "NO-RX",
    JW_FLAG_NO_COMMERCIAL: "NO-NC",
}


@dataclass
class JwManifest:
    version: int = JW_MANIFEST_VERSION
    creation: JwCreationType = JwCreationType.ORIGINAL
    restrictions: int = 0
    visible_badge: bool = True
    artist: str = ""
    extra: dict = field(default_factory=dict)

    def set_restriction(self, flag: int, enabled: bool) -> None:
        if enabled:
            self.restrictions |= flag
        else:
            self.restrictions &= ~flag

    def has_restriction(self, flag: int) -> bool:
        return bool(self.restrictions & flag)

    def restriction_abbrevs(self) -> list[str]:
        return [
            label
            for bit, label in JW_FLAG_LABELS.items()
            if self.restrictions & bit
        ]

    def badge_text(self) -> str:
        parts = ["JW", self.creation.value, *self.restriction_abbrevs()]
        return " · ".join(parts)


def parse_creation(value: str | None) -> JwCreationType:
    if value and value.upper() == JwCreationType.AI_ASSISTED.value:
        return JwCreationType.AI_ASSISTED
    return JwCreationType.ORIGINAL


def restrictions_from_ids(ids: Iterable[str]) -> int:
    id_to_bit = {v: k for k, v in JW_FLAG_LABELS.items()}
    mask = 0
    for rid in ids:
        bit = id_to_bit.get(rid.upper())
        if bit is not None:
            mask |= bit
    return mask


# ─── Payload Encoding ───────────────────────────────────────────────────

def _artist_hash(artist: str) -> str:
    h = hashlib.sha256(artist.strip().lower().encode("utf-8")).hexdigest()
    return h[:4].upper()


def _sanitize_artist(artist: str, max_len: int = 14) -> str:
    safe = "".join(c if 32 < ord(c) < 127 else "_" for c in artist.strip())
    return safe[:max_len]


def encode_jw_payload(manifest: JwManifest) -> str:
    """Encode JwManifest → 24-char ASCII string.

    Layout: JW1 + creation(1) + restrictions_hex(2) + artist_hash(4) + artist_prefix(14)
    """
    creation_char = "O" if manifest.creation == JwCreationType.ORIGINAL else "A"
    restrictions_hex = f"{manifest.restrictions & 0xFF:02X}"
    ahash = _artist_hash(manifest.artist) if manifest.artist.strip() else "0000"
    aprefix = _sanitize_artist(manifest.artist, 14).ljust(14, "_")
    return f"{_JW_PREFIX}{creation_char}{restrictions_hex}{ahash}{aprefix}"[:24]


def encode_jw_lsb_payload(manifest: JwManifest, embed_timestamp: int | None = None) -> str:
    """JW manifest string for LSB backup: 24-char payload + 8 hex Unix timestamp."""
    base = encode_jw_payload(manifest)
    ts = int(time.time()) if embed_timestamp is None else int(embed_timestamp)
    return f"{base}{ts & 0xFFFFFFFF:08X}"


def parse_jw_lsb_text(text: str) -> tuple[JwManifest | None, int]:
    """Decode LSB JW text; returns (manifest, unix_timestamp). Timestamp 0 if absent."""
    if not text or not text.startswith(_JW_PREFIX):
        return None, 0
    core = text[:24]
    manifest = decode_jw_payload(core)
    if manifest is None:
        return None, 0
    if len(text) >= 32:
        suffix = text[24:32]
        if len(suffix) == 8 and all(c in "0123456789ABCDEFabcdef" for c in suffix):
            try:
                return manifest, int(suffix, 16)
            except ValueError:
                pass
    return manifest, 0


def decode_jw_payload(payload: str) -> JwManifest | None:
    """Decode a payload string back to JwManifest, or None if not JW."""
    if not payload or len(payload) < 10 or not payload.startswith(_JW_PREFIX):
        return None

    creation_char = payload[3]
    creation = JwCreationType.AI_ASSISTED if creation_char == "A" else JwCreationType.ORIGINAL

    try:
        restrictions = int(payload[4:6], 16)
    except ValueError:
        restrictions = 0

    artist_hash = payload[6:10]
    artist_prefix = payload[10:24].rstrip("_").strip() if len(payload) > 10 else ""

    manifest = JwManifest(
        creation=creation,
        restrictions=restrictions,
        artist=artist_prefix,
    )
    manifest.extra["artist_hash"] = artist_hash
    return manifest


# ─── Color space ────────────────────────────────────────────────────────

def _rgb_to_ycbcr(image: np.ndarray) -> np.ndarray:
    img_f = image.astype(np.float32)
    r, g, b = img_f[:, :, 0], img_f[:, :, 1], img_f[:, :, 2]
    y = np.float32(0.299) * r + np.float32(0.587) * g + np.float32(0.114) * b
    cb = np.float32(-0.169) * r - np.float32(0.331) * g + np.float32(0.500) * b + np.float32(128.0)
    cr = np.float32(0.500) * r - np.float32(0.419) * g - np.float32(0.081) * b + np.float32(128.0)
    out = np.empty((*image.shape[:2], 3), dtype=np.float32)
    out[:, :, 0] = y
    out[:, :, 1] = cb
    out[:, :, 2] = cr
    return out


def _ycbcr_to_rgb(ycbcr: np.ndarray) -> np.ndarray:
    y = ycbcr[:, :, 0]
    cb = ycbcr[:, :, 1] - np.float32(128.0)
    cr = ycbcr[:, :, 2] - np.float32(128.0)
    r = y + np.float32(1.402) * cr
    g = y - np.float32(0.344) * cb - np.float32(0.714) * cr
    b = y + np.float32(1.772) * cb
    out = np.empty_like(ycbcr, dtype=np.float32)
    out[:, :, 0] = r
    out[:, :, 1] = g
    out[:, :, 2] = b
    np.clip(out, 0, 255, out=out)
    return out.astype(np.uint8)


# ─── Bit-level codec ────────────────────────────────────────────────────

def _encode_bits(text: str, timestamp: int | None = None) -> np.ndarray:
    """Encode text → 256-bit array (J marker + len + text + timestamp + checksum)."""
    if timestamp is None:
        timestamp = int(time.time()) & 0xFFFFFFFF

    text_bytes = text.encode("ascii", errors="replace")[:_MAX_TEXT_LEN]
    text_len = len(text_bytes)

    buf = bytearray(32)
    buf[0] = _MARKER
    buf[1] = text_len
    buf[2: 2 + text_len] = text_bytes
    struct.pack_into(">I", buf, 26, timestamp)
    xor = 0
    for b in buf[:30]:
        xor ^= b
    buf[30] = xor & 0xFF
    buf[31] = (~xor) & 0xFF
    return np.unpackbits(np.frombuffer(bytes(buf), dtype=np.uint8))


_JW_PREFIX_BYTES = _JW_PREFIX.encode("ascii")
# False-positive budget on random bits, per attempt (incl. cyclic shifts):
#   P(marker_dist ≤ 1) = 9/256 ≈ 3.5%
#   P(prefix_dist ≤ 3) = ~2500/2^24 ≈ 1.5e-4
#   Combined ≈ 5e-6 per attempt. With ≤ 32 shifts × 3 channels = 96 attempts
#   on an unmarked image → ~5e-4 false-positive rate. Acceptable.
_MARKER_FUZZY_MAX_BITS = 1
_PREFIX_FUZZY_MAX_BITS = 3


def _popcount(x: int) -> int:
    return bin(x & 0xFF).count("1")


def _bytes_hamming(a: bytes, b: bytes) -> int:
    return sum(_popcount(x ^ y) for x, y in zip(a, b))


def _decode_buf(buf: bytes) -> dict | None:
    """Try strict, then fuzzy decode of a 32-byte payload buffer."""
    if len(buf) < 32:
        buf = buf + b"\x00" * (32 - len(buf))

    xor = 0
    for b in buf[:30]:
        xor ^= b
    checksum_ok = buf[30] == (xor & 0xFF) and buf[31] == ((~xor) & 0xFF)

    text_len = buf[1] if buf[1] <= _MAX_TEXT_LEN else _MAX_TEXT_LEN
    text = buf[2: 2 + text_len].decode("ascii", errors="replace").rstrip("\x00")
    timestamp = struct.unpack_from(">I", buf, 26)[0]

    if buf[0] == _MARKER and (checksum_ok or text.startswith(_JW_PREFIX)):
        return {
            "payload_text": text,
            "timestamp": timestamp,
            "checksum_ok": checksum_ok,
            "fuzzy": False,
        }

    marker_dist = _popcount(buf[0] ^ _MARKER)
    prefix_dist = _bytes_hamming(buf[2:5], _JW_PREFIX_BYTES)
    if (marker_dist <= _MARKER_FUZZY_MAX_BITS
            and prefix_dist <= _PREFIX_FUZZY_MAX_BITS):
        fuzzy_text = _JW_PREFIX + text[3:] if len(text) >= 3 else _JW_PREFIX
        return {
            "payload_text": fuzzy_text,
            "timestamp": timestamp,
            "checksum_ok": False,
            "fuzzy": True,
            "marker_distance": marker_dist,
            "prefix_distance": prefix_dist,
        }
    return None


def _decode_bits(bits: np.ndarray) -> dict | None:
    """Decode 256 bits, with a byte-aligned cyclic-shift search.

    Crops on the carrier image cause the tiled bit indices to roll relative
    to the embedded payload. We search 32 byte-aligned rotations and accept
    the best strict/fuzzy match. Strict checksum wins; otherwise we keep the
    lowest marker+prefix Hamming distance.
    """
    bits = bits[:_PAYLOAD_BITS].astype(np.uint8)

    best: dict | None = None
    best_score = (10**6, 10**6)  # (marker_dist, prefix_dist) — lower is better

    for shift_bytes in range(0, 32):
        if shift_bytes == 0:
            rolled = bits
        else:
            shift = shift_bytes * 8
            rolled = np.concatenate([bits[shift:], bits[:shift]])
        buf = np.packbits(rolled).tobytes()[:32]
        candidate = _decode_buf(buf)
        if candidate is None:
            continue
        if candidate.get("checksum_ok"):
            candidate["rotation_bytes"] = shift_bytes
            return candidate
        score = (
            candidate.get("marker_distance", 0),
            candidate.get("prefix_distance", 0),
        )
        if score < best_score:
            best = {**candidate, "rotation_bytes": shift_bytes}
            best_score = score

    return best


# ─── Layer 1 & 2: DWT LL2 quantisation (one channel) ────────────────────

def _embed_dwt_channel(channel: np.ndarray, payload_bits: np.ndarray, delta: float) -> np.ndarray:
    """Embed 256 bits into a single channel's LL2 subband. Returns reconstructed channel."""
    coeffs = pywt.wavedec2(channel, _WAVELET, level=_DWT_LEVEL)
    ll = coeffs[0].copy()
    ll_flat = ll.ravel()
    n_coeffs = len(ll_flat)
    if n_coeffs < _PAYLOAD_BITS:
        return channel

    n_repeats = max(_MIN_REPEATS, n_coeffs // _PAYLOAD_BITS)
    total_embed = min(n_repeats * _PAYLOAD_BITS, n_coeffs)
    tiled_bits = np.tile(payload_bits, n_repeats)[:total_embed]

    for i in range(total_embed):
        coeff = ll_flat[i]
        bit = tiled_bits[i]
        quantized = round(coeff / delta)
        if bit == 1:
            if quantized % 2 == 0:
                quantized += 1 if coeff >= quantized * delta else -1
        else:
            if quantized % 2 != 0:
                quantized += 1 if coeff >= quantized * delta else -1
        ll_flat[i] = quantized * delta

    coeffs[0] = ll_flat.reshape(ll.shape)
    reconstructed = pywt.waverec2(coeffs, _WAVELET)
    return reconstructed[:channel.shape[0], :channel.shape[1]]


def _extract_dwt_channel(channel: np.ndarray, delta: float) -> tuple[np.ndarray, float]:
    """Extract 256-bit vote + confidence from a channel's LL2."""
    coeffs = pywt.wavedec2(channel, _WAVELET, level=_DWT_LEVEL)
    ll = coeffs[0]
    ll_flat = ll.ravel()
    n_coeffs = len(ll_flat)
    if n_coeffs < _PAYLOAD_BITS:
        return np.zeros(_PAYLOAD_BITS, dtype=np.uint8), 0.0

    n_repeats = max(_MIN_REPEATS, n_coeffs // _PAYLOAD_BITS)
    total_read = min(n_repeats * _PAYLOAD_BITS, n_coeffs)

    extracted_bits = np.zeros(total_read, dtype=np.int32)
    for i in range(total_read):
        coeff = ll_flat[i]
        quantized = round(coeff / delta)
        extracted_bits[i] = 1 if quantized % 2 != 0 else 0

    bit_votes = np.zeros(_PAYLOAD_BITS, dtype=np.float64)
    vote_counts = np.zeros(_PAYLOAD_BITS, dtype=np.int32)
    for i in range(total_read):
        idx = i % _PAYLOAD_BITS
        bit_votes[idx] += extracted_bits[i]
        vote_counts[idx] += 1

    safe_counts = np.maximum(vote_counts, 1)
    bit_ratios = bit_votes / safe_counts
    final_bits = (bit_ratios > 0.5).astype(np.uint8)
    confidence = float(np.mean(np.abs(bit_ratios - 0.5) * 2.0))
    return final_bits, confidence


# ─── Layer 3: Y-channel 8x8 DCT mid-band pair ───────────────────────────

def _embed_dct_mid_y(
    y_channel: np.ndarray,
    payload_bits: np.ndarray,
    strength: float,
    *,
    skip_var_below: float = 0.0,
) -> np.ndarray:
    """Embed payload by enforcing a sign-and-gap relation between two mid-band DCT coefficients.

    Bit=1 → coeff at _DCT_C1 > coeff at _DCT_C2 + strength
    Bit=0 → coeff at _DCT_C2 > coeff at _DCT_C1 + strength
    """
    h, w = y_channel.shape
    bh, bw = h // 8, w // 8
    n_blocks = bh * bw
    if n_blocks < _PAYLOAD_BITS:
        return y_channel

    n_repeats = max(1, n_blocks // _PAYLOAD_BITS)
    total_embed = min(n_repeats * _PAYLOAD_BITS, n_blocks)
    tiled_bits = np.tile(payload_bits, n_repeats)[:total_embed]

    out = y_channel.astype(np.float32).copy()
    r1, c1_pos = _DCT_C1
    r2, c2_pos = _DCT_C2

    block_idx = 0
    for by in range(bh):
        for bx in range(bw):
            if block_idx >= total_embed:
                break
            y0, x0 = by * 8, bx * 8
            block_view = out[y0:y0 + 8, x0:x0 + 8]
            if skip_var_below > 0 and float(block_view.var()) < skip_var_below:
                block_idx += 1
                continue
            block = block_view - 128.0
            dct_block = cv2.dct(block)
            c1 = dct_block[r1, c1_pos]
            c2 = dct_block[r2, c2_pos]

            bit = tiled_bits[block_idx]
            if bit == 1:
                gap = c1 - c2
                if gap < strength:
                    push = (strength - gap) / 2.0
                    c1 += push
                    c2 -= push
            else:
                gap = c2 - c1
                if gap < strength:
                    push = (strength - gap) / 2.0
                    c2 += push
                    c1 -= push

            dct_block[r1, c1_pos] = c1
            dct_block[r2, c2_pos] = c2
            block_back = cv2.idct(dct_block) + 128.0
            out[y0:y0 + 8, x0:x0 + 8] = block_back
            block_idx += 1
        if block_idx >= total_embed:
            break

    np.clip(out, 0, 255, out=out)
    return out


def _extract_dct_mid_y(y_channel: np.ndarray) -> tuple[np.ndarray, float]:
    """Extract bits + confidence from Y 8x8 DCT mid-band sign relation."""
    h, w = y_channel.shape
    bh, bw = h // 8, w // 8
    n_blocks = bh * bw
    if n_blocks < _PAYLOAD_BITS:
        return np.zeros(_PAYLOAD_BITS, dtype=np.uint8), 0.0

    n_repeats = max(1, n_blocks // _PAYLOAD_BITS)
    total_read = min(n_repeats * _PAYLOAD_BITS, n_blocks)

    r1, c1_pos = _DCT_C1
    r2, c2_pos = _DCT_C2

    bit_votes = np.zeros(_PAYLOAD_BITS, dtype=np.float64)
    vote_counts = np.zeros(_PAYLOAD_BITS, dtype=np.int32)

    y_f32 = y_channel.astype(np.float32)
    block_idx = 0
    for by in range(bh):
        for bx in range(bw):
            if block_idx >= total_read:
                break
            y0, x0 = by * 8, bx * 8
            block = y_f32[y0:y0 + 8, x0:x0 + 8] - 128.0
            dct_block = cv2.dct(block)
            diff = dct_block[r1, c1_pos] - dct_block[r2, c2_pos]
            bit = 1 if diff > 0 else 0

            idx = block_idx % _PAYLOAD_BITS
            bit_votes[idx] += bit
            vote_counts[idx] += 1
            block_idx += 1
        if block_idx >= total_read:
            break

    safe_counts = np.maximum(vote_counts, 1)
    bit_ratios = bit_votes / safe_counts
    final_bits = (bit_ratios > 0.5).astype(np.uint8)
    confidence = float(np.mean(np.abs(bit_ratios - 0.5) * 2.0))
    return final_bits, confidence


# ─── Layer 4: Scale-invariant block-DC on Y channel ─────────────────────

def _cell_bounds(n_grid: int, h: int, w: int) -> tuple[np.ndarray, np.ndarray]:
    """Return integer row/col boundaries for an N×N grid using floor rounding.

    Boundaries are computed from a float grid (h/n_grid, w/n_grid) so the
    cells stay near-uniform regardless of whether h/w divide cleanly. This
    is what makes the layer scale-invariant: under a linear rescale, the
    same boundaries (rounded) cover the same image content.
    """
    rows = np.floor(np.linspace(0, h, n_grid + 1)).astype(np.int32)
    cols = np.floor(np.linspace(0, w, n_grid + 1)).astype(np.int32)
    return rows, cols


def _feather_mask(cell_h: int, cell_w: int, feather_ratio: float) -> np.ndarray:
    """Cosine-tapered 2D mask so cell-boundary shifts blend smoothly.

    Eliminates the visible grid lines that a hard rectangular shift would
    leave behind on smooth backgrounds.
    """
    def axis_taper(n: int) -> np.ndarray:
        f = max(1, int(round(n * feather_ratio)))
        m = np.ones(n, dtype=np.float32)
        if f * 2 < n:
            ramp = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, f, dtype=np.float32))
            m[:f] = ramp
            m[-f:] = ramp[::-1]
        return m
    return axis_taper(cell_h)[:, None] * axis_taper(cell_w)[None, :]


def _embed_block_dc_y(y_channel: np.ndarray, payload_bits: np.ndarray,
                      *, n_grid: int = _L4_GRID, delta: float = _L4_DELTA,
                      skip_var_below: float = _L4_SKIP_VAR_BELOW) -> np.ndarray:
    """Quantise the mean of each N×N grid cell to encode bits.

    Robust to arbitrary linear rescaling: a cell's mean is approximately
    preserved under any scaling, so the quantisation parity survives.
    """
    h, w = y_channel.shape
    if min(h, w) < n_grid * _L4_MIN_CELL_PIXELS:
        return y_channel  # cells would be too small

    rows, cols = _cell_bounds(n_grid, h, w)
    n_cells = n_grid * n_grid
    n_repeats = max(1, n_cells // _PAYLOAD_BITS)
    tiled = np.tile(payload_bits, n_repeats)[:min(n_cells, n_repeats * _PAYLOAD_BITS)]
    if len(tiled) < n_cells:
        tiled = np.concatenate([tiled, payload_bits[: n_cells - len(tiled)]])

    out = y_channel.astype(np.float32).copy()
    for idx in range(n_cells):
        i, j = divmod(idx, n_grid)
        r0, r1 = rows[i], rows[i + 1]
        c0, c1 = cols[j], cols[j + 1]
        if r1 - r0 < _L4_MIN_CELL_PIXELS or c1 - c0 < _L4_MIN_CELL_PIXELS:
            continue

        cell_view = out[r0:r1, c0:c1]
        if float(cell_view.var()) < skip_var_below:
            continue
        cell_mean = float(cell_view.mean())
        quantized = round(cell_mean / delta)
        bit = int(tiled[idx])
        if (quantized % 2) != bit:
            quantized += 1 if (cell_mean >= quantized * delta) else -1
        target_mean = quantized * delta
        shift = target_mean - cell_mean

        mask = _feather_mask(r1 - r0, c1 - c0, _L4_FEATHER_RATIO)
        scale = shift / max(mask.mean(), 1e-6)
        out[r0:r1, c0:c1] = cell_view + mask * scale

    np.clip(out, 0, 255, out=out)
    return out


def _extract_block_dc_y(y_channel: np.ndarray,
                        *, n_grid: int = _L4_GRID, delta: float = _L4_DELTA
                        ) -> tuple[np.ndarray, float]:
    """Decode L4 bits from a (possibly rescaled) Y channel."""
    h, w = y_channel.shape
    if min(h, w) < n_grid * _L4_MIN_CELL_PIXELS:
        return np.zeros(_PAYLOAD_BITS, dtype=np.uint8), 0.0

    rows, cols = _cell_bounds(n_grid, h, w)
    n_cells = n_grid * n_grid

    extracted = np.zeros(n_cells, dtype=np.float64)
    for idx in range(n_cells):
        i, j = divmod(idx, n_grid)
        r0, r1 = rows[i], rows[i + 1]
        c0, c1 = cols[j], cols[j + 1]
        if r1 <= r0 or c1 <= c0:
            extracted[idx] = 0.5
            continue
        cell_mean = float(y_channel[r0:r1, c0:c1].mean())
        quantized = round(cell_mean / delta)
        residual = cell_mean - quantized * delta  # ∈ [-δ/2, δ/2]
        # Soft bit value: bias toward parity, scaled by how cleanly the mean
        # sits on a quantisation level (smaller residual ⇒ more confident).
        soft = 1.0 if (quantized % 2) else 0.0
        confidence = 1.0 - 2.0 * abs(residual) / delta  # 1 at lattice, 0 at midpoint
        extracted[idx] = 0.5 + (soft - 0.5) * max(confidence, 0.0)

    bit_votes = np.zeros(_PAYLOAD_BITS, dtype=np.float64)
    weight_sum = np.zeros(_PAYLOAD_BITS, dtype=np.float64)
    for idx in range(n_cells):
        bit_idx = idx % _PAYLOAD_BITS
        weight = abs(extracted[idx] - 0.5) * 2.0 + 1e-4
        bit_votes[bit_idx] += extracted[idx] * weight
        weight_sum[bit_idx] += weight

    bit_ratios = bit_votes / np.maximum(weight_sum, 1e-6)
    final_bits = (bit_ratios > 0.5).astype(np.uint8)
    confidence = float(np.mean(np.abs(bit_ratios - 0.5) * 2.0))
    return final_bits, confidence


# ─── Public API ─────────────────────────────────────────────────────────

def estimate_flat_ratio(image: np.ndarray) -> float:
    """Fraction of 8×8 Y blocks with variance below _FLAT_BLOCK_VAR."""
    if image.ndim != 3 or image.shape[2] != 3:
        return 0.0
    ycbcr = _rgb_to_ycbcr(image)
    y = ycbcr[:, :, 0]
    h, w = y.shape
    # Downsample very large uploads — same decision, much faster on phone wallpapers.
    max_side = max(h, w)
    if max_side > 960:
        scale = 960.0 / max_side
        nh = max(8, int(h * scale))
        nw = max(8, int(w * scale))
        y = cv2.resize(y, (nw, nh), interpolation=cv2.INTER_AREA)
        h, w = y.shape
    bh, bw = h // 8, w // 8
    if bh == 0 or bw == 0:
        return 0.0
    y_crop = y[: bh * 8, : bw * 8]
    blocks = (
        y_crop.reshape(bh, 8, bw, 8)
        .transpose(0, 2, 1, 3)
        .reshape(bh * bw, 8, 8)
        .astype(np.float64)
    )
    flat = int(np.sum(blocks.var(axis=(1, 2)) < _FLAT_BLOCK_VAR))
    return flat / (bh * bw)


def estimate_texture_ratio(image: np.ndarray) -> float:
    """Complement of flat_ratio — approximate share of non-uniform 8×8 blocks."""
    return max(0.0, min(1.0, 1.0 - estimate_flat_ratio(image)))


def jw_write_hint_for_image(image: np.ndarray) -> dict:
    """User-facing hint before protect (plain language, no tier jargon)."""
    flat_ratio = estimate_flat_ratio(image)
    texture_ratio = 1.0 - flat_ratio
    if flat_ratio >= _FLAT_RATIO_CHROMA_BLOCK:
        kind = "flat"
        summary = "您的图大色块较多，隐形精卫写入空间有限。"
        suggest = "建议开启底部白边并选用 PNG。"
    elif flat_ratio >= _FLAT_RATIO_FULL_BLOCK:
        kind = "mixed"
        summary = "您的图含较大纯色区域；隐形精卫会主要写在细节与边缘，大色块区域会尽量保持原样。"
        suggest = "建议选用 PNG 保存原图以便验证。"
    else:
        kind = "rich"
        summary = "您的图细节较多，适合隐形精卫，通常不易看出变化。"
        suggest = "建议选用 PNG 保存原图以便验证。"
    return {
        "kind": kind,
        "flat_ratio": round(flat_ratio, 3),
        "texture_ratio": round(texture_ratio, 3),
        "summary": summary,
        "suggest": suggest,
    }


def _embed_y_layers(
    y_channel: np.ndarray,
    payload_bits: np.ndarray,
    profile: JwEmbedProfile,
    *,
    image_h: int,
    image_w: int,
) -> np.ndarray:
    y = y_channel.copy()
    if image_h >= 128 and image_w >= 128:
        y = _embed_dct_mid_y(
            y, payload_bits, profile.dct_strength, skip_var_below=profile.dct_skip,
        )
    y = _embed_block_dc_y(
        y, payload_bits, delta=profile.l4_delta, skip_var_below=profile.l4_skip,
    )
    if profile.y_ll2:
        y = _embed_dwt_channel(y, payload_bits, profile.y_ll2_delta)
    return y


def embed_jw_watermark(
    image: np.ndarray,
    manifest: JwManifest,
    *,
    perceptual_stealth: bool = False,
    profile: JwEmbedProfile | None = None,
    embed_timestamp: int | None = None,
) -> np.ndarray:
    """Embed JW manifest into redundant frequency / channel locations.

    Pass ``profile`` for tiered strength; ``perceptual_stealth=True`` maps to
    JW_PROFILE_STEALTH when profile is omitted.
    """
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Input must be uint8 HxWx3 RGB.")
    if image.shape[0] < 64 or image.shape[1] < 64:
        raise ValueError("Image must be at least 64x64 for JW watermark.")

    if profile is None:
        profile = JW_PROFILE_STEALTH if perceptual_stealth else JW_PROFILE_FULL

    payload_str = encode_jw_payload(manifest)
    ts = int(time.time()) if embed_timestamp is None else int(embed_timestamp)
    payload_bits = _encode_bits(payload_str, timestamp=ts)
    ycbcr = _rgb_to_ycbcr(image)
    h, w = image.shape[:2]

    if profile.chroma_dwt in ("cr", "both"):
        ycbcr[:, :, 2] = _embed_dwt_channel(
            ycbcr[:, :, 2].copy(), payload_bits, profile.chroma_delta,
        )
    if profile.chroma_dwt == "both":
        ycbcr[:, :, 1] = _embed_dwt_channel(
            ycbcr[:, :, 1].copy(), payload_bits, profile.chroma_delta,
        )

    ycbcr[:, :, 0] = _embed_y_layers(
        ycbcr[:, :, 0], payload_bits, profile, image_h=h, image_w=w,
    )
    return _ycbcr_to_rgb(ycbcr)


def embed_jw_verifiable(
    image: np.ndarray,
    manifest: JwManifest,
    *,
    priority: JwEmbedPriority | str = JwEmbedPriority.AUTO,
    embed_timestamp: int | None = None,
) -> tuple[np.ndarray, bool, str | None]:
    """Embed JW using a texture-first ladder; stop at the first self-verifiable tier.

    Skips uniform (flat) blocks at each tier — no whole-image Y-LL2 grid.
    Returns (image, applied, tier_name).
    """
    if isinstance(priority, str):
        priority = parse_jw_embed_priority(priority)

    flat_ratio = estimate_flat_ratio(image)
    # Large flat art: skip freq tries (slow on big canvases, visible grid if forced).
    # Caller falls back to LSB — fast and invisible on uniform regions.
    if flat_ratio >= _FLAT_RATIO_CHROMA_BLOCK:
        return image.copy(), False, None

    ladder = build_jw_embed_ladder(flat_ratio, priority)

    base = image.copy()
    last = base
    for prof in ladder:
        last = embed_jw_watermark(
            base, manifest, profile=prof, embed_timestamp=embed_timestamp,
        )
        if extract_jw_watermark(last).get("found"):
            return last, True, prof.name
    return last, False, None


def embed_jw_lsb_fallback(
    image: np.ndarray,
    manifest: JwManifest,
    *,
    embed_timestamp: int | None = None,
) -> np.ndarray:
    """Write the JW manifest string into LSB when frequency embed cannot decode."""
    from core.lsb_watermark import embed_lsb_watermark

    payload = encode_jw_lsb_payload(manifest, embed_timestamp=embed_timestamp)
    return embed_lsb_watermark(image, payload)


def extract_jw_for_verify(image: np.ndarray) -> dict:
    """Fast JW verify: LSB backup first, then freq, screenshot recovery last."""
    lsb_hit = extract_jw_from_lsb(image)
    if lsb_hit:
        return lsb_hit
    direct = extract_jw_watermark(image)
    if direct.get("found"):
        return direct
    if not direct.get("decode_hint"):
        return direct
    from core.screenshot_recovery import extract_jw_with_recovery

    return extract_jw_with_recovery(image, initial_result=direct)


def extract_jw_from_lsb(image: np.ndarray) -> dict | None:
    """If LSB holds a JW1 payload, return the same shape as extract_jw_watermark hit."""
    from core.lsb_watermark import extract_lsb_watermark

    try:
        text = extract_lsb_watermark(image)
    except ValueError:
        return None
    manifest, ts = parse_jw_lsb_text(text)
    if manifest is None:
        return None
    return {
        "found": True,
        "confidence": 1.0,
        "channel": "lsb",
        "channels_tried": ["lsb"],
        "per_channel": {"lsb": 1.0},
        "creation": manifest.creation.value,
        "creation_label": (
            "原創 Original" if manifest.creation == JwCreationType.ORIGINAL else "AI 輔助 AI-Assisted"
        ),
        "restrictions": manifest.restriction_abbrevs(),
        "artist": _clean_artist(manifest.artist),
        "artist_hash": manifest.extra.get("artist_hash", ""),
        "badge_text": manifest.badge_text(),
        "timestamp": ts,
        "protected_at": _format_jw_protected_at(ts),
    }


def _badge_icon_specs(manifest: JwManifest) -> list[tuple[str, bool]]:
    """Return (inner label, is_restriction) for each circular badge icon."""
    specs: list[tuple[str, bool]] = [("JW", False)]
    specs.append((manifest.creation.value, False))
    for abbrev in manifest.restriction_abbrevs():
        inner = abbrev.split("-", 1)[1] if "-" in abbrev else abbrev
        specs.append((inner, True))
    return specs


def _badge_font(size: int):
    from PIL import ImageFont

    for path in (
        _ASSETS_DIR / "DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            continue
    return ImageFont.load_default()


def _footer_zh_font(size: int):
    from PIL import ImageFont

    for path in (
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _footer_en_font(size: int):
    return _badge_font(size)


def _region_mean_luma(image: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> float:
    h, w = image.shape[:2]
    x0 = max(0, min(x0, w - 1))
    x1 = max(x0 + 1, min(x1, w))
    y0 = max(0, min(y0, h - 1))
    y1 = max(y0 + 1, min(y1, h))
    patch = image[y0:y1, x0:x1, :3].astype(np.float32)
    return float(0.299 * patch[:, :, 0].mean()
                 + 0.587 * patch[:, :, 1].mean()
                 + 0.114 * patch[:, :, 2].mean())


def _badge_ink_for_luma(luma: float) -> tuple[int, int, int, int]:
    return _BADGE_INK_ON_DARK if luma < _BADGE_LUMA_THRESHOLD else _BADGE_INK


def _draw_badge_icon(
    draw,
    cx: float,
    cy: float,
    radius: float,
    label: str,
    *,
    ink: tuple[int, int, int, int],
    strike: tuple[int, int, int, int],
    font,
    is_restriction: bool,
) -> None:
    stroke = max(2, int(radius * 0.11))
    left = cx - radius
    top = cy - radius
    right = cx + radius
    bottom = cy + radius
    draw.ellipse([left, top, right, bottom], outline=ink, width=stroke)
    if is_restriction:
        pad = radius * 0.62
        draw.line(
            [(cx - pad, cy + pad), (cx + pad, cy - pad)],
            fill=strike,
            width=stroke,
        )
    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    try:
        draw.text((cx, cy), label, font=font, fill=ink, anchor="mm")
    except TypeError:
        draw.text(
            (cx - tw / 2, cy - th / 2 - 1),
            label,
            font=font,
            fill=ink,
        )


def apply_jw_visible_badge(image: np.ndarray, manifest: JwManifest) -> np.ndarray:
    """Draw circular JW symbol row at bottom-right (monochrome, adaptive ink)."""
    if not manifest.visible_badge:
        return image
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        return image

    from PIL import Image, ImageDraw

    h, w = image.shape[:2]
    short = min(h, w)
    icon_r = max(11, int(short * 0.022))
    gap = max(3, int(icon_r * 0.28))
    pad_x = max(6, int(icon_r * 0.35))
    font = _badge_font(max(8, int(icon_r * 0.95)))

    specs = _badge_icon_specs(manifest)
    row_w = len(specs) * (icon_r * 2) + max(0, len(specs) - 1) * gap
    margin = max(10, int(short * 0.022))
    pill_x = max(margin, w - row_w - pad_x * 2 - margin)
    pill_y = max(margin, h - icon_r * 2 - pad_x - margin)
    pill_w = row_w + pad_x * 2
    pill_h = icon_r * 2 + pad_x

    luma = _region_mean_luma(image, pill_x, pill_y, pill_x + pill_w, pill_y + pill_h)
    ink = _badge_ink_for_luma(luma)
    strike = ink

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    cx = w - margin - icon_r - (len(specs) - 1) * (icon_r * 2 + gap)
    cy = h - margin - icon_r
    for label, is_restriction in specs:
        _draw_badge_icon(
            draw, cx, cy, icon_r, label,
            ink=ink, strike=strike, font=font, is_restriction=is_restriction,
        )
        cx += icon_r * 2 + gap

    base = Image.fromarray(image).convert("RGBA")
    return np.array(Image.alpha_composite(base, overlay).convert("RGB"))


_FOOTER_STRIP_HEIGHT_RATIO = 0.108   # ~10.8% of reference height (readable logo + badges)
_FOOTER_STRIP_MAX_HEIGHT_RATIO = 0.144
_FOOTER_PANO_ASPECT = 1.5            # above this, size band by short edge not canvas height


def _format_jw_protected_at(timestamp: int) -> str | None:
    """Format embedded Unix timestamp for verify UI; 0 means not recorded."""
    if timestamp <= 0:
        return None
    try:
        return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
    except (OSError, ValueError, OverflowError):
        return None



_ASSETS_DIR = Path(__file__).resolve().parent / "assets"

_BIRD_PNG_PATHS = [
    _ASSETS_DIR / "jingwei-bird.png",
    Path(__file__).resolve().parent.parent / "frontend" / "src" / "assets" / "jingwei-bird.png",
]

_LOGO_PNG_PATHS = [
    _ASSETS_DIR / "jingwei-logo.png",
    Path(__file__).resolve().parent.parent / "frontend" / "src" / "assets" / "jingwei-logo.png",
]


def _load_rgba_logo(paths: list[Path], target_h: int) -> "Image.Image | None":
    """Load and resize an RGBA logo asset to target height."""
    from PIL import Image as _PILImage

    for p in paths:
        if p.is_file():
            logo = _PILImage.open(p).convert("RGBA")
            bbox = logo.getbbox()
            if bbox:
                logo = logo.crop(bbox)
            ratio = target_h / logo.height
            new_w = max(1, int(logo.width * ratio))
            return logo.resize((new_w, target_h), _PILImage.LANCZOS)
    return None


def _load_bird_logo(target_h: int) -> "Image.Image | None":
    """Load and resize the jingwei bird logo (original colours)."""
    return _load_rgba_logo(_BIRD_PNG_PATHS, target_h)


def _load_footer_logo(target_h: int) -> "Image.Image | None":
    """Load full Jingwei wordmark for footer; fall back to bird-only."""
    return _load_rgba_logo(_LOGO_PNG_PATHS, target_h) or _load_bird_logo(target_h)


def _footer_reference_height(image_h: int, image_w: int) -> int:
    """Panoramas size the band from the short edge so logo/icons stay legible."""
    short = min(image_h, image_w)
    aspect = max(image_w, image_h) / max(short, 1)
    if aspect >= _FOOTER_PANO_ASPECT:
        return short
    return image_h


def _footer_strip_height(image_h: int, image_w: int) -> int:
    ref = _footer_reference_height(image_h, image_w)
    target = int(round(ref * _FOOTER_STRIP_HEIGHT_RATIO))
    cap = int(round(ref * _FOOTER_STRIP_MAX_HEIGHT_RATIO))
    return max(1, min(target, cap))


def _estimate_orig_height_with_footer(total_h: int, total_w: int) -> int | None:
    """Estimate art height before footer strip was appended."""
    h0 = int(round(total_h / (1.0 + _FOOTER_STRIP_HEIGHT_RATIO)))
    for _ in range(4):
        strip = _footer_strip_height(h0, total_w)
        h0 = total_h - strip
    if 64 <= h0 < total_h - 8:
        return h0
    return None


def apply_jw_footer_strip(
    image: np.ndarray,
    manifest: JwManifest,
    *,
    alpha_channel: np.ndarray | None = None,
) -> np.ndarray:
    """Append a white footer strip: logo left, JW badge icons right (single row)."""
    from PIL import Image as _PILImage, ImageDraw

    h, w = image.shape[:2]
    specs = _badge_icon_specs(manifest)
    strip_h = _footer_strip_height(h, w)

    scale = 2
    sw = w * scale
    sh = strip_h * scale
    margin_x = max(22, int(sw * 0.024))
    icon_r = max(12, int(sh * 0.38))
    icon_gap = max(5, int(icon_r * 0.26))
    font = _badge_font(max(10, int(icon_r * 0.72)))
    ink = _BADGE_INK
    strike = _BADGE_INK

    footer_hi = _PILImage.new("RGBA", (sw, sh), (255, 255, 255, 255))
    draw = ImageDraw.Draw(footer_hi)

    logo = _load_footer_logo(int(sh * 0.79))
    left_x = margin_x
    if logo:
        logo_y = (sh - logo.height) // 2
        footer_hi.paste(logo, (left_x, logo_y), logo)
    row_w = len(specs) * (icon_r * 2) + max(0, len(specs) - 1) * icon_gap
    right_start_x = sw - margin_x - row_w - icon_r
    cy = sh // 2
    cx = right_start_x + icon_r
    for label, is_restriction in specs:
        _draw_badge_icon(
            draw, cx, cy, icon_r, label,
            ink=ink, strike=strike, font=font, is_restriction=is_restriction,
        )
        cx += icon_r * 2 + icon_gap

    footer_1x = footer_hi.resize((w, strip_h), _PILImage.LANCZOS)
    footer_arr = np.array(footer_1x)
    footer_arr[:, :, 3] = 255

    if alpha_channel is not None:
        base_rgba = np.dstack([image, alpha_channel])
        combined = np.vstack([base_rgba, footer_arr])
        return combined

    footer_rgb = footer_arr[:, :, :3]
    return np.vstack([image, footer_rgb])


def _channel_decode(bits: np.ndarray, confidence: float) -> tuple[tuple[JwManifest, dict] | None, bool]:
    """Decode one channel. Second value is True when bits look like JW but manifest failed."""
    if confidence < _MIN_CONFIDENCE:
        return None, False
    raw = _decode_bits(bits)
    if raw is None:
        return None, False
    manifest = decode_jw_payload(raw["payload_text"])
    if manifest is None:
        return None, True
    return (manifest, raw), False


def _clean_artist(artist: str) -> str:
    out = ""
    for c in artist:
        if 32 < ord(c) < 127 and c != "?":
            out += c
        else:
            break
    return out


def _jw_extract_canvases(image: np.ndarray) -> list[np.ndarray]:
    """Return canvases to try — art crop first when footer likely, then full frame."""
    h, w = image.shape[:2]
    est_orig_h = _estimate_orig_height_with_footer(h, w)
    if est_orig_h is not None:
        return [image[:est_orig_h, :w], image]
    return [image]


def _extract_jw_from_canvas(image: np.ndarray) -> dict:
    """Extract JW from a single RGB canvas (no footer fallback)."""
    ycbcr = _rgb_to_ycbcr(image)

    layers: list[tuple[str, np.ndarray, float]] = []
    try:
        bits, conf = _extract_dwt_channel(ycbcr[:, :, 2], _DELTA)
        layers.append(("cr", bits, conf))
    except Exception:
        pass
    try:
        bits, conf = _extract_dwt_channel(ycbcr[:, :, 1], _DELTA)
        layers.append(("cb", bits, conf))
    except Exception:
        pass
    y_dwt_best: tuple[np.ndarray, float] | None = None
    for delta in _Y_DWT_EXTRACT_DELTAS:
        try:
            bits, conf = _extract_dwt_channel(ycbcr[:, :, 0], delta)
            if y_dwt_best is None or conf > y_dwt_best[1]:
                y_dwt_best = (bits, conf)
        except Exception:
            pass
    if y_dwt_best is not None:
        layers.append(("y_dwt", y_dwt_best[0], y_dwt_best[1]))
    if image.shape[0] >= 128 and image.shape[1] >= 128:
        try:
            bits, conf = _extract_dct_mid_y(ycbcr[:, :, 0])
            layers.append(("dct", bits, conf))
        except Exception:
            pass
    try:
        bits, conf = _extract_block_dc_y(ycbcr[:, :, 0])
        layers.append(("bdc", bits, conf))
    except Exception:
        pass

    per_channel = {name: round(c, 4) for name, _b, c in layers}
    channels_tried = [name for name, _b, _c in layers]

    if not layers:
        return {"found": False, "channels_tried": channels_tried}

    best: tuple[str, JwManifest, float, dict] | None = None
    decode_hint = False
    for name, bits, conf in layers:
        decoded, hint = _channel_decode(bits, conf)
        decode_hint = decode_hint or hint
        if decoded is None:
            continue
        manifest, raw = decoded
        score = conf * (1.15 if raw.get("checksum_ok") else 1.0)
        if best is None or score > best[2]:
            best = (name, manifest, score, raw)

    if best is None and len(layers) >= 2:
        weighted = np.zeros(_PAYLOAD_BITS, dtype=np.float64)
        weight_sum = 0.0
        for _name, bits, conf in layers:
            if conf <= 0:
                continue
            weighted += bits.astype(np.float64) * conf
            weight_sum += conf
        if weight_sum > 0:
            fused = (weighted / weight_sum > 0.5).astype(np.uint8)
            avg_conf = weight_sum / len(layers)
            decoded, hint = _channel_decode(fused, avg_conf)
            decode_hint = decode_hint or hint
            if decoded is not None:
                manifest, raw = decoded
                best = ("fused", manifest, avg_conf, raw)

    if best is None:
        max_conf = max((c for _n, _b, c in layers), default=0.0)
        return {
            "found": False,
            "confidence": round(max_conf, 4),
            "channels_tried": channels_tried,
            "per_channel": per_channel,
            "decode_hint": decode_hint,
        }

    channel_used, manifest, score, raw = best
    display_conf = min(score, 1.0)
    ts = int(raw.get("timestamp") or 0)
    return {
        "found": True,
        "confidence": round(display_conf, 4),
        "channel": channel_used,
        "channels_tried": channels_tried,
        "per_channel": per_channel,
        "creation": manifest.creation.value,
        "creation_label": "原創 Original" if manifest.creation == JwCreationType.ORIGINAL else "AI 輔助 AI-Assisted",
        "restrictions": manifest.restriction_abbrevs(),
        "artist": _clean_artist(manifest.artist),
        "artist_hash": manifest.extra.get("artist_hash", ""),
        "badge_text": manifest.badge_text(),
        "timestamp": ts,
        "protected_at": _format_jw_protected_at(ts),
    }


def extract_jw_watermark(image: np.ndarray) -> dict:
    """Extract JW manifest. Tries each layer independently, then fusion.

    When a JW footer strip is appended below the art, also tries the main canvas
    crop so verification matches downloaded PNGs.
    """
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        return {"found": False, "error": "Invalid image format"}
    if image.shape[0] < 64 or image.shape[1] < 64:
        return {"found": False, "error": "Image too small for JW detection"}

    best_result: dict | None = None
    best_score = -1.0
    decode_hint = False
    for canvas in _jw_extract_canvases(image):
        result = _extract_jw_from_canvas(canvas)
        decode_hint = decode_hint or bool(result.get("decode_hint"))
        if result.get("found"):
            score = float(result.get("confidence") or 0)
            if best_result is None or score > best_score:
                best_result = result
                best_score = score
        elif best_result is None or not best_result.get("found"):
            score = float(result.get("confidence") or 0)
            if best_result is None or score > best_score:
                best_result = result
                best_score = score

    if best_result is None:
        return {"found": False, "decode_hint": False}
    if not best_result.get("found"):
        best_result["decode_hint"] = decode_hint
    return best_result
