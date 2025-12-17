"""
⚠️ 废弃警告

此模块已迁移到 src.utils.helpers.timer

旧的用法（将在 v2.0.0 中移除）:
    from src.Timer import Timer

新的用法:
    from src.utils.helpers.timer import Timer

迁移指南: docs/proposals/legacy-module-migration.md
"""
import warnings
from src.utils.helpers.timer import Timer

warnings.warn(
    "src.Timer 已废弃，请使用 src.utils.helpers.timer",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["Timer"]
