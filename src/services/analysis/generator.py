"""结构化视频分析 — 一步完成转写+LLM分析，输出结构化 VideoAnalysis"""

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.core.output_status import SUMMARY_SKIP_MESSAGE, should_skip_summary
from src.services.llm import LLMQueryParams, query_llm_async
from src.services.llm.prompts import PromptType, get_prompt
from src.utils.config import get_config
from src.utils.logging.logger import get_logger

logger = get_logger(__name__)


class VideoSegment(BaseModel):
    start_time: float = Field(..., description="分段开始时间，单位秒")
    end_time: float = Field(..., description="分段结束时间，单位秒")
    text: str = Field(..., description="分段原文或摘要文本")
    topic: str | None = Field(default=None, description="分段主题")


class VideoAnalysis(BaseModel):
    title: str = Field(..., description="视频标题")
    transcript: str = Field(..., description="原始转写全文")
    summary: str = Field(..., description="结构化摘要")
    key_points: list[str] = Field(default_factory=list, description="关键要点列表")
    segments: list[VideoSegment] = Field(default_factory=list, description="结构化分段列表")
    metadata: dict[str, Any] | None = Field(default=None, description="原始视频元数据")
    output_dir: str = Field(default="", description="输出目录")
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


async def generate_analysis(
    polished_text: str,
    title: str,
    transcript: str = "",
    output_dir: str = "",
    prompt_hint: str = "",
    metadata: Any = None,
) -> VideoAnalysis:
    metadata_data = _serialize_metadata(metadata)
    if should_skip_summary(polished_text, transcript or None):
        logger.info(
            "Skipping structured analysis because text is shorter than the reliability threshold"
        )
        return VideoAnalysis(
            title=title,
            transcript=transcript,
            summary=SUMMARY_SKIP_MESSAGE,
            key_points=[],
            segments=[],
            metadata=metadata_data,
            output_dir=output_dir,
        )

    config = get_config()
    prompt_spec = get_prompt(PromptType.ANALYZE_VIDEO)
    system_instruction = prompt_spec.render_system()
    if prompt_hint.strip():
        system_instruction += f"\n\n---\n[Agent 指令]\n{prompt_hint.strip()[:500]}"
    metadata_prompt = _format_metadata_for_prompt(metadata)
    if metadata_prompt and metadata_prompt != "[视频元数据]":
        system_instruction += f"\n\n---\n{metadata_prompt}"
    user_content = prompt_spec.render_user(text=polished_text, title=title)

    params = LLMQueryParams(
        content=user_content,
        system_instruction=system_instruction,
        temperature=0.2,
        max_tokens=4000,
        api_server=config.llm.summary_llm_server or config.llm.llm_server,
        top_p=0.95,
        top_k=1,
    )

    logger.info(f"正在生成结构化分析（使用 {params.api_server}）...")
    response = await query_llm_async(params)
    data = _parse_analysis_response(response)

    return VideoAnalysis(
        title=title,
        transcript=transcript,
        summary=data.get("summary", ""),
        key_points=data.get("key_points", []),
        segments=[VideoSegment(**s) for s in data.get("segments", []) if isinstance(s, dict)],
        metadata=metadata_data,
        output_dir=output_dir,
    )


def _serialize_metadata(metadata: Any) -> dict[str, Any] | None:
    if metadata is None:
        return None
    if isinstance(metadata, BaseModel):
        return metadata.model_dump()
    if isinstance(metadata, dict):
        return dict(metadata)
    return None


def _format_metadata_for_prompt(metadata: Any) -> str:
    if metadata is None:
        return ""
    from src.mcp.bilibili_api import VideoMetadata, format_metadata_for_prompt

    if isinstance(metadata, VideoMetadata):
        metadata_model = metadata
    elif isinstance(metadata, BaseModel):
        metadata_model = VideoMetadata(**metadata.model_dump())
    elif isinstance(metadata, dict):
        metadata_model = VideoMetadata(**metadata)
    else:
        return ""
    return format_metadata_for_prompt(metadata_model)


def _parse_analysis_response(response: str) -> dict:
    cleaned = response.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("LLM analysis response is not valid JSON, returning empty result")
        return {"summary": "", "key_points": [], "segments": []}
