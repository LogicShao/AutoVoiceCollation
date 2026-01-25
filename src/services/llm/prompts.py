"""
提示词管理

集中管理默认提示词，并支持可选的外部覆盖文件。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
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


class PromptType(str, Enum):
    POLISH = "polish"
    SUMMARY = "summary"
    SUBTITLE_SEGMENT = "subtitle_segment"
    TITLE = "title"


POLISH_SYSTEM_PROMPT = """你是一个高级语言处理助手，专注于文本清理与拼写修正。
核心原则：
1. **准确性优先**：修正明显的ASR识别错误（如同音字错误），但不要改写用户原本的用词习惯。
2. **去口语化**：仅删除“呃、那个、然后”等无意义填充词及重复口吃。
3. **不要总结**：绝不要对文本进行摘要，必须保留所有细节信息。
4. **格式保留**：不要使用 Markdown，仅输出纯文本。"""

POLISH_USER_TEMPLATE = """请处理被 <input_text> 标签包裹的语音识别文本。
<input_text>
{text}
</input_text>

输出要求：直接输出整理后的文本，不要包含 XML 标签，不要包含任何解释性语句。"""

SUMMARY_SYSTEM_PROMPT = (
    "你是一名资深学术研究助手，擅长将素材转化为具有哲学深度和辩证张力的小论文。"
    "当前任务是针对用户提供的长视频 ASR 转写文本（仅经换行和少量错误修正）撰写一篇风格契合范文的研究文章。"
    "请首先为论文拟定一个高度概括核心议题的标题，并在正文中始终以该标题来指代视频内容，绝不使用“ASR转写文本”等标签。"
    "正文分引言、主体与结论三部分，以连贯的自然段落呈现。"
    "在主体中，每段应先对原文要点进行细致解读，随后融入辩证式批判，最后自然过渡至对结构性根源或主体锻造仪式般过程的拓展讨论。"
    "文风要浓缩、直切本质，善用哲学隐喻与批判性提问，避免任何编号、列表或显式过渡句。"
)

SUMMARY_USER_TEMPLATE = """来源视频标题：{title}
来源转写文本：
{text}

请基于以上内容，按照系统指令撰写一篇具有哲学深度的小论文。"""

SUBTITLE_SEGMENT_SYSTEM_PROMPT = """你是一个专业的字幕切分助手。任务是将长文本按语义和长度切分为字幕行。
规则：
1. 必须在逻辑停顿处切分。
2. 每段尽量控制在 {max_chars_per_segment} 字符以内。
3. 使用 '|' 符号作为分隔符，保持单行输出。
4. 严禁修改、删除或增加原文的任何文字。

示例：
输入：今天天气真好我们要去公园玩但是可能会下雨
输出：今天天气真好|我们要去公园玩|但是可能会下雨"""

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

_DEFAULT_PROMPTS: dict[PromptType, PromptSpec] = {
    PromptType.POLISH: PromptSpec(system=POLISH_SYSTEM_PROMPT, user_template=POLISH_USER_TEMPLATE),
    PromptType.SUMMARY: PromptSpec(
        system=SUMMARY_SYSTEM_PROMPT, user_template=SUMMARY_USER_TEMPLATE
    ),
    PromptType.SUBTITLE_SEGMENT: PromptSpec(
        system=SUBTITLE_SEGMENT_SYSTEM_PROMPT,
        user_template=SUBTITLE_SEGMENT_USER_TEMPLATE,
    ),
    PromptType.TITLE: PromptSpec(system=TITLE_SYSTEM_PROMPT, user_template=TITLE_USER_TEMPLATE),
}


@lru_cache
def get_prompt(prompt_id: PromptType | str) -> PromptSpec:
    prompt_type = _normalize_prompt_id(prompt_id)
    prompt_dir = get_config().paths.prompt_dir
    override = _load_prompt_override(prompt_type, prompt_dir)
    return override or _DEFAULT_PROMPTS[prompt_type]


def clear_prompt_cache() -> None:
    get_prompt.cache_clear()


def _normalize_prompt_id(prompt_id: PromptType | str) -> PromptType:
    if isinstance(prompt_id, PromptType):
        return prompt_id
    try:
        return PromptType(prompt_id)
    except ValueError:
        raise ValueError(f"Unknown prompt id: {prompt_id}") from None


def _load_prompt_override(prompt_id: PromptType, prompt_dir: Path | None) -> PromptSpec | None:
    if prompt_dir is None:
        return None

    file_path = prompt_dir / f"{prompt_id.value}.json"
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
    rendered = template
    for key, value in kwargs.items():
        rendered = rendered.replace("{" + str(key) + "}", str(value))
    return rendered
