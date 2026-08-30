"""Live Photo 实验导出：H.264 MOV、Apple 配对元数据、.livp 与相册可导入配对文件。"""

from __future__ import annotations

import plistlib
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

try:
    import piexif
except ImportError:  # pragma: no cover
    piexif = None  # type: ignore[assignment]

# Apple Live Photo：still-image-time 常用 -1（0xFF）
_STILL_IMAGE_TIME = "-1"


def _ensure_rgb_frames(frames: list[np.ndarray]) -> list[np.ndarray]:
    out: list[np.ndarray] = []
    for f in frames:
        if f.dtype != np.uint8 or f.ndim != 3 or f.shape[2] != 3:
            raise ValueError(f"Each frame must be uint8 HxWx3, got {f.shape} {f.dtype}.")
        out.append(f)
    if not out:
        raise ValueError("frames must not be empty.")
    return out


def _ffmpeg_exe() -> str | None:
    """优先 bundled ffmpeg（imageio-ffmpeg），其次系统 PATH。"""
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def _open_video_writer(path: Path, fps: int, size: tuple[int, int]) -> tuple[cv2.VideoWriter, str]:
    w, h = size
    for fourcc_str in ("avc1", "H264", "mp4v"):
        fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
        writer = cv2.VideoWriter(str(path), fourcc, float(fps), (w, h))
        if writer.isOpened():
            return writer, fourcc_str
        writer.release()
    raise RuntimeError(f"无法创建视频写入器：{path}")


def encode_video(
    frames: list[np.ndarray],
    path: str | Path,
    *,
    fps: int,
    container: str = "mp4",
) -> str:
    """OpenCV 编码（预览用）；Live 相册导入请用 ``encode_live_mov``。"""
    frames = _ensure_rgb_frames(frames)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    h, w = frames[0].shape[:2]
    writer, codec = _open_video_writer(out, fps, (w, h))
    try:
        for frame in frames:
            bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            writer.write(bgr)
    finally:
        writer.release()
    if not out.is_file() or out.stat().st_size == 0:
        raise RuntimeError(f"视频编码失败：{out}（codec={codec}）")
    return codec


def encode_preview_mp4(frames: list[np.ndarray], path: str | Path, *, fps: int) -> str:
    return encode_video(frames, path, fps=fps, container="mp4")


def encode_mov(frames: list[np.ndarray], path: str | Path, *, fps: int) -> str:
    """兼容旧调用；内部优先走 Live 级 H.264。"""
    return encode_live_mov(frames, path, fps=fps)


def encode_live_mov(frames: list[np.ndarray], path: str | Path, *, fps: int) -> str:
    """编码 iPhone 相册可识别的 H.264 MOV（yuv420p）。"""
    frames = _ensure_rgb_frames(frames)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg_exe()
    if ffmpeg:
        with tempfile.TemporaryDirectory(prefix="jw_live_") as td:
            td_path = Path(td)
            for i, frame in enumerate(frames):
                Image.fromarray(frame).save(td_path / f"frame_{i:04d}.jpg", quality=92)
            cmd = [
                ffmpeg,
                "-y",
                "-framerate",
                str(fps),
                "-i",
                str(td_path / "frame_%04d.jpg"),
                "-c:v",
                "libx264",
                "-profile:v",
                "main",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(out),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=300)
                if out.is_file() and out.stat().st_size > 0:
                    return "libx264"
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
                pass
    return encode_video(frames, out, fps=fps, container="mov")


def save_key_jpeg(frame: np.ndarray, path: str | Path, *, quality: int = 92) -> None:
    if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError(f"frame must be uint8 HxWx3, got {frame.shape}.")
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(frame).save(out, format="JPEG", quality=quality, optimize=True)


def _apple_maker_note_bytes(content_id: str) -> bytes:
    """Apple MakerNote：键 17 = ContentIdentifier（二进制 plist）。"""
    return plistlib.dumps({17: content_id}, fmt=plistlib.FMT_BINARY)


