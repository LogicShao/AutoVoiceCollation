"""
处理历史管理模块

提供处理历史记录的存储、查询、统计等功能
"""

from .manager import (
    ProcessHistoryManager,
    ProcessRecord,
    get_history_manager,
)

__all__ = [
    "ProcessRecord",
    "ProcessHistoryManager",
    "get_history_manager",
]
