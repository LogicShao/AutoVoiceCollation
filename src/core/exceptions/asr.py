"""
ASR 相关异常类

定义 ASR（自动语音识别）服务相关的异常
"""

from .base import AutoVoiceCollationError


class ASRError(AutoVoiceCollationError):
    """ASR 服务基础异常"""

    def __init__(
        self,
        message: str,
        model: str | None = None,
        audio_file: str | None = None,
    ):
        details = {}
        if model:
            details["model"] = model
        if audio_file:
            details["audio_file"] = audio_file

        code = f"ASR_ERROR_{model.upper()}" if model else "ASR_ERROR"
        super().__init__(message, code, details)


class ASRModelLoadError(ASRError):
    """ASR 模型加载失败异常"""

    def __init__(self, message: str, model: str):
        super().__init__(message, model)
        self.code = f"ASR_MODEL_LOAD_ERROR_{model.upper()}"


class ASRInferenceError(ASRError):
    """ASR 推理失败异常"""

    def __init__(self, message: str, model: str, audio_file: str | None = None):
        super().__init__(message, model, audio_file)
        self.code = f"ASR_INFERENCE_ERROR_{model.upper()}"


class ASRDeviceError(ASRError):
    """ASR 设备错误异常（如 CUDA OOM）"""

    def __init__(self, message: str, device: str, model: str | None = None):
        details = {"device": device}
        if model:
            details["model"] = model
        super().__init__(message, model)
        self.code = "ASR_DEVICE_ERROR"
        self.details.update(details)


class AudioFormatError(ASRError):
    """音频格式不支持异常"""

    def __init__(self, message: str, audio_file: str, format: str | None = None):
        details = {"audio_file": audio_file}
        if format:
            details["format"] = format
        super().__init__(message, audio_file=audio_file)
        self.code = "AUDIO_FORMAT_ERROR"
        self.details.update(details)
