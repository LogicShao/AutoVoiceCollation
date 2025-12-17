"""
基础异常类

定义项目统一的异常基类和通用异常类型
"""

from typing import Optional, Dict, Any
from datetime import datetime


class AutoVoiceCollationError(Exception):
    """
    项目基础异常类

    所有项目自定义异常都应继承此类，提供统一的错误码和错误信息格式。

    Attributes:
        message: 错误消息
        code: 错误码（用于 API 响应和日志记录）
        details: 额外的错误详情（可选）
    """

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式（用于 API 响应）

        Returns:
            包含错误信息的字典
        """
        return {
            "error": self.message,
            "code": self.code,
            "type": self.__class__.__name__,
            "timestamp": self.timestamp,
            "details": self.details,
        }

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(message={self.message!r}, code={self.code!r})"
        )


class ConfigurationError(AutoVoiceCollationError):
    """配置错误异常"""

    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {"config_key": config_key} if config_key else {}
        super().__init__(message, "CONFIG_ERROR", details)


class ValidationError(AutoVoiceCollationError):
    """数据验证错误异常"""

    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(message, "VALIDATION_ERROR", details)


class ResourceNotFoundError(AutoVoiceCollationError):
    """资源不存在异常"""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, "RESOURCE_NOT_FOUND", details)


class NetworkError(AutoVoiceCollationError):
    """网络请求错误异常"""

    def __init__(
        self, message: str, url: Optional[str] = None, status_code: Optional[int] = None
    ):
        details = {}
        if url:
            details["url"] = url
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, "NETWORK_ERROR", details)


class FileOperationError(AutoVoiceCollationError):
    """文件操作错误异常"""

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
    ):
        details = {}
        if file_path:
            details["file_path"] = file_path
        if operation:
            details["operation"] = operation
        super().__init__(message, "FILE_OPERATION_ERROR", details)
