"""
B站下载服务模块

提供B站视频/音频下载、音频提取等功能
"""

from .bilibili_downloader import (
    BiliVideoFile,
    FileType,
    download_bilibili_video,
    download_bilibili_audio,
    extract_audio_from_video,
    new_local_bili_file,
)

__all__ = [
    "BiliVideoFile",
    "FileType",
    "download_bilibili_video",
    "download_bilibili_audio",
    "extract_audio_from_video",
    "new_local_bili_file",
]
