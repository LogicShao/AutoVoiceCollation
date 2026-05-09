"""思维导图生成器 — 从转写文本提取层级主题并输出多种格式"""

import json
import os
from datetime import datetime

from pydantic import BaseModel, Field

from src.services.llm import LLMQueryParams, query_llm_async
from src.services.llm.prompts import PromptType, get_prompt
from src.utils.config import get_config
from src.utils.logging.logger import get_logger

logger = get_logger(__name__)


class MindMapNode(BaseModel):
    """思维导图节点（递归树结构）"""

    title: str
    children: list["MindMapNode"] = Field(default_factory=list)


class MindMapOutput(BaseModel):
    """思维导图输出"""

    root: MindMapNode
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
    source_url: str | None = None,
    max_topics: int = 5,
    max_sub_points: int = 4,
) -> MindMapOutput:
    """
    从转写文本生成思维导图

    Args:
        text: 转写文本内容
        title: 视频/音频标题（可选，用于根节点）
        source_url: 来源 URL（可选，存入 metadata）
        max_topics: 最大一级主题数
        max_sub_points: 每个主题最大子要点数
    """
    config = get_config()
    prompt_spec = get_prompt(PromptType.MINDMAP)
    system_instruction = prompt_spec.render_system(
        max_topics=max_topics, max_sub_points=max_sub_points
    )
    user_content = prompt_spec.render_user(text=text, title=title or "未命名")

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
        source_url=source_url,
        source_title=title,
    )


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
        lines.extend(_render(child, 0))
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
