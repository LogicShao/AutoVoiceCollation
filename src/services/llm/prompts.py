"""
提示词管理

集中管理默认提示词，并支持可选的外部覆盖文件。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.utils.config import get_config
from src.utils.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class PromptSpec:
    system: str
    user_template: str

    def render_system(self, **kwargs) -> str:
        return _safe_format(self.system, **kwargs)

    def render_user(self, **kwargs) -> str:
        return _safe_format(self.user_template, **kwargs)


POLISH_SYSTEM_PROMPT = """你是一个高级语言处理助手，专注于文本清理、分段与拼写修正。请按照以下要求处理以下文本：
1. **去除冗余内容**：删除所有的口吃、语气词、重复的词汇或无关的表达（例如：“呃”，“嗯”，“啊”）。
2. **合理分段**：根据上下文将文本分段，使其更加清晰易懂。
3. **拼写和语法修正**：自动修正拼写错误、语法错误和标点符号问题。
4. **保留原意和风格**：在修改过程中，请尽量保留文本的原意和风格，不做任何不必要的改写。
5. **简化和优化**：适当去除冗余、重复的内容，但确保不改变原文的核心信息。
根据这些要求，处理下面的文本：
"""

POLISH_USER_TEMPLATE = (
    "以下是语音识别的原始文本：\n{text}\n\n"
    "请你仅仅输出整理后的文本，不要增加多余的文字，"
    "也不要使用任何markdown形式的文字，只使用plain text的形式。"
)

SUMMARY_SYSTEM_PROMPT = (
    "你是一名资深学术研究助手，擅长将素材转化为具有哲学深度和辩证张力的小论文。"
    "当前任务是针对用户提供的长视频 ASR 转写文本（仅经换行和少量错误修正）撰写一篇风格契合范文的研究文章。"
    "请首先为论文拟定一个高度概括核心议题的标题，并在正文中始终以该标题来指代视频内容，绝不使用“ASR转写文本”等标签。"
    "正文分引言、主体与结论三部分，以连贯的自然段落呈现。"
    "在主体中，每段应先对原文要点进行细致解读，随后融入辩证式批判，最后自然过渡至对结构性根源或主体锻造仪式般过程的拓展讨论。"
    "文风要浓缩、直切本质，善用哲学隐喻与批判性提问，避免任何编号、列表或显式过渡句。"
)

SUMMARY_USER_TEMPLATE = """请基于以下 ASR 转写文本（仅作换行和少量错误修正），先拟定一个凝练且富有哲学意味的标题，然后撰写一篇小论文。论文包含引言、主体与结论三大段，全文以流畅的段落呈现，不使用项目符号或编号。
{title}
{text}

在引言中以高度凝练的段落点明研究切入点与核心命题；
在主体部分，每段依次完成“细致解读→辩证批判→结构性／主体性拓展”；
在结论中回扣标题，揭示研究所得的深层洞见，并在最后一笔中自然勾勒未来研究或实践的潜在脉络。

请务必保持学术严谨与哲学厚度，避免任何面向用户的元提示或建议语句。"""

SUBTITLE_SEGMENT_SYSTEM_PROMPT = (
    "你是一个字幕切分助手。请将以下文本切分为适合显示的多行字幕。"
    "每行最长 {max_chars_per_segment} 个字符。"
    "在每个切分点用 '|' 分隔，不要换行，不要添加、删除或替换任何文字。"
)

SUBTITLE_SEGMENT_USER_TEMPLATE = "{text}"

TITLE_SYSTEM_PROMPT = "You are a helpful assistant that generates concise titles."

TITLE_USER_TEMPLATE = """请根据以下文本内容生成一个简洁、准确的标题。

要求：
1. 标题长度不超过 {max_length} 个字符
2. 准确概括文本主题
3. 使用中文
4. 只返回标题本身，不要有任何解释、标点符号或引号

文本内容：
{text}

标题："""

_DEFAULT_PROMPTS: dict[str, PromptSpec] = {
    "polish": PromptSpec(system=POLISH_SYSTEM_PROMPT, user_template=POLISH_USER_TEMPLATE),
    "summary": PromptSpec(system=SUMMARY_SYSTEM_PROMPT, user_template=SUMMARY_USER_TEMPLATE),
    "subtitle_segment": PromptSpec(
        system=SUBTITLE_SEGMENT_SYSTEM_PROMPT,
        user_template=SUBTITLE_SEGMENT_USER_TEMPLATE,
    ),
    "title": PromptSpec(system=TITLE_SYSTEM_PROMPT, user_template=TITLE_USER_TEMPLATE),
}


def get_prompt(prompt_id: str) -> PromptSpec:
    if prompt_id not in _DEFAULT_PROMPTS:
        raise ValueError(f"Unknown prompt id: {prompt_id}")

    prompt_dir = get_config().paths.prompt_dir
    override = _load_prompt_override(prompt_id, prompt_dir)
    return override or _DEFAULT_PROMPTS[prompt_id]


def _load_prompt_override(prompt_id: str, prompt_dir: Path | None) -> PromptSpec | None:
    if prompt_dir is None:
        return None

    file_path = prompt_dir / f"{prompt_id}.json"
    if not file_path.is_file():
        return None

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"提示词覆盖文件读取失败: {file_path}，将使用默认提示词: {e}")
        return None

    if not isinstance(data, dict):
        logger.warning(f"提示词覆盖文件格式错误: {file_path}，将使用默认提示词")
        return None

    default_prompt = _DEFAULT_PROMPTS[prompt_id]
    system = data.get("system")
    user = data.get("user") if "user" in data else data.get("user_template")

    if system is None:
        system = default_prompt.system
    if user is None:
        user = default_prompt.user_template

    return PromptSpec(system=system, user_template=user)


def _safe_format(template: str, **kwargs) -> str:
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError) as e:
        logger.warning(f"提示词格式化失败，将使用未格式化模板: {e}")
        return template
