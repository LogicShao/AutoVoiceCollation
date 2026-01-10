"""
下载相关异常

定义视频/音频下载过程中的异常类型
"""

from typing import Any

from .base import AutoVoiceCollationError


class DownloadError(AutoVoiceCollationError):
    """下载相关异常基类"""

    def __init__(
        self,
        message: str,
        url: str | None = None,
        code: str = "DOWNLOAD_ERROR",
        details: dict[str, Any] | None = None,
    ):
        """
        初始化下载异常

        Args:
            message: 错误信息
            url: 下载URL
            code: 错误码
            details: 额外详情
        """
        self.url = url

        # 将URL添加到详情中
        if details is None:
            details = {}
        if url:
            details["url"] = url

        super().__init__(message, code, details)


class VideoNotFoundError(DownloadError):
    """视频不存在异常"""

    def __init__(self, url: str):
        super().__init__(message=f"视频不存在或无法访问: {url}", url=url, code="VIDEO_NOT_FOUND")


class VideoUnavailableError(DownloadError):
    """视频不可用异常"""

    def __init__(
        self,
        url: str,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        if details is None:
            details = {}
        if reason:
            details["reason"] = reason

        message = f"视频不可用: {url}"
        if reason:
            message += f" (原因: {reason})"

        super().__init__(message=message, url=url, code="VIDEO_UNAVAILABLE", details=details)


class NetworkError(DownloadError):
    """网络错误异常"""

    def __init__(
        self,
        message: str,
        url: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message=message, url=url, code="NETWORK_ERROR", details=details)
