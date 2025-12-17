"""
⚠️ 废弃警告

此模块已迁移到 src.core.history.manager

旧的用法（将在 v2.0.0 中移除）:
    from src.process_history import ProcessRecord, get_history_manager

新的用法:
    from src.core.history import ProcessRecord, get_history_manager

迁移指南: docs/proposals/legacy-module-migration.md
"""
import warnings
from src.core.history.manager import *

warnings.warn(
    "src.process_history 已废弃，请使用 src.core.history",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "ProcessRecord",
    "ProcessHistoryManager",
    "get_history_manager",
]