def _write_jpeg_content_id(jpeg_path: Path, content_id: str) -> bool:
    """写入 Apple Live Photo 所需 JPEG 侧配对元数据。"""
    if piexif is None:
        return False
    try:
        try:
            exif_dict = piexif.load(str(jpeg_path))
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

        if "Exif" not in exif_dict:
            exif_dict["Exif"] = {}
        exif_dict["Exif"][piexif.ExifIFD.MakerNote] = _apple_maker_note_bytes(content_id)
        exif_dict["0th"][piexif.ImageIFD.ImageUniqueID] = content_id.encode("ascii", "ignore")

        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(jpeg_path))
        return True
    except Exception:
        return False


def _finalize_mov_for_live_photo(mov_path: Path, content_id: str) -> tuple[bool, str]:
    """为 MOV 写入 Apple Live 配对元数据（H.264 + content.identifier + still-image-time）。"""
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg:
        return False, "no_ffmpeg"

    tmp = mov_path.with_suffix(".live.mov")
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(mov_path),
        "-c:v",
        "libx264",
        "-profile:v",
        "main",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-metadata",
        f"com.apple.quicktime.content.identifier={content_id}",
        "-metadata",
        f"com.apple.quicktime.still-image-time={_STILL_IMAGE_TIME}",
        str(tmp),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        tmp.replace(mov_path)
        return True, "libx264+metadata"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        # 无法重编码时，尝试 copy 写入元数据
        cmd_copy = [
            ffmpeg,
            "-y",
            "-i",
            str(mov_path),
            "-c",
            "copy",
            "-metadata",
            f"com.apple.quicktime.content.identifier={content_id}",
            "-metadata",
            f"com.apple.quicktime.still-image-time={_STILL_IMAGE_TIME}",
            str(tmp),
        ]
        try:
            subprocess.run(cmd_copy, check=True, capture_output=True, timeout=120)
            tmp.replace(mov_path)
            return True, "copy+metadata"
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            return False, f"metadata_failed:{type(exc).__name__}"


def _prepare_paired_live_assets(
    jpg_path: Path,
    mov_path: Path,
    work_dir: Path,
    *,
    content_id: str | None = None,
) -> tuple[Path, Path, str, str, str, bool, bool, str]:
    if not jpg_path.is_file():
        raise FileNotFoundError(jpg_path)
    if not mov_path.is_file():
        raise FileNotFoundError(mov_path)

    cid = content_id or str(uuid.uuid4()).upper()
    stem = f"IMG_{uuid.uuid4().hex[:8].upper()}"
    jpg_name = f"{stem}.JPG"
    mov_name = f"{stem}.MOV"

    work_dir.mkdir(parents=True, exist_ok=True)
    work_jpg = work_dir / jpg_name
    work_mov = work_dir / mov_name
    shutil.copy2(jpg_path, work_jpg)
    shutil.copy2(mov_path, work_mov)

    jpeg_paired = _write_jpeg_content_id(work_jpg, cid)
    mov_paired, mov_codec = _finalize_mov_for_live_photo(work_mov, cid)
    return work_jpg, work_mov, cid, jpg_name, mov_name, jpeg_paired, mov_paired, mov_codec


