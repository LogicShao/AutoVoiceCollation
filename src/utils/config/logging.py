"""
日志配置

管理日志系统相关配置
"""

from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator
from .base import BaseConfig


class LoggingConfig(BaseConfig):
    """日志配置"""

    # 日志级别
    log_level: str = Field(
        default="INFO", description="日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )

    # 日志文件
    log_file: Optional[Path] = Field(
        default=None, description="日志文件路径（留空则不写入文件）"
    )

    # 控制台输出
    log_console_output: bool = Field(default=True, description="是否输出到控制台")

    # 彩色输出
    log_colored_output: bool = Field(default=True, description="控制台输出是否使用彩色")

    # 第三方库日志级别
    third_party_log_level: str = Field(default="ERROR", description="第三方库日志级别")

    @field_validator("log_level", "third_party_log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(
                f"无效的日志级别: {v}。有效级别: {', '.join(valid_levels)}"
            )
        return v_upper

    @field_validator("log_file", mode="before")
    @classmethod
    def resolve_log_file(cls, v) -> Optional[Path]:
        """解析日志文件路径（处理空字符串）"""
        # 处理空字符串或 None
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None

        # 转换为 Path 对象
        if isinstance(v, str):
            v = Path(v)
        elif not isinstance(v, Path):
            return None

        if not v.is_absolute():
            v = cls.get_project_root() / v
        return v.resolve()

    def ensure_log_dir(self, strict: bool = False) -> None:
        """确保日志目录存在"""
        if self.log_file is None:
            return
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            if strict:
                raise RuntimeError(f"Failed to create log directory: {e}") from e
