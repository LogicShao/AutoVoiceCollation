"""
LLM服务模块

提供统一的LLM查询接口,支持多个提供商
"""

from .models import LLMProvider, LLMQueryParams, is_local_llm

__all__ = [
    "LLMQueryParams",
    "LLMProvider",
    "is_local_llm",
    "query_llm",
]


def __getattr__(name):
    if name == "query_llm":
        from .factory import query_llm

        return query_llm
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(__all__)
