"""
LLM 相关异常类

定义 LLM（大语言模型）服务相关的异常
"""

from .base import AutoVoiceCollationError


class LLMError(AutoVoiceCollationError):
    """LLM 服务基础异常"""

    def __init__(self, message: str, provider: str | None = None, model: str | None = None):
        details = {}
        if provider:
            details["provider"] = provider
        if model:
            details["model"] = model

        code = f"LLM_ERROR_{provider.upper()}" if provider else "LLM_ERROR"
        super().__init__(message, code, details)


class LLMAPIError(LLMError):
    """LLM API 调用失败异常"""

    def __init__(
        self,
        message: str,
        provider: str,
        status_code: int | None = None,
        api_error_code: str | None = None,
    ):
        super().__init__(message, provider)
        self.code = f"LLM_API_ERROR_{provider.upper()}"
        if status_code:
            self.details["status_code"] = status_code
        if api_error_code:
            self.details["api_error_code"] = api_error_code


class LLMRateLimitError(LLMError):
    """LLM API 速率限制异常"""

    def __init__(self, message: str, provider: str, retry_after: int | None = None):
        super().__init__(message, provider)
        self.code = f"LLM_RATE_LIMIT_{provider.upper()}"
        if retry_after:
            self.details["retry_after"] = retry_after


class LLMAuthenticationError(LLMError):
    """LLM API 认证失败异常"""

    def __init__(self, message: str, provider: str):
        super().__init__(message, provider)
        self.code = f"LLM_AUTH_ERROR_{provider.upper()}"


class LLMTimeoutError(LLMError):
    """LLM API 超时异常"""

    def __init__(self, message: str, provider: str, timeout: float | None = None):
        super().__init__(message, provider)
        self.code = f"LLM_TIMEOUT_{provider.upper()}"
        if timeout:
            self.details["timeout"] = timeout


class LLMResponseError(LLMError):
    """LLM 响应格式错误异常"""

    def __init__(self, message: str, provider: str, response: str | None = None):
        super().__init__(message, provider)
        self.code = f"LLM_RESPONSE_ERROR_{provider.upper()}"
        if response:
            self.details["response"] = response[:200]  # 限制响应长度
