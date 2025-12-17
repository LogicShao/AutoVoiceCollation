"""
文件操作相关异常

定义文件读写操作中的异常类型
"""

from typing import Optional, Dict, Any
from pathlib import Path
from .base import AutoVoiceCollationError


class FileOperationError(AutoVoiceCollationError):
    """文件操作相关异常基类"""

    def __init__(
        self,
        message: str,
        file_path: Optional[Path] = None,
        code: str = "FILE_OPERATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化文件操作异常

        Args:
            message: 错误信息
            file_path: 文件路径
            code: 错误码
            details: 额外详情
        """
        self.file_path = file_path

        # 将文件路径添加到详情中
        if details is None:
            details = {}
        if file_path:
            details["file_path"] = str(file_path)

        super().__init__(message, code, details)


class FileNotFoundError(FileOperationError):
    """文件不存在异常"""

    def __init__(self, file_path: Path):
        super().__init__(
            message=f"文件不存在: {file_path}",
            file_path=file_path,
            code="FILE_NOT_FOUND",
        )


class FileWriteError(FileOperationError):
    """文件写入失败异常"""

    def __init__(
        self,
        file_path: Path,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if details is None:
            details = {}
        if reason:
            details["reason"] = reason

        message = f"文件写入失败: {file_path}"
        if reason:
            message += f" (原因: {reason})"

        super().__init__(
            message=message,
            file_path=file_path,
            code="FILE_WRITE_ERROR",
            details=details,
        )


class FileReadError(FileOperationError):
    """文件读取失败异常"""

    def __init__(
        self,
        file_path: Path,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if details is None:
            details = {}
        if reason:
            details["reason"] = reason

        message = f"文件读取失败: {file_path}"
        if reason:
            message += f" (原因: {reason})"

        super().__init__(
            message=message,
            file_path=file_path,
            code="FILE_READ_ERROR",
            details=details,
        )
