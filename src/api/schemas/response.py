"""
响应 Schema

定义通用 API 响应的 Pydantic 模型
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SuccessResponse(BaseModel):
    """成功响应基础模型"""

    success: bool = Field(True, description="操作是否成功")
    message: str = Field(..., description="响应消息")
    data: dict[str, Any] | None = Field(None, description="响应数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "操作成功",
                "data": {"key": "value"},
                "timestamp": "2025-12-16T10:30:00",
            }
        }


class ErrorResponse(BaseModel):
    """错误响应模型"""

    error: str = Field(..., description="错误信息")
    code: str = Field(..., description="错误码")
    type: str = Field(..., description="错误类型")
    details: dict[str, Any] | None = Field(None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.now, description="错误时间戳")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "任务不存在",
                "code": "TASK_NOT_FOUND",
                "type": "TaskNotFoundError",
                "details": {"task_id": "abc123"},
                "timestamp": "2025-12-16T10:30:00",
            }
        }


class FileDownloadInfo(BaseModel):
    """文件下载信息"""

    task_id: str = Field(..., description="任务ID")
    file_name: str = Field(..., description="文件名")
    file_path: str = Field(..., description="文件路径")
    file_size: int | None = Field(None, description="文件大小（字节）")
    mime_type: str | None = Field(None, description="MIME 类型")
    download_url: str = Field(..., description="下载 URL")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "abc123",
                "file_name": "output.pdf",
                "file_path": "/out/video_title/output.pdf",
                "file_size": 1024000,
                "mime_type": "application/pdf",
                "download_url": "/api/v1/download/abc123/output.pdf",
            }
        }


class HealthCheckResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(..., description="服务状态")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")
    services: dict[str, str] = Field(..., description="各服务状态")
    version: str | None = Field(None, description="API 版本")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-12-16T10:30:00",
                "services": {
                    "asr": "operational",
                    "llm": "operational",
                    "storage": "operational",
                },
                "version": "1.0.0",
            }
        }
