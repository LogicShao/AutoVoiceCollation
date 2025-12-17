"""
⚠️ 废弃警告

此模块已迁移到 src.utils.logging.logger

旧的用法（将在 v2.0.0 中移除）:
    from src.logger import get_logger, configure_third_party_loggers

新的用法:
    from src.utils.logging.logger import get_logger, configure_third_party_loggers

迁移指南: docs/proposals/legacy-module-migration.md
"""
import warnings
from src.utils.logging.logger import (
    ColoredFormatter,
    setup_logger,
    get_logger,
    configure_third_party_loggers,
)

warnings.warn(
    "src.logger 已废弃，请使用 src.utils.logging.logger",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "ColoredFormatter",
    "setup_logger",
    "get_logger",
    "configure_third_party_loggers",
]
