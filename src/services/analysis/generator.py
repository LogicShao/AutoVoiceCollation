"""结构化视频分析 — 一步完成转写+LLM分析，输出结构化 VideoAnalysis"""

import json
from datetime import datetime

from pydantic import BaseModel, Field

from src.services.llm import LLMQueryParams, query_llm_async
from src.services.llm.prompts import PromptType, get_prompt
from src.utils.config import get_config
from src.utils.logging.logger import get_logger

logger = get_logger(__name__)


class VideoSegment(BaseModel):
    start_time: float
    end_time: float
    text: str
    topic: str | None = None


class VideoAnalysis(BaseModel):
    title: str
    transcript: str
    summary: str
    key_points: list[str] = Field(default_factory=list)
    segments: list[VideoSegment] = Field(default_factory=list)
    output_dir: str = ""
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


async def generate_analysis(
    polished_text: str,
    title: str,
    transcript: str = "",
    output_dir: str = "",
) -> VideoAnalysis:
    config = get_config()
    prompt_spec = get_prompt(PromptType.ANALYZE_VIDEO)
    system_instruction = prompt_spec.render_system()
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
        output_dir=output_dir,
    )


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
