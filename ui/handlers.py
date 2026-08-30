"""UI 純邏輯層 — 影像保護處理、指標格式化、品質評定、水印驗證。

All fonts are system-installed; no network requests.
"""

from __future__ import annotations

import html
import tempfile
import warnings
from pathlib import Path
from typing import Any, Literal

import numpy as np
from PIL import Image

from core.compliance_metadata import (
    embed_compliance_metadata,
    read_compliance_metadata,
)
from core.lsb_watermark import extract_lsb_watermark
from core.pipeline import protect_image
from evaluation.psnr_ssim import evaluate_protection
from evaluation.visualize import generate_comparison

_TEMP_DIR = Path(tempfile.gettempdir()) / "ai_protect_tool"
_TEMP_DIR.mkdir(parents=True, exist_ok=True)


def _new_temp_path(suffix: str = ".png") -> str:
    _TEMP_DIR.mkdir(parents=True, exist_ok=True)
    fd = tempfile.NamedTemporaryFile(
        suffix=suffix, delete=False, dir=str(_TEMP_DIR)
    )
    path = fd.name
    fd.close()
    return path


def _new_temp_png() -> str:
    return _new_temp_path(".png")


def process_image(
    image_array: np.ndarray | None,
    level: Literal["light", "standard", "strong"],
    watermark_text: str | None,
    visible_watermark_text: str | None,
    artist: str | None,
    embed_metadata: bool,
    *,
    delivery_mode: bool = False,
    protection_mode: str | None = None,
    delivery_text: str | None = "",
    poison_commands: list[str] | str | None = None,
    face_shield: bool = False,
    artist_signature: str | None = "",
    artist_signature_position: Literal[
        "bottom_right", "bottom_left", "top_right", "top_left"
    ] = "bottom_right",
    output_format: Literal["png", "jpg"] = "png",
    blur_bar: bool = False,
    blur_bar_text: str | None = "",
    blur_bar_position: str = "below_face",
    blur_bar_sigma: int = 12,
    emboss: bool = False,
    emboss_pattern: str = "diagonal",
    emboss_intensity: float = 0.28,
    emboss_text: str = "",
    emboss_text_density: str = "normal",
    emboss_strength: str | None = None,
    displacement: bool = False,
    displacement_text: str = "",
    displacement_shift: int = 10,
    displacement_density: str = "normal",
    displacement_font_ratio: float = 0.15,
    displacement_mode: str = "scatter",
    displacement_seed: int = 42,
    displacement_shadow: bool = False,
    displacement_anchor_x: float = -1.0,
    displacement_anchor_y: float = -1.0,
    face_emboss_text: str = "",
    face_emboss_copies: int = 1,
    face_emboss_seed: int = 42,
    face_emboss_patch_ratio: float = 0.30,
    face_emboss_shift: int = 12,
    face_emboss_opacity: float = 0.25,
    dwt_payload: str = "",
    blur_bar_count: int = 1,
    blur_bar_y_ratio: float = -1.0,
    skip_disk_artifacts: bool = False,
) -> dict[str, Any]:
    """保護影像並計算品質指標。

    raise / warn 契約
    ------------------
    **raise ValueError**（UI 以 try/except 捕捉並顯示中文錯誤）：
    - ``image_array is None``
    - ``H < 64 or W < 64`` → "图片太小，请上传至少 64x64 像素的图片"
    - ``dtype ≠ uint8 or ndim ≠ 3 or shape[2] ≠ 3`` → "图片格式不支持，请上传 RGB 图片"

    **收集至 status（不 raise）**：
    - M5 visible watermark 在非 strong 的 ``UserWarning``
    - ``embed_metadata=True`` 但 ``artist`` 為空 → 中文提示，跳過 M10
    - M10 後端降級 ``UserWarning``

    Returns
    -------
    dict
        ``protected_array``, ``metrics``, ``comparison_path``,
        ``output_path``, ``status``, ``quality_label``, ``quality_text``
    """
    if image_array is None:
        raise ValueError("请先上传图片")

    if image_array.dtype != np.uint8 or image_array.ndim != 3 or image_array.shape[2] != 3:
        raise ValueError("图片格式不支持，请上传 RGB 图片")

    h, w = image_array.shape[:2]
    if h < 64 or w < 64:
        raise ValueError("图片太小，请上传至少 64x64 像素的图片")

    # Gradio Textbox 清空時可能傳 None；統一為 str 再 strip
    artist = (artist or "").strip()
    watermark_text = (watermark_text or "").strip()
    visible_watermark_text = (visible_watermark_text or "").strip()
    delivery_text = (delivery_text or "").strip()
    artist_signature = (artist_signature or "").strip()
    blur_bar_text = (blur_bar_text or "").strip()

    if isinstance(poison_commands, str):
        _raw_pc = poison_commands or ""
        _lines = [ln.strip() for ln in _raw_pc.splitlines() if ln.strip()]
        poison_commands = _lines if _lines else None
    elif poison_commands is not None:
        _cleaned: list[str] = []
        for _x in poison_commands:
            if _x is None:
                continue
            _s = str(_x).strip()
            if _s:
                _cleaned.append(_s)
        poison_commands = _cleaned if _cleaned else None

    status_msgs: list[str] = []

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        protected = protect_image(
            image_array,
            level=level,
            watermark_text=watermark_text,
            visible_watermark_text=visible_watermark_text,
            delivery_mode=delivery_mode,
            protection_mode=protection_mode,
            delivery_text=delivery_text,
            poison_commands=poison_commands,
            face_shield=face_shield,
            artist_signature=artist_signature,
            artist_signature_position=artist_signature_position,
            blur_bar=blur_bar,
            blur_bar_text=blur_bar_text,
            blur_bar_position=blur_bar_position,
            blur_bar_sigma=blur_bar_sigma,
            emboss=emboss,
            emboss_pattern=emboss_pattern,
            emboss_intensity=emboss_intensity,
            emboss_text=emboss_text,
            emboss_text_density=emboss_text_density,
            emboss_strength=emboss_strength,
            displacement=displacement,
            displacement_text=displacement_text,
            displacement_shift=displacement_shift,
            displacement_density=displacement_density,
            displacement_font_ratio=displacement_font_ratio,
            displacement_mode=displacement_mode,
            displacement_seed=displacement_seed,
            displacement_shadow=displacement_shadow,
            displacement_anchor_x=displacement_anchor_x,
            displacement_anchor_y=displacement_anchor_y,
            face_emboss_text=face_emboss_text,
            face_emboss_copies=face_emboss_copies,
            face_emboss_seed=face_emboss_seed,
            face_emboss_patch_ratio=face_emboss_patch_ratio,
            face_emboss_shift=face_emboss_shift,
            face_emboss_opacity=face_emboss_opacity,
            dwt_payload=dwt_payload,
            blur_bar_count=blur_bar_count,
            blur_bar_y_ratio=blur_bar_y_ratio,
        )
    for w_item in caught:
        if issubclass(w_item.category, UserWarning):
            status_msgs.append(str(w_item.message))

    metrics = evaluate_protection(image_array, protected)
    quality_label, quality_text = quality_assessment(metrics["psnr"])

    output_path = ""
    comparison_path = ""

    if not skip_disk_artifacts:
        fmt = (output_format or "png").lower()
        if fmt not in ("png", "jpg", "jpeg"):
            fmt = "png"
        suffix = ".png" if fmt == "png" else ".jpg"
        output_path = _new_temp_path(suffix)
        pil_protected = Image.fromarray(protected)
        if fmt == "png":
            pil_protected.save(output_path, format="PNG")
        else:
            pil_protected.save(output_path, format="JPEG", quality=95)

        comparison_path = _new_temp_png()
        generate_comparison(image_array, protected, comparison_path)

        if embed_metadata:
            if artist:
                with warnings.catch_warnings(record=True) as m10_caught:
                    warnings.simplefilter("always")
                    try:
                        embed_compliance_metadata(output_path, artist=artist)
                    except Exception as exc:
                        status_msgs.append(f"元数据嵌入失败：{exc}")
                for w_item in m10_caught:
                    if issubclass(w_item.category, UserWarning):
                        status_msgs.append(str(w_item.message))
            else:
                status_msgs.append("需要填写作者姓名才能嵌入元数据，已跳过元数据嵌入")

    return {
        "protected_array": protected,
        "metrics": metrics,
        "comparison_path": comparison_path,
        "output_path": output_path,
        "status": "; ".join(status_msgs) if status_msgs else "",
        "quality_label": quality_label,
        "quality_text": quality_text,
    }


