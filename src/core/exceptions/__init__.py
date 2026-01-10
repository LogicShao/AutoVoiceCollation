"""
异常模块

导出所有自定义异常类
"""

from .asr import (
    ASRDeviceError,
    ASRError,
    ASRInferenceError,
    ASRModelLoadError,
    AudioFormatError,
)
from .base import (
    AutoVoiceCollationError,
    ConfigurationError,
    FileOperationError,
    NetworkError,
    ResourceNotFoundError,
    ValidationError,
)
from .llm import (
    LLMAPIError,
    LLMAuthenticationError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)
from .task import (
    TaskAlreadyExistsError,
    TaskCancelledException,
    TaskError,
    TaskNotFoundError,
    TaskStatusError,
    TaskTimeoutError,
)

__all__ = [
    # 基础异常
    "AutoVoiceCollationError",
    "ConfigurationError",
    "ValidationError",
    "ResourceNotFoundError",
    "NetworkError",
    "FileOperationError",
    # ASR 异常
    "ASRError",
    "ASRModelLoadError",
    "ASRInferenceError",
    "ASRDeviceError",
    "AudioFormatError",
    # LLM 异常
    "LLMError",
    "LLMAPIError",
    "LLMRateLimitError",
    "LLMAuthenticationError",
    "LLMTimeoutError",
    "LLMResponseError",
    # 任务异常
    "TaskError",
    "TaskCancelledException",
    "TaskNotFoundError",
    "TaskAlreadyExistsError",
    "TaskTimeoutError",
    "TaskStatusError",
]