def export_live_photo_pair(
    jpg_path: str | Path,
    mov_path: str | Path,
    out_dir: str | Path,
    *,
    content_id: str | None = None,
    export_basename: str | None = None,
) -> dict[str, str | bool]:
    """导出相册可导入的配对 ``IMG_xxxx.JPG`` + ``IMG_xxxx.MOV``（推荐 AirDrop）。"""
    out = Path(out_dir)
    work_jpg, work_mov, cid, jpg_name, mov_name, jpeg_paired, mov_paired, mov_codec = (
        _prepare_paired_live_assets(
            Path(jpg_path), Path(mov_path), out, content_id=content_id
        )
    )

    if export_basename:
        dest_jpg = out / f"{export_basename}.JPG"
        dest_mov = out / f"{export_basename}.MOV"
    else:
        dest_jpg = out / jpg_name
        dest_mov = out / mov_name

    if dest_jpg.resolve() != work_jpg.resolve():
        shutil.copy2(work_jpg, dest_jpg)
    if dest_mov.resolve() != work_mov.resolve():
        shutil.copy2(work_mov, dest_mov)

    if dest_jpg.resolve() != work_jpg.resolve():
        work_jpg.unlink(missing_ok=True)
    if dest_mov.resolve() != work_mov.resolve():
        work_mov.unlink(missing_ok=True)

    return {
        "content_id": cid,
        "jpeg_paired": jpeg_paired,
        "mov_paired": mov_paired,
        "mov_codec": mov_codec,
        "jpg_path": str(dest_jpg),
        "mov_path": str(dest_mov),
        "jpg_name": dest_jpg.name,
        "mov_name": dest_mov.name,
        "pair_stem": dest_jpg.stem,
    }


def package_live_livp(
    jpg_path: str | Path,
    mov_path: str | Path,
    out_livp: str | Path,
    *,
    content_id: str | None = None,
) -> dict[str, str | bool]:
    """打包 ``.livp``（ZIP 容器）。注意：iPhone 相册通常无法直接打开 .livp，请优先用配对 JPG+MOV。"""
    jpg = Path(jpg_path)
    mov = Path(mov_path)
    out = Path(out_livp)
    if out.suffix.lower() != ".livp":
        raise ValueError(f"out_livp must use .livp extension, got {out.suffix!r}")

    work_jpg, work_mov, cid, jpg_name, mov_name, jpeg_paired, mov_paired, mov_codec = (
        _prepare_paired_live_assets(jpg, mov, out.parent, content_id=content_id)
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.write(work_jpg, jpg_name)
        zf.write(work_mov, mov_name)

    work_jpg.unlink(missing_ok=True)
    work_mov.unlink(missing_ok=True)

    return {
        "content_id": cid,
        "jpeg_paired": jpeg_paired,
        "mov_paired": mov_paired,
        "mov_codec": mov_codec,
        "livp_stem": Path(jpg_name).stem,
        "jpg_entry": jpg_name,
        "mov_entry": mov_name,
    }


def package_live_zip(
    jpg_path: str | Path,
    mov_path: str | Path,
    out_zip: str | Path,
    *,
    content_id: str | None = None,
) -> dict[str, str | bool]:
    jpg = Path(jpg_path)
    mov = Path(mov_path)
    out = Path(out_zip)

    work_jpg, work_mov, cid, jpg_name, mov_name, jpeg_paired, mov_paired, mov_codec = (
        _prepare_paired_live_assets(jpg, mov, out.parent, content_id=content_id)
    )

    readme = (
        "精卫 Live 反光实验包\n"
        "==================\n\n"
        f"Content ID: {cid}\n"
        f"MOV: {mov_codec}\n"
        f"JPEG 配对: {'是' if jpeg_paired else '否'}\n"
        f"MOV 配对: {'是' if mov_paired else '否'}\n\n"
        "导入 iPhone 相册：请 AirDrop 同文件夹内 IMG_xxxx.JPG 与 IMG_xxxx.MOV 两个文件。\n"
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(work_jpg, jpg_name)
        zf.write(work_mov, mov_name)
        zf.writestr("导入说明.txt", readme.encode("utf-8"))

    work_jpg.unlink(missing_ok=True)
    work_mov.unlink(missing_ok=True)

    return {
        "content_id": cid,
        "jpeg_paired": jpeg_paired,
        "mov_paired": mov_paired,
        "mov_codec": mov_codec,
        "zip_stem": Path(jpg_name).stem,
    }
