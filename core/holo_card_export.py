"""Export a downloadable flash-card MP4 from a protected still.

The foil is the real HoloCard CSS (``scripts/capture_holo_css.py``), not a
numpy recreation. This module only fits the face, records those frames, and
encodes H.264/MP4 for sharing.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

import numpy as np
from PIL import Image

HOLO_FACE_MAX_EDGE = 1600
HOLO_CLIP_FPS = 8
HOLO_CLIP_FRAMES = 48

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"

CaptureFn = Callable[..., list[np.ndarray]]


class HoloCaptureError(RuntimeError):
    """Chrome / selenium is missing or the CSS recorder cannot start."""


def fit_holo_face(image: np.ndarray, *, max_edge: int = HOLO_FACE_MAX_EDGE) -> np.ndarray:
    """Downscale so the capture window stays fast and memory-bounded."""
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image must be uint8 HxWx3 RGB")
    h, w = image.shape[:2]
    long = max(h, w)
    if long <= max_edge:
        return image
    scale = max_edge / long
    nw = max(2, int(round(w * scale)))
    nh = max(2, int(round(h * scale)))
    return np.asarray(
        Image.fromarray(image).resize((nw, nh), Image.Resampling.LANCZOS),
        dtype=np.uint8,
    )


def _ffmpeg_exe() -> str | None:
    """Prefer the imageio-ffmpeg binary, else a system ``ffmpeg`` on PATH."""
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def _encode_mp4_opencv(frames: list[np.ndarray], path: Path, *, fps: int) -> None:
    """Fallback encoder when ffmpeg H.264 is unavailable."""
    import cv2

    h, w = frames[0].shape[:2]
    h -= h % 2
    w -= w % 2
    if h < 2 or w < 2:
        raise ValueError("frames are too small to encode")
    for fourcc_str in ("avc1", "H264", "mp4v"):
        writer = cv2.VideoWriter(
            str(path),
            cv2.VideoWriter_fourcc(*fourcc_str),
            float(fps),
            (w, h),
        )
        if not writer.isOpened():
            writer.release()
            continue
        try:
            for frame in frames:
                writer.write(cv2.cvtColor(frame[:h, :w], cv2.COLOR_RGB2BGR))
        finally:
            writer.release()
        if path.is_file() and path.stat().st_size > 0:
            return
    raise RuntimeError("unable to encode MP4")


def encode_holo_mp4(frames: list[np.ndarray], *, fps: int = HOLO_CLIP_FPS) -> bytes:
    """Encode captured RGB frames to MP4 bytes (ffmpeg H.264 when available)."""
    if not frames:
        raise ValueError("frames must not be empty")
    with tempfile.TemporaryDirectory(prefix="jw_holo_") as td:
        path = Path(td) / "holo.mp4"
        ffmpeg = _ffmpeg_exe()
        if ffmpeg:
            frame_dir = Path(td) / "frames"
            frame_dir.mkdir()
            for i, frame in enumerate(frames):
                Image.fromarray(frame).save(frame_dir / f"frame_{i:04d}.jpg", quality=94)
            cmd = [
                ffmpeg, "-y",
                "-framerate", str(fps),
                "-i", str(frame_dir / "frame_%04d.jpg"),
                "-c:v", "libx264",
                "-crf", "18",
                "-preset", "fast",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(path),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=300)
                if path.is_file() and path.stat().st_size > 0:
                    return path.read_bytes()
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
                pass
        _encode_mp4_opencv(frames, path, fps=fps)
        return path.read_bytes()


def _is_capture_env_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(token in text for token in ("selenium", "chrome", "chromedriver", "webdriver"))


def _default_capture(image_path: Path, *, n_frames: int) -> list[np.ndarray]:
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    from capture_holo_css import capture_css_frames

    # 2× matches the homepage sample; 48 frames at 8 fps ≈ 6s clip.
    return capture_css_frames(
        image_path,
        n_frames=n_frames,
        scale=2.0,
        window_size="780,1040",
    )


def export_holo_mp4_from_image(
    image: np.ndarray,
    *,
    n_frames: int = HOLO_CLIP_FRAMES,
    fps: int = HOLO_CLIP_FPS,
    capture_frames: CaptureFn | None = None,
) -> bytes:
    """Fit the still, record real CSS foil, return an MP4 byte string.

    ``capture_frames`` is injectable so unit tests do not need Chrome.
    """
    face = fit_holo_face(image)
    capture = capture_frames or _default_capture
    with tempfile.TemporaryDirectory(prefix="jw_holo_face_") as td:
        face_path = Path(td) / "face.jpg"
        Image.fromarray(face).save(face_path, format="JPEG", quality=92, optimize=True)
        try:
            frames = capture(face_path, n_frames=n_frames)
        except HoloCaptureError:
            raise
        except Exception as exc:
            if _is_capture_env_error(exc):
                raise HoloCaptureError(str(exc)) from exc
            raise
        return encode_holo_mp4(frames, fps=fps)
