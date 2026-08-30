"""C2PA manifest read + human-readable summary for verification (no signing)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.compliance_metadata import C2PA_AVAILABLE, read_compliance_metadata


def _walk(obj: Any) -> list[Any]:
    out: list[Any] = []
    if isinstance(obj, dict):
        out.append(obj)
        for v in obj.values():
            out.extend(_walk(v))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(_walk(item))
    return out


def _first_str(data: dict[str, Any], *keys: str) -> str | None:
    for k in keys:
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _extract_from_manifest_tree(raw: dict[str, Any]) -> dict[str, Any]:
    """Best-effort parse of c2pa-python Reader.json() output."""
    nodes = _walk(raw)
    generator: str | None = None
    software: str | None = None
    digital_source: str | None = None
    actions: list[str] = []
    do_not_train: str | None = None
    title: str | None = None
    author: str | None = None

    for node in nodes:
        if not isinstance(node, dict):
            continue
        if generator is None:
            generator = _first_str(node, "claim_generator", "claimGenerator", "generator")
        if software is None:
            software = _first_str(node, "softwareAgent", "software_agent")
        if digital_source is None:
            digital_source = _first_str(
                node,
                "digitalSourceType",
                "digital_source_type",
                "digitalSource",
            )
        if title is None:
            title = _first_str(node, "title", "dc:title")
        if author is None:
            author = _first_str(node, "author", "dc:creator", "creator")

        label = node.get("label") or node.get("assertion_label")
        if isinstance(label, str):
            label_l = label.lower()
            if "action" in label_l or label.endswith(".actions"):
                data = node.get("data") or node.get("actions") or node
                if isinstance(data, dict):
                    acts = data.get("actions") or data.get("action")
                    if isinstance(acts, list):
                        for a in acts:
                            if isinstance(a, dict):
                                act = a.get("action") or a.get("type")
                                if act:
                                    actions.append(str(act))
                            elif a:
                                actions.append(str(a))
                    elif isinstance(acts, str):
                        actions.append(acts)
                elif isinstance(data, list):
                    for a in data:
                        if isinstance(a, dict) and a.get("action"):
                            actions.append(str(a["action"]))
            if "training" in label_l or "datamining" in label_l:
                data = node.get("data") or node
                if isinstance(data, dict):
                    dnt = data.get("entries") or data.get("use") or data.get("training")
                    if dnt is not None:
                        do_not_train = str(dnt)

        if do_not_train is None and "cawg" in str(node.get("label", "")).lower():
            data = node.get("data")
            if isinstance(data, dict):
                for k, v in data.items():
                    if "train" in k.lower():
                        do_not_train = str(v)

    # Top-level validation status if present
    validated = raw.get("validation_status")
    if validated is None:
        validated = raw.get("validationStatus")
    sig_ok = raw.get("signature_valid")
    if sig_ok is None:
        sig_ok = raw.get("signatureValid")

    return {
        "claim_generator": generator,
        "software_agent": software,
        "digital_source_type": digital_source,
        "title": title,
        "author": author,
        "actions": list(dict.fromkeys(actions))[:12],
        "training_policy": do_not_train,
        "validation_status": validated,
        "signature_valid": sig_ok,
    }


def summarize_c2pa_raw(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Turn raw C2PA JSON into verify API payload."""
    if raw is None:
        return {
            "found": False,
            "available": False,
            "hint": "未安装 c2pa-python，无法读取 C2PA。验证 JW/DWT 不受影响。",
        }
    if not raw:
        return {
            "found": False,
            "available": True,
            "hint": "此文件未检测到 C2PA Content Credentials。",
        }

    parsed = _extract_from_manifest_tree(raw)
    has_signal = any([
        parsed.get("claim_generator"),
        parsed.get("digital_source_type"),
        parsed.get("author"),
        parsed.get("actions"),
        parsed.get("training_policy"),
    ])

    return {
        "found": bool(has_signal),
        "available": True,
        "claim_generator": parsed.get("claim_generator"),
        "software_agent": parsed.get("software_agent"),
        "digital_source_type": parsed.get("digital_source_type"),
        "title": parsed.get("title"),
        "author": parsed.get("author"),
        "actions": parsed.get("actions") or [],
        "training_policy": parsed.get("training_policy"),
        "signature_valid": parsed.get("signature_valid"),
        "validation_status": parsed.get("validation_status"),
        "hint": None if has_signal else "检测到 C2PA 结构但未能解析关键字段。",
    }


def read_c2pa_from_path(path: str | Path) -> dict[str, Any]:
    """Read file and return C2PA verify summary."""
    if not C2PA_AVAILABLE:
        return summarize_c2pa_raw(None)
    meta = read_compliance_metadata(path)
    raw = meta.get("c2pa")
    if raw is None:
        return summarize_c2pa_raw(None)
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = {}
    if not isinstance(raw, dict):
        raw = {}
    return summarize_c2pa_raw(raw)
