"""
LLM服务模块

提供统一的LLM查询接口,支持多个提供商
"""

from .models import LLMQueryParams, LLMProvider, is_local_llm
from .factory import query_llm

__all__ = [
    "LLMQueryParams",
    "LLMProvider",
    "is_local_llm",
    "query_llm",
]
