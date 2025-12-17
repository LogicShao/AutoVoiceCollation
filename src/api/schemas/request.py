"""
请求 Schema

定义 API 请求的 Pydantic 模型
"""

from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl, field_validator


class BilibiliProcessRequest(BaseModel):
    """B站视频处理请求"""

    url: HttpUrl = Field(
        ...,
        description="B站视频 URL",
        examples=["https://www.bilibili.com/video/BV1xx411c7mD"],
    )

    disable_llm_polish: Optional[bool] = Field(
        None, description="是否禁用 LLM 润色（覆盖全局配置）"
    )

    disable_llm_summary: Optional[bool] = Field(
        None, description="是否禁用 LLM 摘要（覆盖全局配置）"
    )

    output_style: Optional[str] = Field(
        None,
        description="输出样式：pdf_only, pdf_with_img, img_only, text_only",
        examples=["pdf_only"],
    )

    @field_validator("output_style")
    @classmethod
    def validate_output_style(cls, v: Optional[str]) -> Optional[str]:
        """验证输出样式"""
        if v is not None:
            valid_styles = ["pdf_only", "pdf_with_img", "img_only", "text_only"]
            if v not in valid_styles:
                raise ValueError(
                    f"无效的输出样式: {v}。有效值: {', '.join(valid_styles)}"
                )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.bilibili.com/video/BV1xx411c7mD",
                "disable_llm_polish": False,
                "disable_llm_summary": False,
                "output_style": "pdf_only",
            }
        }


class AudioProcessRequest(BaseModel):
    """音频文件处理请求（用于文档说明）"""

    # 注意：实际使用 FastAPI 的 File upload，这里仅用于文档
    disable_llm_polish: Optional[bool] = Field(None, description="是否禁用 LLM 润色")

    disable_llm_summary: Optional[bool] = Field(None, description="是否禁用 LLM 摘要")

    output_style: Optional[str] = Field(None, description="输出样式")

    class Config:
        json_schema_extra = {
            "example": {
                "file": "(binary audio file)",
                "disable_llm_polish": False,
                "output_style": "pdf_only",
            }
        }


class BatchProcessRequest(BaseModel):
    """批量处理请求"""

    urls: List[HttpUrl] = Field(
        ..., description="B站视频 URL 列表", min_length=1, max_length=100
    )

    disable_llm_polish: Optional[bool] = Field(None, description="是否禁用 LLM 润色")

    disable_llm_summary: Optional[bool] = Field(None, description="是否禁用 LLM 摘要")

    output_style: Optional[str] = Field(None, description="输出样式")

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: List[HttpUrl]) -> List[HttpUrl]:
        """验证 URL 列表"""
        if len(v) > 100:
            raise ValueError("批量处理最多支持 100 个 URL")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "urls": [
                    "https://www.bilibili.com/video/BV1xx411c7mD",
                    "https://www.bilibili.com/video/BV1yy411c7mE",
                ],
                "disable_llm_polish": False,
                "output_style": "pdf_only",
            }
        }
