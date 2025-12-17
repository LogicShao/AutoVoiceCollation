"""
⚠️ 废弃警告

此模块已迁移到 src.core.export.file_manager

旧的用法（将在 v2.0.0 中移除）:
    from src.output_file_manager import copy_output_files, move_output_files

新的用法:
    from src.core.export import copy_output_files, move_output_files

迁移指南: docs/proposals/legacy-module-migration.md
"""
import warnings
from src.core.export.file_manager import *

warnings.warn(
    "src.output_file_manager 已废弃，请使用 src.core.export",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "copy_output_files",
    "move_output_files",
    "clean_directory",
    "remove_files",
]
