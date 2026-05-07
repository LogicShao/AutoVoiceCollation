"""
LLM数据模型

定义LLM查询参数和模型注册表（单一数据源）。
"""

from dataclasses import dataclass
from enum import StrEnum


def _model_enum_name(key: str) -> str:
    return key.replace(":", "_").replace("-", "_").replace(".", "_").replace("/", "_").upper()


# ============= 单一数据源：所有支持的 LLM 模型 =============

LLM_MODELS: dict[str, dict[str, str]] = {
    "deepseek-chat": {"provider": "deepseek", "model_id": "deepseek-chat"},
    "deepseek-reasoner": {"provider": "deepseek", "model_id": "deepseek-reasoner"},
    "deepseek-v4-pro": {"provider": "deepseek", "model_id": "deepseek-v4-pro"},
    "deepseek-v4-flash": {"provider": "deepseek", "model_id": "deepseek-v4-flash"},
    "gemini-2.0-flash": {"provider": "gemini", "model_id": "gemini-2.0-flash"},
    "qwen3-plus": {"provider": "dashscope", "model_id": "qwen-plus"},
    "qwen3-max": {"provider": "dashscope", "model_id": "qwen-max"},
    "Cerebras:Qwen-3-32B": {"provider": "cerebras", "model_id": "qwen-3-32b"},
    "Cerebras:Qwen-3-235B-Instruct": {
        "provider": "cerebras",
        "model_id": "qwen-3-235b-a22b-instruct-2507",
    },
    "Cerebras:Qwen-3-235B-Thinking": {
        "provider": "cerebras",
        "model_id": "qwen-3-235b-a22b-thinking-2507",
    },
    "local:Qwen/Qwen2.5-1.5B-Instruct": {
        "provider": "local",
        "model_id": "Qwen/Qwen2.5-1.5B-Instruct",
    },
}

LLMProvider = StrEnum(  # type: ignore[call-overload]
    "LLMProvider", [(_model_enum_name(k), k) for k in LLM_MODELS]
)


# ============= 查询参数 =============


@dataclass
class LLMQueryParams:
    """LLM查询参数"""

    content: str
    system_instruction: str = "You are a helpful assistant."
    temperature: float = 0.3
    max_tokens: int = 1024
    top_k: int | None = None
    top_p: float | None = None
    api_server: str = "gemini-2.0-flash"


def is_local_llm(api_name: str) -> bool:
    """检查是否为本地LLM"""
    return api_name.startswith("local:")
