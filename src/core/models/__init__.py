"""
核心数据模型

提供类型安全的数据结构，用于任务、视频、处理结果等
"""

from .task import TaskStatus, TaskResult, ProcessingTask
from .video import VideoInfo

__all__ = [
    "TaskStatus",
    "TaskResult",
    "ProcessingTask",
    "VideoInfo",
]
