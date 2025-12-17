"""
任务相关数据模型

定义任务状态、任务结果等数据结构
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskResult(BaseModel):
    """任务处理结果"""

    # 基础信息
    task_id: str = Field(..., description="任务唯一标识")
    status: TaskStatus = Field(..., description="任务状态")
    message: str = Field(default="", description="状态消息")

    # 时间信息
    created_at: datetime = Field(..., description="任务创建时间")
    started_at: Optional[datetime] = Field(default=None, description="任务开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="任务完成时间")

    # 处理结果
    result: Optional[Dict[str, Any]] = Field(default=None, description="处理结果数据")
    error: Optional[str] = Field(default=None, description="错误信息")

    # 元数据
    url: Optional[str] = Field(default=None, description="处理的 URL（如 B站视频）")
    filename: Optional[str] = Field(default=None, description="处理的文件名")

    class Config:
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class ProcessingTask(BaseModel):
    """处理任务配置"""

    # LLM 配置
    llm_api: str = Field(..., description="LLM 服务提供商")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="LLM 温度参数")
    max_tokens: int = Field(default=6000, gt=0, description="LLM 最大 tokens")

    # 处理选项
    text_only: bool = Field(default=False, description="仅返回文本结果")
    summarize: bool = Field(default=False, description="是否生成摘要")

    # 任务控制
    task_id: Optional[str] = Field(default=None, description="任务 ID")

    class Config:
        json_schema_extra = {
            "example": {
                "llm_api": "Cerebras:Qwen-3-235B-Instruct",
                "temperature": 0.1,
                "max_tokens": 6000,
                "text_only": False,
                "summarize": False,
            }
        }
