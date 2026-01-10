"""
任务相关 Schema

定义任务管理 API 的请求和响应模型
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskResponse(BaseModel):
    """任务响应模型"""

    task_id: str = Field(..., description="任务唯一标识符")
    status: TaskStatus = Field(..., description="任务状态")
    created_at: datetime = Field(..., description="任务创建时间")
    updated_at: datetime | None = Field(None, description="任务最后更新时间")
    completed_at: datetime | None = Field(None, description="任务完成时间")

    # 输入信息
    url: str | None = Field(None, description="处理的视频 URL（B站任务）")
    file_name: str | None = Field(None, description="处理的文件名（音频上传任务）")

    # 处理结果
    result: dict[str, Any] | None = Field(None, description="处理结果详情")
    error: str | None = Field(None, description="错误信息（如果失败）")

    # 输出文件信息
    output_dir: str | None = Field(None, description="输出目录路径")
    files: list[str] | None = Field(None, description="生成的文件列表")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "abc123def456",
                "status": "completed",
                "created_at": "2025-12-16T10:30:00",
                "updated_at": "2025-12-16T10:35:00",
                "completed_at": "2025-12-16T10:35:00",
                "url": "https://www.bilibili.com/video/BV1xx411c7mD",
                "result": {
                    "title": "示例视频标题",
                    "duration": "10:30",
                    "transcription_length": 5000,
                },
                "output_dir": "/out/video_title",
                "files": ["output.pdf", "audio_transcription.txt"],
            }
        }


class TaskListResponse(BaseModel):
    """任务列表响应模型"""

    tasks: list[TaskResponse] = Field(..., description="任务列表")
    total: int = Field(..., description="任务总数")

    class Config:
        json_schema_extra = {
            "example": {
                "tasks": [
                    {
                        "task_id": "abc123",
                        "status": "completed",
                        "created_at": "2025-12-16T10:30:00",
                        "url": "https://www.bilibili.com/video/BV1xx411c7mD",
                    }
                ],
                "total": 1,
            }
        }


class TaskCancelResponse(BaseModel):
    """任务取消响应模型"""

    task_id: str = Field(..., description="任务ID")
    message: str = Field(..., description="操作消息")
    status: TaskStatus = Field(..., description="当前任务状态")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "abc123",
                "message": "任务取消请求已发送",
                "status": "cancelled",
            }
        }
