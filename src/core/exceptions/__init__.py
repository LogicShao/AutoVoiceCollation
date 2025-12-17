"""
异常模块

导出所有自定义异常类
"""

from .base import (
    AutoVoiceCollationError,
    ConfigurationError,
    ValidationError,
    ResourceNotFoundError,
    NetworkError,
    FileOperationError,
)

from .asr import (
    ASRError,
    ASRModelLoadError,
    ASRInferenceError,
    ASRDeviceError,
    AudioFormatError,
)

from .llm import (
    LLMError,
    LLMAPIError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMTimeoutError,
    LLMResponseError,
)

from .task import (
    TaskError,
    TaskCancelledException,
    TaskNotFoundError,
    TaskAlreadyExistsError,
    TaskTimeoutError,
    TaskStatusError,
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