def generate_output_filename(input_filename: str, level: str) -> str:
    """建議輸出檔名：``{stem}_protected_{level}.png``。"""
    stem = Path(input_filename).stem
    return f"{stem}_protected_{level}.png"


def quality_assessment(psnr: float) -> tuple[str, str]:
    """依 PSNR 回傳 ``(label, text)``。"""
    if psnr >= 38:
        return ("success", "视觉无感")
    if psnr >= 32:
        return ("warning", "轻微可见")
    return ("danger", "明显可见")


def verify_image(image_array: np.ndarray | None) -> str:
    """提取 LSB 水印 + 讀取元數據，回傳 HTML 報告。

    Parameters
    ----------
    image_array:
        Gradio numpy 上傳；若為 None 回傳「請上傳」提示。

    Returns
    -------
    str
        HTML 字串，含 LSB 結果 + 元數據結果，分區呈現。
    """
    if image_array is None:
        return (
            '<div class="verify-result fail">'
            '<h4>未上傳圖片</h4>'
            '請先在左側上傳要驗證的圖片。'
            '</div>'
        )

    parts: list[str] = []

    # 0) DWT frequency-domain watermark extraction
    try:
        from core.dwt_watermark import extract_dwt_watermark
        dwt_result = extract_dwt_watermark(image_array)
        conf = dwt_result.get("confidence", 0)
        payload_text = dwt_result.get("payload_text", "")
        ts = dwt_result.get("timestamp", 0)
        if conf >= 0.60 and payload_text:
            import datetime
            ts_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts > 0 else "--"
            parts.append(
                '<div class="verify-result ok">'
                '<h4>DWT 频域水印（抗截图/抗压缩）</h4>'
                f'<div>嵌入内容：<code>{html.escape(payload_text)}</code></div>'
                f'<div>嵌入时间：<code>{ts_str}</code></div>'
                f'<div>置信度：<code>{conf:.1%}</code></div>'
                '<div style="margin-top:6px;font-size:11px;opacity:0.8">'
                'DWT 水印嵌入在频域低频系数中，可抗 JPEG 压缩、截图、社媒转存。'
                '</div>'
                '</div>'
            )
        else:
            parts.append(
                '<div class="verify-result fail">'
                '<h4>未检测到 DWT 频域水印</h4>'
                f'<div>置信度过低（{conf:.1%}），可能未嵌入或图片被严重修改。</div>'
                '</div>'
            )
    except Exception as exc:
        parts.append(
            '<div class="verify-result fail">'
            '<h4>DWT 提取失败</h4>'
            '<div>{}</div>'
            '</div>'.format(html.escape(str(exc)))
        )

    # 1) LSB extraction (works directly on numpy)
    try:
        if image_array.dtype != np.uint8 or image_array.ndim != 3:
            raise ValueError("圖片格式不正確，需為 uint8 RGB。")
        text = extract_lsb_watermark(image_array)
        safe = html.escape(text)
        parts.append(
            '<div class="verify-result ok">'
            '<h4>✓ LSB 隐写水印</h4>'
            '<div>检测到水印：<code>{}</code></div>'
            '<div style="margin-top:6px;font-size:11px;opacity:0.8">'
            '此为像素级隐写，可作为法律证据（仅原始文件有效）。'
            '</div>'
            '</div>'.format(safe)
        )
    except ValueError as exc:
        parts.append(
            '<div class="verify-result fail">'
            '<h4>✗ 未检测到 LSB 水印</h4>'
            '<div>{}</div>'
            '<div style="margin-top:6px;font-size:11px;opacity:0.8">'
            '可能原因：未嵌入水印，或图片经过截图/JPEG 压缩破坏了 LSB。'
            '</div>'
            '</div>'.format(html.escape(str(exc)))
        )
    except Exception as exc:  # pragma: no cover
        parts.append(
            '<div class="verify-result fail">'
            '<h4>✗ LSB 提取失败</h4>'
            '<div>{}</div>'
            '</div>'.format(html.escape(str(exc)))
        )

    # 2) Metadata: requires a file path. Save the uploaded array as temp PNG
    #    and try both PNG-chunk and EXIF reads.  If the upload was originally
    #    a JPEG, the EXIF lives in the original bytes — but Gradio gives us a
    #    decoded ndarray, not the original file.  So this branch only
    #    detects metadata that survived Gradio's load (PNG tEXt does).
    tmp_path = _new_temp_path(".png")
    try:
        Image.fromarray(image_array).save(tmp_path, format="PNG")

        try:
            meta = read_compliance_metadata(tmp_path)
            exif = meta.get("exif")
            iptc = meta.get("iptc")
            lines: list[str] = []
            if exif and any(exif.values()):
                artist = exif.get("artist") or "—"
                cr = exif.get("copyright") or "—"
                lines.append(
                    '<div>EXIF Artist：<code>{}</code></div>'
                    '<div>EXIF Copyright：<code>{}</code></div>'.format(
                        html.escape(str(artist)), html.escape(str(cr))
                    )
                )
            if iptc and any(iptc.values()):
                by = iptc.get("by_line") or "—"
                cr = iptc.get("copyright_notice") or "—"
                sp = iptc.get("special_instructions") or "—"
                lines.append(
                    '<div>IPTC By-line：<code>{}</code></div>'
                    '<div>IPTC Copyright：<code>{}</code></div>'
                    '<div>IPTC Instructions：<code>{}</code></div>'.format(
                        html.escape(str(by)),
                        html.escape(str(cr)),
                        html.escape(str(sp)),
                    )
                )
            if lines:
                parts.append(
                    '<div class="verify-result ok">'
                    '<h4>✓ 版权元数据</h4>'
                    + "".join(lines)
                    + '</div>'
                )
            else:
                parts.append(
                    '<div class="verify-result fail">'
                    '<h4>✗ 未检测到元数据</h4>'
                    '<div>Gradio 上传时通常会丢弃 JPEG 元数据。'
                    '如需验证元数据请直接读取原始文件，不要经过浏览器上传。</div>'
                    '</div>'
                )
        except Exception as exc:  # pragma: no cover
            parts.append(
                '<div class="verify-result fail">'
                '<h4>✗ 元数据读取失败</h4>'
                '<div>{}</div>'
                '</div>'.format(html.escape(str(exc)))
            )

    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return "".join(parts)


