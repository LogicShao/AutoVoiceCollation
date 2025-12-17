"""
LLM数据模型

定义LLM查询参数和枚举
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Optional


class LLMProvider(StrEnum):
    """LLM提供商枚举"""

    DEEPSEEK_CHAT = "deepseek-chat"
    DEEPSEEK_REASONER = "deepseek-reasoner"
    GEMINI_2_0_FLASH = "gemini-2.0-flash"
    QWEN3_PLUS = "qwen3-plus"
    QWEN3_MAX = "qwen3-max"
    CEREBRAS_QWEN3_32B = "Cerebras:Qwen-3-32B"
    CEREBRAS_QWEN3_235B_INSTRUCT = "Cerebras:Qwen-3-235B-Instruct"
    CEREBRAS_QWEN3_235B_THINKING = "Cerebras:Qwen-3-235B-Thinking"
    LOCAL_QWEN2_5 = "local:Qwen/Qwen2.5-1.5B-Instruct"


@dataclass
class LLMQueryParams:
    """LLM查询参数"""

    content: str
    system_instruction: str = "You are a helpful assistant."
    temperature: float = 0.3
    max_tokens: int = 1024
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    api_server: str = "gemini-2.0-flash"


def is_local_llm(api_name: str) -> bool:
    """检查是否为本地LLM"""
    return api_name.startswith("local:")
