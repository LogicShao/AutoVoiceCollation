"""思维导图生成器 — 从转写文本提取层级主题并输出多种格式"""

import json
import os
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from src.services.llm import LLMQueryParams, query_llm_async
from src.services.llm.prompts import PromptType, get_prompt
from src.utils.config import get_config
from src.utils.logging.logger import get_logger

logger = get_logger(__name__)


class MindMapDepth(StrEnum):
    """思维导图生成深度"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    AUTO = "auto"


_DEPTH_SETTINGS = {
    MindMapDepth.LOW: {
        "label": "浅层",
        "max_topics": 3,
        "max_sub_points": 3,
        "max_levels": 2,
        "instruction": "只保留主干主题和直接要点，避免展开细节。",
    },
    MindMapDepth.MEDIUM: {
        "label": "中等",
        "max_topics": 5,
        "max_sub_points": 4,
        "max_levels": 3,
        "instruction": "保留主题、子主题和关键细节，适合常规知识整理。",
    },
    MindMapDepth.HIGH: {
        "label": "深入",
        "max_topics": 7,
        "max_sub_points": 5,
        "max_levels": 4,
        "instruction": "充分展开主题层级、关键细节和因果关系，但不要臆造原文没有的信息。",
    },
}


class MindMapNode(BaseModel):
    """思维导图节点（递归树结构）"""

    title: str
    children: list["MindMapNode"] = Field(default_factory=list)


class MindMapOutput(BaseModel):
    """思维导图输出"""

    root: MindMapNode
    depth: MindMapDepth = MindMapDepth.LOW
    source_url: str | None = None
    source_title: str | None = None
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    node_count: int = 0

    def model_post_init(self, __context) -> None:
        self.node_count = self._count_nodes(self.root)

    @staticmethod
    def _count_nodes(node: MindMapNode) -> int:
        return 1 + sum(MindMapOutput._count_nodes(c) for c in node.children)


async def generate_mindmap(
    text: str,
    title: str | None = None,
    depth: MindMapDepth | str = MindMapDepth.LOW,
    source_url: str | None = None,
    max_topics: int | None = None,
    max_sub_points: int | None = None,
    prompt_hint: str = "",
) -> MindMapOutput:
    config = get_config()
    requested_depth = _normalize_depth(depth)
    prompt_depth = _resolve_prompt_depth(requested_depth, text)
    depth_settings = _DEPTH_SETTINGS[prompt_depth]
    resolved_max_topics = max_topics or depth_settings["max_topics"]
    resolved_max_sub_points = max_sub_points or depth_settings["max_sub_points"]
    prompt_spec = get_prompt(PromptType.MINDMAP)
    system_instruction = prompt_spec.render_system(
        depth_value=requested_depth.value,
        depth_label=depth_settings["label"],
        resolved_depth=prompt_depth.value,
        max_topics=resolved_max_topics,
        max_sub_points=resolved_max_sub_points,
        max_levels=depth_settings["max_levels"],
        depth_instruction=depth_settings["instruction"],
    )
    if prompt_hint.strip():
        system_instruction += f"\n\n---\n[Agent 指令]\n{prompt_hint.strip()[:500]}"
    user_content = prompt_spec.render_user(
        text=text, title=title or "未命名", depth_label=depth_settings["label"]
    )

    params = LLMQueryParams(
        content=user_content,
        system_instruction=system_instruction,
        temperature=0.3,
        max_tokens=2000,
        api_server=config.llm.summary_llm_server or config.llm.llm_server,
        top_p=0.95,
        top_k=1,
    )

    logger.info(f"正在生成思维导图（使用 {params.api_server}）...")
    response = await query_llm_async(params)
    root = _parse_llm_response(response, title)

    if not root.children:
        logger.warning("LLM 未生成任何主题节点，请检查 prompt 或尝试更换更强的 LLM 模型")

    return MindMapOutput(
        root=root,
        depth=requested_depth,
        source_url=source_url,
        source_title=title,
    )


def _normalize_depth(depth: MindMapDepth | str) -> MindMapDepth:
    if isinstance(depth, MindMapDepth):
        return depth
    try:
        return MindMapDepth(str(depth).lower())
    except ValueError:
        valid_values = ", ".join(item.value for item in MindMapDepth)
        raise ValueError(
            f"Unsupported mindmap depth: {depth}. Valid values: {valid_values}"
        ) from None


def _resolve_prompt_depth(depth: MindMapDepth, text: str) -> MindMapDepth:
    if depth != MindMapDepth.AUTO:
        return depth

    text_length = len(text.strip())
    if text_length >= 6000:
        return MindMapDepth.HIGH
    if text_length >= 2000:
        return MindMapDepth.MEDIUM
    return MindMapDepth.LOW


def _parse_llm_response(response: str, fallback_title: str | None = None) -> MindMapNode:
    """解析 LLM 返回的 JSON，容错处理"""
    cleaned = response.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("LLM 返回的不是合法 JSON，使用原始文本作为根节点")
        return MindMapNode(title=fallback_title or "内容", children=[])

    return _dict_to_node(data, fallback_title)


def _dict_to_node(data: dict, fallback_title: str | None = None) -> MindMapNode:
    title = data.get("title") or fallback_title or "未命名"
    children = [_dict_to_node(c) for c in data.get("children", []) if isinstance(c, dict)]
    return MindMapNode(title=title, children=children)


def render_mermaid(root: MindMapNode) -> str:
    """渲染为 Mermaid mindmap 语法文本"""

    def _render(node: MindMapNode, depth: int) -> list[str]:
        indent = "  " * (depth + 1)
        lines = [f"{indent}{node.title}"]
        for child in node.children:
            lines.extend(_render(child, depth + 1))
        return lines

    lines = ["mindmap", f"  root(({root.title}))"]
    for child in root.children:
        lines.extend(_render(child, 1))
    return "\n".join(lines)


def render_json(output: MindMapOutput) -> str:
    """渲染为 JSON 文本"""
    return output.model_dump_json(indent=2, ensure_ascii=False)


def export_mindmap_to_files(
    output: MindMapOutput,
    output_dir: str,
    formats: list[str] | None = None,
) -> dict[str, str]:
    """
    导出思维导图为文件

    Args:
        output: MindMapOutput 对象
        output_dir: 输出目录
        formats: 输出格式列表，默认 ['mermaid', 'json']

    Returns:
        {格式: 文件路径} 字典
    """
    if formats is None:
        formats = ["mermaid", "json"]

    os.makedirs(output_dir, exist_ok=True)
    base_name = "mindmap"
    result: dict[str, str] = {}

    for fmt in formats:
        if fmt == "mermaid":
            path = os.path.join(output_dir, f"{base_name}.md")
            content = render_mermaid(output.root)
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# {output.source_title or '思维导图'}\n\n```mermaid\n{content}\n```\n")
            result["mermaid"] = path
            logger.info(f"Mermaid 导图已保存: {path}")

        elif fmt == "json":
            path = os.path.join(output_dir, f"{base_name}.json")
            content = render_json(output)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            result["json"] = path
            logger.info(f"JSON 导图已保存: {path}")

    return result
