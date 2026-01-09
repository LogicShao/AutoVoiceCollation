"""
B站下载服务模块

提供B站视频/音频下载、音频提取等功能
"""

from .bilibili_downloader import (
    BiliVideoFile,
    BiliVideoPart,
    BiliMultiPartVideo,
    FileType,
    download_bilibili_video,
    download_bilibili_audio,
    extract_audio_from_video,
    new_local_bili_file,
    detect_multi_part,
    get_multi_part_info,
)

__all__ = [
    "BiliVideoFile",
    "BiliVideoPart",
    "BiliMultiPartVideo",
    "FileType",
    "download_bilibili_video",
    "download_bilibili_audio",
    "extract_audio_from_video",
    "new_local_bili_file",
    "detect_multi_part",
    "get_multi_part_info",
]
