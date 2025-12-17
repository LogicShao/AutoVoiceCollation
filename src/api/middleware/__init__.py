"""
API 中间件模块
"""

from .error_handler import register_exception_handlers

__all__ = ["register_exception_handlers"]
