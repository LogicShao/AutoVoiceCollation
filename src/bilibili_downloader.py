"""
⚠️ 废弃警告

此模块已迁移到 src.services.download.bilibili_downloader

旧的用法（将在 v2.0.0 中移除）:
    from src.bilibili_downloader import BiliVideoFile, download_bilibili_video

新的用法:
    from src.services.download import BiliVideoFile, download_bilibili_video

迁移指南: docs/proposals/legacy-module-migration.md
"""
import warnings
from src.services.download.bilibili_downloader import *

warnings.warn(
    "src.bilibili_downloader 已废弃，请使用 src.services.download",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "BiliVideoFile",
    "FileType",
    "download_bilibili_video",
    "download_bilibili_audio",
    "extract_audio_from_video",
    "new_local_bili_file",
]
