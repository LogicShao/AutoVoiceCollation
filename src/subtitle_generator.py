"""
⚠️ 废弃警告

此模块已迁移到 src.services.subtitle.generator

旧的用法（将在 v2.0.0 中移除）:
    from src.subtitle_generator import generate_subtitle_file, encode_subtitle_to_video

新的用法:
    from src.services.subtitle import generate_subtitle_file, encode_subtitle_to_video

迁移指南: docs/proposals/legacy-module-migration.md
"""
import warnings
from src.services.subtitle.generator import *

warnings.warn(
    "src.subtitle_generator 已废弃，请使用 src.services.subtitle",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "SubtitleConfig",
    "SubtitleSegment",
    "ASRResult",
    "generate_subtitle_file",
    "encode_subtitle_to_video",
    "gen_timestamped_text_file",
    "hard_encode_dot_srt_file",
]
