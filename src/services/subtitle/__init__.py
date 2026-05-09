"""
字幕生成服务模块

提供字幕生成、分段、视频硬编码等功能
"""

from .config import SubtitleConfig
from .generator import (
    encode_subtitle_to_video,
    gen_timestamped_text_file,
    generate_subtitle_file,
    hard_encode_dot_srt_file,
)
from .models import ASRResult, SubtitleSegment

__all__ = [
    "SubtitleConfig",
    "SubtitleSegment",
    "ASRResult",
    "generate_subtitle_file",
    "encode_subtitle_to_video",
    "gen_timestamped_text_file",
    "hard_encode_dot_srt_file",
]
