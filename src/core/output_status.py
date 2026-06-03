"""输出状态、质量门控与缓存扫描工具。"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

MIN_RELIABLE_TEXT_CHARS = 200
SUMMARY_SKIP_MESSAGE = "内容过短，无法生成可靠摘要"
LOW_QUALITY_WARNING = "转写内容过短，结果可能不可靠"


def is_text_too_short(text: str | None, min_chars: int = MIN_RELIABLE_TEXT_CHARS) -> bool:
    """判断文本是否短到不适合生成可靠摘要。"""
    return len((text or "").strip()) < min_chars


def build_quality_warning(text: str | None) -> str | None:
    """根据原始转写文本返回质量警告。"""
    if is_text_too_short(text):
        return LOW_QUALITY_WARNING
    return None


def should_skip_summary(
    polished_text: str | None,
    source_text: str | None = None,
    min_chars: int = MIN_RELIABLE_TEXT_CHARS,
) -> bool:
    """摘要前置门控，任一输入文本过短都跳过 LLM 摘要。"""
    if is_text_too_short(polished_text, min_chars=min_chars):
        return True
    return source_text is not None and is_text_too_short(source_text, min_chars=min_chars)


def extract_bvid(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(BV[a-zA-Z0-9]+)", value)
    return match.group(1) if match else None


def normalize_output_status(
    output_dir: str | Path,
    requested_status: str = "completed",
    output_style: str | None = None,
) -> str:
    """根据目录实际产物修正输出状态。"""
    if requested_status == "failed":
        return "failed"

    directory = Path(output_dir)
    has_polish = (directory / "polish_text.txt").exists() or (
        directory / "merged_polish_text.txt"
    ).exists()
    has_pdf = any(directory.glob("*.pdf"))

    style = output_style or ""
    pdf_required = style in ("", "pdf_only", "pdf_with_img")
    if not has_polish or (pdf_required and not has_pdf):
        return "partial"
    return requested_status


def build_result_metadata(
    output_dir: str | Path,
    status: str = "completed",
    *,
    source_url: str | None = None,
    title: str | None = None,
    bvid: str | None = None,
    created_at: str | None = None,
    completed_at: str | None = None,
    audio_text: str | None = None,
    polished_text: str | None = None,
    summary_text: str | None = None,
    model_config: dict[str, Any] | None = None,
    quality_warning: str | None = None,
    output_style: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """构造 result.json 的稳定元数据。"""
    directory = Path(output_dir)
    resolved_status = normalize_output_status(directory, status, output_style)
    summary = summary_text or _read_text(directory / "summary_text.md")
    audio = (
        audio_text if audio_text is not None else _read_text(directory / "audio_transcription.txt")
    )
    polish = polished_text if polished_text is not None else _read_polished_text(directory)

    data: dict[str, Any] = {
        "status": resolved_status,
        "output_status": resolved_status,
        "source_url": source_url or "",
        "title": title or "",
        "bvid": bvid or extract_bvid(source_url) or extract_bvid(str(directory)) or "",
        "created_at": created_at,
        "completed_at": completed_at,
        "audio_chars": len((audio or "").strip()),
        "polish_chars": len((polish or "").strip()),
        "summary_chars": len((summary or "").strip()),
        "has_pdf": any(directory.glob("*.pdf")),
        "has_zip": directory.with_suffix(".zip").exists() or any(directory.glob("*.zip")),
        "model_config": model_config or {},
        "quality_warning": quality_warning or build_quality_warning(audio),
    }
    if extra:
        data.update(extra)
    return data


def write_result_metadata(
    output_dir: str | Path,
    status: str = "completed",
    **kwargs: Any,
) -> dict[str, Any]:
    """写入 result.json；保留既有 result 字段并补齐生产状态字段。"""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    result_path = directory / "result.json"
    existing: dict[str, Any] = {}
    if result_path.exists():
        try:
            loaded = json.loads(result_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing = loaded
        except Exception:
            existing = {}

    existing.update(build_result_metadata(directory, status=status, **kwargs))
    result_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    return existing


def scan_output_cache(output_root: str | Path, keep_per_bvid: int = 3) -> dict[str, Any]:
    """扫描 out 目录，返回半成品、重复目录和 dry-run 清理候选。"""
    root = Path(output_root)
    if not root.exists():
        return {
            "total_cache_size": 0,
            "directories": [],
            "partial_directories": [],
            "duplicate_groups": [],
            "cleanup_candidates": [],
        }

    entries = [_scan_output_directory(path) for path in root.iterdir() if path.is_dir()]
    entries.sort(key=lambda item: item["created_at"] or item["name"], reverse=True)

    groups: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        bvid = entry.get("bvid")
        if bvid:
            groups.setdefault(bvid, []).append(entry)

    duplicate_groups = []
    cleanup_candidates = []
    for bvid, group in sorted(groups.items()):
        if len(group) <= 1:
            continue
        sorted_group = sorted(group, key=lambda item: item["created_at"] or "", reverse=True)
        duplicate_groups.append(
            {
                "bvid": bvid,
                "count": len(sorted_group),
                "directories": [item["path"] for item in sorted_group],
            }
        )
        cleanup_candidates.extend(sorted_group[max(keep_per_bvid, 0) :])

    partial_directories = [entry for entry in entries if entry["status"] == "partial"]
    return {
        "total_cache_size": sum(entry["size_bytes"] for entry in entries),
        "directories": entries,
        "partial_directories": partial_directories,
        "duplicate_groups": duplicate_groups,
        "cleanup_candidates": cleanup_candidates,
    }


def _scan_output_directory(path: Path) -> dict[str, Any]:
    result_json = _read_json(path / "result.json")
    bvid = result_json.get("bvid") or extract_bvid(path.name) or _read_bvid_from_video_info(path)
    status = result_json.get("status") or _infer_directory_status(path)
    created_at = result_json.get("created_at") or _format_timestamp(path.stat().st_ctime)
    audio_text = _read_text(path / "audio_transcription.txt")
    return {
        "name": path.name,
        "path": str(path),
        "bvid": bvid or "",
        "status": status,
        "created_at": created_at,
        "completed_at": result_json.get("completed_at"),
        "audio_chars": result_json.get("audio_chars", len(audio_text.strip())),
        "polish_chars": result_json.get("polish_chars", _read_polish_len(path)),
        "summary_chars": result_json.get("summary_chars", _text_len(path / "summary_text.md")),
        "has_pdf": result_json.get("has_pdf", any(path.glob("*.pdf"))),
        "has_zip": result_json.get("has_zip", path.with_suffix(".zip").exists()),
        "quality_warning": result_json.get("quality_warning") or build_quality_warning(audio_text),
        "size_bytes": _directory_size(path),
    }


def _infer_directory_status(path: Path) -> str:
    has_audio = (path / "audio_transcription.txt").exists()
    has_polish = (path / "polish_text.txt").exists() or (path / "merged_polish_text.txt").exists()
    has_pdf = any(path.glob("*.pdf"))
    if has_audio and has_polish and has_pdf:
        return "completed"
    return "partial"


def _read_polished_text(path: Path) -> str:
    return _read_text(path / "polish_text.txt") or _read_text(path / "merged_polish_text.txt")


def _read_polish_len(path: Path) -> int:
    return len(_read_polished_text(path).strip())


def _text_len(path: Path) -> int:
    return len(_read_text(path).strip())


def _read_text(path: Path) -> str:
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    except Exception:
        return ""
    return ""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        return {}
    return {}


def _read_bvid_from_video_info(path: Path) -> str | None:
    for candidate in ("video_info.txt", "result.json"):
        bvid = extract_bvid(_read_text(path / candidate))
        if bvid:
            return bvid
    return None


def _directory_size(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                continue
    return total


def _format_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).isoformat()
