"""输出缓存治理质量测试。"""

import json

from src.core.output_status import scan_output_cache, write_result_metadata


def _make_output_dir(root, name, *, bvid, audio, polish="", summary="", pdf=True):
    output_dir = root / name
    output_dir.mkdir(parents=True)
    (output_dir / "audio_transcription.txt").write_text(audio, encoding="utf-8")
    if polish:
        (output_dir / "polish_text.txt").write_text(polish, encoding="utf-8")
    if summary:
        (output_dir / "summary_text.md").write_text(summary, encoding="utf-8")
    if pdf:
        (output_dir / "output.pdf").write_bytes(b"%PDF-1.4")
    (output_dir / "video_info.txt").write_text(
        json.dumps({"url": f"https://www.bilibili.com/video/{bvid}", "title": name}),
        encoding="utf-8",
    )
    return output_dir


def test_write_result_metadata_marks_partial_and_quality_warning(tmp_path):
    output_dir = _make_output_dir(
        tmp_path,
        "BV16cNEeXEer",
        bvid="BV16cNEeXEer",
        audio="只有十个字",
        polish="",
        pdf=False,
    )

    result = write_result_metadata(
        output_dir,
        status="completed",
        source_url="https://www.bilibili.com/video/BV16cNEeXEer",
        title="半成品",
        audio_text="只有十个字",
        output_style="pdf_only",
    )

    assert result["status"] == "partial"
    assert result["output_status"] == "partial"
    assert result["audio_chars"] == 5
    assert result["quality_warning"]


def test_write_result_metadata_extra_cannot_override_status(tmp_path):
    output_dir = _make_output_dir(
        tmp_path,
        "BV1OverrideStatus",
        bvid="BV1OverrideStatus",
        audio="a" * 300,
        polish="b" * 300,
        pdf=False,
    )

    result = write_result_metadata(
        output_dir,
        status="completed",
        output_style="pdf_only",
        extra={"status": "completed", "output_status": "completed"},
    )

    assert result["status"] == "partial"
    assert result["output_status"] == "partial"


def test_scan_output_cache_corrects_stale_completed_status(tmp_path):
    output_dir = _make_output_dir(
        tmp_path,
        "BV1StaleStatus",
        bvid="BV1StaleStatus",
        audio="a" * 300,
        polish="",
        pdf=False,
    )
    (output_dir / "result.json").write_text(
        json.dumps(
            {
                "bvid": "BV1StaleStatus",
                "status": "completed",
                "model_config": {"output_style": "pdf_only"},
            }
        ),
        encoding="utf-8",
    )

    scan = scan_output_cache(tmp_path)

    partial = next(item for item in scan["partial_directories"] if item["bvid"] == "BV1StaleStatus")
    assert partial["status"] == "partial"


def test_scan_output_cache_finds_partial_duplicates_and_dry_run_candidates(tmp_path):
    _make_output_dir(
        tmp_path,
        "BV1cSLJ6vErH",
        bvid="BV1cSLJ6vErH",
        audio="a" * 300,
        polish="b" * 300,
    )
    _make_output_dir(
        tmp_path,
        "BV1cSLJ6vErH_1",
        bvid="BV1cSLJ6vErH",
        audio="a" * 300,
        polish="b" * 300,
    )
    _make_output_dir(
        tmp_path,
        "BV1cSLJ6vErH_2",
        bvid="BV1cSLJ6vErH",
        audio="a" * 300,
        polish="b" * 300,
    )
    _make_output_dir(
        tmp_path,
        "BV1cSLJ6vErH_3",
        bvid="BV1cSLJ6vErH",
        audio="a" * 300,
        polish="b" * 300,
    )
    _make_output_dir(
        tmp_path,
        "BV16cNEeXEer",
        bvid="BV16cNEeXEer",
        audio="短文本",
        polish="",
        pdf=False,
    )

    scan = scan_output_cache(tmp_path, keep_per_bvid=3)

    assert any(item["name"] == "BV16cNEeXEer" for item in scan["partial_directories"])
    duplicate = next(group for group in scan["duplicate_groups"] if group["bvid"] == "BV1cSLJ6vErH")
    assert duplicate["count"] == 4
    assert len(scan["cleanup_candidates"]) == 1
    assert all((tmp_path / name).exists() for name in ["BV1cSLJ6vErH", "BV16cNEeXEer"])
