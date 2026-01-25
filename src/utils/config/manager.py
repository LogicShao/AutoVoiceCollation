"""
配置管理器

统一管理所有配置并提供全局访问接口
"""

from pathlib import Path

from pydantic import Field, field_validator

from .asr import ASRConfig
from .base import BaseConfig
from .llm import LLMConfig
from .logging import LoggingConfig
from .paths import PathConfig


class AppConfig(BaseConfig):
    """
    应用配置

    整合所有配置模块，提供统一的配置访问接口
    """

    # 子配置模块
    paths: PathConfig = Field(default_factory=PathConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    asr: ASRConfig = Field(default_factory=ASRConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # 输出配置
    output_style: str = Field(
        default="pdf_only",
        description="输出样式：pdf_with_img, img_only, text_only, pdf_only, markdown, json",
    )

    pdf_font_path: Path | None = Field(
        default=None, description="PDF 主字体路径（留空则自动检测系统字体）"
    )

    pdf_latin_font_path: Path | None = Field(
        default=None, description="PDF 拉丁字符字体路径（留空则自动检测系统字体）"
    )

    zip_output_enabled: bool = Field(default=False, description="是否输出 zip 压缩包")

    text_only_default: bool = Field(
        default=False, description="Web 前端中是否默认仅返回纯文本（JSON）结果"
    )

    # Web 服务器配置
    web_server_port: int | None = Field(
        default=None, description="Web 服务器端口（留空则不启动 Web 服务）"
    )

    # 缓存配置
    cache_ttl_seconds: int = Field(default=3600, ge=0, description="缓存过期时间（秒）")

    # 调试配置
    debug_flag: bool = Field(default=False, description="调试模式")

    enable_strict_validation: bool = Field(default=False, description="是否启用严格验证模式")

    @field_validator("output_style")
    @classmethod
    def validate_output_style(cls, v: str) -> str:
        """验证输出样式"""
        valid_styles = [
            "pdf_with_img",
            "img_only",
            "text_only",
            "pdf_only",
            "markdown",
            "json",
        ]
        if v not in valid_styles:
            raise ValueError(f"无效的输出样式: {v}。有效样式: {', '.join(valid_styles)}")
        return v

    @field_validator("web_server_port", mode="before")
    @classmethod
    def validate_port(cls, v) -> int | None:
        """验证端口号（处理空字符串）"""
        # 处理空字符串或 None
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None

        # 转换为整数
        try:
            port = int(v)
        except (ValueError, TypeError) as e:
            raise ValueError(f"无效的端口号: {v}。必须是 1-65535 之间的整数或留空") from e

        # 验证端口范围
        if port < 1 or port > 65535:
            raise ValueError(f"无效的端口号: {port}。端口范围: 1-65535")

        return port

    def initialize(self) -> None:
        """
        初始化配置

        - 创建必要的目录
        - 验证配置的有效性
        """
        # 创建目录
        self.paths.ensure_dirs(strict=self.enable_strict_validation)
        if self.logging.log_file is None and self.paths.log_dir is not None:
            self.logging.log_file = self.paths.log_dir / "AutoVoiceCollation.log"
        self.logging.ensure_log_dir(strict=self.enable_strict_validation)

        # 验证 LLM 服务支持
        self.llm.validate_server_support()

        # 检查 API Key（非严格模式下仅警告）
        if not self.llm.has_valid_api_key():
            message = "警告: 未配置任何 LLM API Key，某些功能可能无法使用"
            if self.enable_strict_validation:
                raise ValueError(message)
            print(f"⚠️  {message}")


# 全局配置实例
_config: AppConfig | None = None


def get_config(reload: bool = False) -> AppConfig:
    """
    获取全局配置实例

    Args:
        reload: 是否重新加载配置（默认 False）

    Returns:
        AppConfig: 全局配置实例
    """
    global _config

    if _config is None or reload:
        _config = AppConfig()
        _config.initialize()

    return _config


def reset_config() -> None:
    """重置全局配置实例（主要用于测试）"""
    global _config
    _config = None
