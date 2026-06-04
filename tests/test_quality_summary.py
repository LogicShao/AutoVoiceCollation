"""生产摘要质量回归测试。"""

import asyncio
import json
from pathlib import Path

from src.core.output_status import SUMMARY_SKIP_MESSAGE, should_skip_summary
from src.mcp.bilibili_api import VideoMetadata
from src.services.analysis.generator import VideoAnalysis, generate_analysis
from src.services.llm import prompts

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "quality_samples"
POLLUTED_WORDS = ["哲学", "主体锻造", "存在论"]


def _read_sample(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _read_expectations() -> dict:
    return json.loads((FIXTURE_DIR / "expectations.json").read_text(encoding="utf-8"))


def test_summary_prompt_is_production_oriented():
    prompt = prompts.SUMMARY_SYSTEM_PROMPT

    assert "## 摘要" in prompt
    assert "## 关键点" in prompt
    assert "## 细节/行动项" in prompt
    assert "不得补充原文没有" in prompt
    for word in POLLUTED_WORDS:
        assert word not in prompt


def test_short_text_must_skip_summary():
    sample = _read_sample("short_text.txt")

    assert should_skip_summary(sample)


def test_text_only_summary_skips_short_source_text_without_llm(monkeypatch):
    import api

    def fail_summarize(*args, **kwargs):
        raise AssertionError("short source text should not call LLM summary")

    monkeypatch.setattr(api, "summarize_text", fail_summarize)

    async def run_summary():
        loop = asyncio.get_running_loop()
        return await api._summarize_text_result(
            loop,
            {
                "title": "短转写长润色",
                "audio_text": _read_sample("short_text.txt"),
                "polished_text": _read_sample("career_planning_long.txt"),
            },
            llm_api="http://example.invalid",
            temperature=0.3,
            max_tokens=256,
        )

    summary = asyncio.run(run_summary())

    assert summary == SUMMARY_SKIP_MESSAGE


def test_structured_analysis_skips_short_text_without_llm(monkeypatch):
    async def fail_query(*args, **kwargs):
        raise AssertionError("short text should not call LLM")

    monkeypatch.setattr("src.services.analysis.generator.query_llm_async", fail_query)

    analysis = asyncio.run(
        generate_analysis(
            polished_text=_read_sample("short_text.txt"),
            title="短文本",
            transcript=_read_sample("short_text.txt"),
        )
    )

    assert analysis.summary == SUMMARY_SKIP_MESSAGE
    assert analysis.key_points == []
    assert analysis.segments == []


def test_video_analysis_json_schema_contract():
    schema = VideoAnalysis.model_json_schema()
    properties = schema["properties"]

    assert "summary" in properties
    assert "key_points" in properties
    assert "segments" in properties
    assert "metadata" in properties
    assert "summary" in schema["required"]


def test_structured_analysis_preserves_metadata(monkeypatch):
    sample = _read_sample("career_planning_long.txt")
    captured = {}

    async def fake_query(params):
        captured["system_instruction"] = params.system_instruction
        return (
            '{"summary":"围绕职业规划给出可执行建议。",'
            '"key_points":["明确目标岗位"],'
            '"segments":[{"start_time":0,"end_time":12,"text":"目标岗位分析","topic":"规划"}]}'
        )

    monkeypatch.setattr("src.services.analysis.generator.query_llm_async", fake_query)

    metadata = VideoMetadata(
        title="职业规划视频",
        owner="测试UP主",
        tags=["职业", "简历"],
        chapters=[{"title": "开场", "part_number": 1, "duration": 12}],
    )
    analysis = asyncio.run(
        generate_analysis(sample, "职业规划", transcript=sample, metadata=metadata)
    )

    assert analysis.metadata is not None
    assert analysis.metadata["title"] == "职业规划视频"
    assert analysis.metadata["owner"] == "测试UP主"
    assert analysis.metadata["tags"] == ["职业", "简历"]
    assert "测试UP主" in captured["system_instruction"]


def test_structured_analysis_accepts_dict_metadata(monkeypatch):
    sample = _read_sample("career_planning_long.txt")
    captured = {}

    async def fake_query(params):
        captured["system_instruction"] = params.system_instruction
        return (
            '{"summary":"围绕职业规划给出可执行建议。",'
            '"key_points":["明确目标岗位"],'
            '"segments":[{"start_time":0,"end_time":12,"text":"目标岗位分析","topic":"规划"}]}'
        )

    monkeypatch.setattr("src.services.analysis.generator.query_llm_async", fake_query)

    analysis = asyncio.run(
        generate_analysis(
            sample,
            "职业规划",
            transcript=sample,
            metadata={"title": "职业规划视频", "owner": "测试UP主", "tags": ["职业"]},
        )
    )

    assert analysis.metadata == {"title": "职业规划视频", "owner": "测试UP主", "tags": ["职业"]}
    assert "测试UP主" in captured["system_instruction"]


def test_analysis_summary_style_and_length(monkeypatch):
    sample = _read_sample("career_planning_long.txt")
    expectation = _read_expectations()["career_planning_long.txt"]

    async def fake_query(*args, **kwargs):
        return (
            '{"summary":"视频围绕职业规划、简历修改和实习选择给出建议，强调从目标岗位反推能力要求，'
            '用真实项目和反馈持续优化求职材料。","key_points":["明确目标岗位","修改简历","选择实习",'
            '"准备面试","复盘职业规划"],"segments":[{"start_time":0,"end_time":0,'
            '"text":"职业规划与求职准备","topic":"职业规划"}]}'
        )

    monkeypatch.setattr("src.services.analysis.generator.query_llm_async", fake_query)
    analysis = asyncio.run(generate_analysis(sample, "职业规划", transcript=sample))

    assert len(analysis.summary) >= expectation["summary_min_chars"]
    assert len(analysis.summary) <= len(sample) * expectation["summary_max_ratio"]
    assert len(analysis.key_points) >= expectation["key_points_min"]
    for keyword in expectation["keywords"]:
        assert keyword in sample
    assert any("简历" in point for point in analysis.key_points)
    assert any("实习" in point for point in analysis.key_points)
    for word in expectation["forbidden_words"]:
        assert word not in analysis.summary
        assert all(word not in point for point in analysis.key_points)


def test_quality_samples_cover_required_scenarios():
    expectations = _read_expectations()
    samples = {
        "short_text.txt",
        "ai_news_short.txt",
        "career_planning_long.txt",
        "game_spoken.txt",
    }

    for sample in samples:
        assert (FIXTURE_DIR / sample).is_file()
        assert sample in expectations
