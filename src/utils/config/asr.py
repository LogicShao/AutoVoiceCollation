"""
ASR 配置

管理语音识别相关配置
"""

from typing import Optional
from pydantic import Field, field_validator
from .base import BaseConfig


class ASRConfig(BaseConfig):
    """ASR 配置"""

    # ASR 模型选择
    asr_model: str = Field(
        default="paraformer", description="ASR 模型选择：sense_voice 或 paraformer"
    )

    # 设备配置
    device: str = Field(
        default="auto", description="设备选择：auto, cpu, cuda, cuda:0, cuda:1 等"
    )

    # ONNX 配置
    use_onnx: bool = Field(default=False, description="是否启用 ONNX 推理")

    onnx_providers: str = Field(default="", description="ONNX 执行提供者（逗号分隔）")

    @field_validator("asr_model")
    @classmethod
    def validate_asr_model(cls, v: str) -> str:
        """验证 ASR 模型是否支持"""
        supported_models = ["paraformer", "sense_voice"]
        if v.lower() not in supported_models:
            raise ValueError(
                f"不支持的 ASR 模型: {v}。支持的模型: {', '.join(supported_models)}"
            )
        return v.lower()

    @field_validator("device")
    @classmethod
    def validate_device(cls, v: str) -> str:
        """验证设备配置"""
        v_lower = v.lower()
        valid_prefixes = ["auto", "cpu", "cuda"]

        if not any(v_lower.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(
                f"无效的设备配置: {v}。有效格式: auto, cpu, cuda, cuda:0, cuda:1 等"
            )
        return v

    def get_onnx_providers_list(self) -> Optional[list]:
        """获取 ONNX 提供者列表"""
        if not self.onnx_providers or not self.onnx_providers.strip():
            return None
        return [p.strip() for p in self.onnx_providers.split(",") if p.strip()]
