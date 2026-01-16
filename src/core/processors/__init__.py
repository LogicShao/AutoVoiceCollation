"""
核心处理器模块

提供音频、视频、字幕等处理功能
"""

__all__ = [
    "BaseProcessor",
    "AudioProcessor",
    "VideoProcessor",
    "SubtitleProcessor",
    "MultiPartVideoProcessor",
]


def __getattr__(name):
    if name == "BaseProcessor":
        from .base import BaseProcessor

        return BaseProcessor
    if name == "AudioProcessor":
        from .audio import AudioProcessor

        return AudioProcessor
    if name == "VideoProcessor":
        from .video import VideoProcessor

        return VideoProcessor
    if name == "SubtitleProcessor":
        from .subtitle import SubtitleProcessor

        return SubtitleProcessor
    if name == "MultiPartVideoProcessor":
        from .multi_part_video import MultiPartVideoProcessor

        return MultiPartVideoProcessor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(__all__)