def reencode_protected(
    source_path: str | None,
    output_format: Literal["png", "jpg"] = "png",
) -> str | None:
    """Re-encode an existing protected image into a different container.

    Used by the UI to flip PNG ↔ JPG without re-running the protection
    pipeline.  Returns the new temp-file path (or None on missing input).
    """
    if not source_path:
        return None
    fmt = (output_format or "png").lower()
    if fmt not in ("png", "jpg", "jpeg"):
        fmt = "png"
    suffix = ".png" if fmt == "png" else ".jpg"
    new_path = _new_temp_path(suffix)
    with Image.open(source_path) as im:
        im = im.convert("RGB")
        if fmt == "png":
            im.save(new_path, format="PNG")
        else:
            im.save(new_path, format="JPEG", quality=95)
    return new_path


def format_metrics_html(
    metrics: dict[str, Any],
    quality_label: str,
    quality_text: str,
) -> str:
    """將指標格式化為 HTML，含 metric-badge。"""
    psnr = metrics.get("psnr", 0.0)
    psnr_s = "\u221e" if psnr == float("inf") else "{:.2f}".format(psnr)
    ssim_s = "{:.4f}".format(metrics.get("ssim", 0.0))
    max_d = metrics.get("max_diff", 0)
    mean_s = "{:.2f}".format(metrics.get("mean_diff", 0.0))

    return (
        '<div style="line-height:2.2">'
        '<span class="metric-badge {label}">{qtext}</span> '
        "<b>PSNR:</b> {psnr} dB &nbsp; "
        "<b>SSIM:</b> {ssim} &nbsp; "
        "<b>Max diff:</b> {maxd} &nbsp; "
        "<b>Mean diff:</b> {meand}"
        "</div>"
    ).format(
        label=quality_label,
        qtext=quality_text,
        psnr=psnr_s,
        ssim=ssim_s,
        maxd=max_d,
        meand=mean_s,
    )
