"""
API Schemas 模块

提供 FastAPI 请求和响应的 Pydantic 模型定义
"""

from .request import (
    AudioProcessRequest,
    BatchProcessRequest,
    BilibiliProcessRequest,
)
from .response import (
    ErrorResponse,
    FileDownloadInfo,
    SuccessResponse,
)
from .task import (
    TaskCancelResponse,
    TaskListResponse,
    TaskResponse,
    TaskStatus,
)

__all__ = [
    # 任务相关
    "TaskStatus",
    "TaskResponse",
    "TaskListResponse",
    "TaskCancelResponse",
    # 请求模型
    "BilibiliProcessRequest",
    "AudioProcessRequest",
    "BatchProcessRequest",
    # 响应模型
    "SuccessResponse",
    "ErrorResponse",
    "FileDownloadInfo",
]
