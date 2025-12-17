"""
视频相关数据模型

定义视频信息、B站视频文件等数据结构
"""

from typing import Optional
from pydantic import BaseModel, Field


class VideoInfo(BaseModel):
    """视频信息"""

    # 基础信息
    title: str = Field(..., description="视频标题")
    url: Optional[str] = Field(default=None, description="视频 URL")
    duration: Optional[int] = Field(default=None, description="视频时长（秒）")

    # 创作者信息
    author: Optional[str] = Field(default=None, description="作者/UP主")
    author_id: Optional[str] = Field(default=None, description="作者 ID")

    # 平台信息
    platform: str = Field(default="bilibili", description="视频平台")
    video_id: Optional[str] = Field(default=None, description="视频 ID")

    # 文件信息
    file_path: Optional[str] = Field(default=None, description="本地文件路径")
    file_size: Optional[int] = Field(default=None, description="文件大小（字节）")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Python 教程",
                "url": "https://www.bilibili.com/video/BV1xx411c7mD",
                "duration": 3600,
                "author": "UP主名称",
                "platform": "bilibili",
                "video_id": "BV1xx411c7mD",
            }
        }


class ProcessResult(BaseModel):
    """处理结果"""

    # 输出信息
    output_dir: str = Field(..., description="输出目录路径")

    # 性能指标
    extract_time: float = Field(..., description="ASR 提取时间（秒）")
    polish_time: float = Field(..., description="LLM 润色时间（秒）")
    total_time: Optional[float] = Field(default=None, description="总处理时间（秒）")

    # 文件输出
    zip_file: Optional[str] = Field(default=None, description="ZIP 压缩包路径")
    pdf_file: Optional[str] = Field(default=None, description="PDF 文件路径")

    # 文本内容（text_only 模式）
    raw_text: Optional[str] = Field(default=None, description="ASR 原始文本")
    polished_text: Optional[str] = Field(default=None, description="润色后文本")
    summary: Optional[str] = Field(default=None, description="摘要")

    class Config:
        json_schema_extra = {
            "example": {
                "output_dir": "/path/to/output",
                "extract_time": 12.5,
                "polish_time": 8.3,
                "total_time": 20.8,
                "zip_file": "/path/to/output.zip",
            }
        }
