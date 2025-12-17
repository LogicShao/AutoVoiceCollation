"""
⚠️ 废弃警告

此模块已迁移到 src.utils.helpers.task_manager

旧的用法（将在 v2.0.0 中移除）:
    from src.task_manager import TaskManager, get_task_manager

新的用法:
    from src.utils.helpers.task_manager import TaskManager, get_task_manager

迁移指南: docs/proposals/legacy-module-migration.md
"""
import warnings
from src.utils.helpers.task_manager import (
    TaskManager,
    get_task_manager,
)

warnings.warn(
    "src.task_manager 已废弃，请使用 src.utils.helpers.task_manager",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["TaskManager", "get_task_manager"]
