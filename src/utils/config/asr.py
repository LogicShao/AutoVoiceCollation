"""
ASR 配置

管理语音识别相关配置
"""

from pathlib import Path

from pydantic import Field, field_validator

from .base import BaseConfig


class ASRConfig(BaseConfig):
    """ASR 配置"""

    # ASR 模型选择
    asr_model: str = Field(
        default="paraformer", description="ASR 模型选择：sense_voice 或 paraformer"
    )

    # 设备配置
    device: str = Field(default="auto", description="设备选择：auto, cpu, cuda, cuda:0, cuda:1 等")

    # whisper.cpp 配置（可选，仅在 ASR_MODEL=whisper_cpp 时生效）
    whisper_cpp_bin: Path | None = Field(
        default=None,
        description="whisper.cpp CLI 可执行文件路径（例如：./assets/whisper.cpp/whisper-cli.exe）",
    )

    whisper_cpp_model: Path | None = Field(
        default=None,
        description="whisper.cpp ggml 模型文件路径（例如：./assets/models/ggml-medium-q5_0.bin）",
    )

    whisper_cpp_language: str = Field(
        default="auto", description="whisper.cpp 语言（auto/zh/en/...）"
    )

    whisper_cpp_threads: int = Field(default=4, ge=1, description="whisper.cpp threads")

    whisper_cpp_extra_args: str = Field(
        default="",
        description="额外传给 whisper-cli.exe 的参数（原样拼接；例如：--vad --no-gpu）",
    )

    whisper_cpp_vad: bool = Field(
        default=False, description="whisper.cpp 是否启用 VAD（需要提供 VAD 模型）"
    )

    whisper_cpp_vad_model: Path | None = Field(
        default=None,
        description="whisper.cpp VAD 模型文件路径（例如：./assets/models/ggml-silero-v6.2.0.bin）",
    )

    # ONNX 配置
    use_onnx: bool = Field(default=False, description="是否启用 ONNX 推理")

    onnx_providers: str = Field(default="", description="ONNX 执行提供者（逗号分隔）")

    @field_validator("asr_model")
    @classmethod
    def validate_asr_model(cls, v: str) -> str:
        """验证 ASR 模型是否支持"""
        supported_models = ["paraformer", "sense_voice", "whisper_cpp"]
        if v.lower() not in supported_models:
            raise ValueError(f"不支持的 ASR 模型: {v}。支持的模型: {', '.join(supported_models)}")
        return v.lower()

    @field_validator("device")
    @classmethod
    def validate_device(cls, v: str) -> str:
        """验证设备配置"""
        v_lower = v.lower()
        valid_prefixes = ["auto", "cpu", "cuda"]

        if not any(v_lower.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(f"无效的设备配置: {v}。有效格式: auto, cpu, cuda, cuda:0, cuda:1 等")
        return v

    @field_validator("whisper_cpp_bin", "whisper_cpp_model", "whisper_cpp_vad_model", mode="before")
    @classmethod
    def resolve_whisper_cpp_path(cls, v) -> Path | None:
        """解析 whisper.cpp 相关路径（支持项目相对路径；空值视为未配置）。"""
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None

        if isinstance(v, str):
            v = Path(v)
        elif not isinstance(v, Path):
            return None

        if not v.is_absolute():
            v = cls.get_project_root() / v
        return v.resolve()

    @field_validator("whisper_cpp_language")
    @classmethod
    def normalize_whisper_cpp_language(cls, v: str) -> str:
        return v.strip().lower()

    def get_onnx_providers_list(self) -> list | None:
        """获取 ONNX 提供者列表"""
        if not self.onnx_providers or not self.onnx_providers.strip():
            return None
        return [p.strip() for p in self.onnx_providers.split(",") if p.strip()]
