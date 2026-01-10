"""
路径配置

管理项目中所有目录和文件路径
"""

from pathlib import Path

from pydantic import Field, field_validator

from .base import BaseConfig


class PathConfig(BaseConfig):
    """路径配置"""

    # 输出目录
    output_dir: Path = Field(
        default_factory=lambda: BaseConfig.get_project_root() / "out",
        description="输出目录（处理后的文件存放位置）",
    )

    # 下载目录
    download_dir: Path = Field(
        default_factory=lambda: BaseConfig.get_project_root() / "download",
        description="下载目录（B站音频下载位置）",
    )

    # 临时目录
    temp_dir: Path = Field(
        default_factory=lambda: BaseConfig.get_project_root() / "temp",
        description="临时文件目录",
    )

    # 日志目录
    log_dir: Path = Field(
        default_factory=lambda: BaseConfig.get_project_root() / "logs",
        description="日志目录",
    )

    # 模型目录（None 表示使用系统默认缓存）
    model_dir: Path | None = Field(
        default=None, description="模型缓存目录（留空则使用系统默认缓存目录）"
    )

    @field_validator(
        "output_dir", "download_dir", "temp_dir", "log_dir", "model_dir", mode="before"
    )
    @classmethod
    def resolve_path(cls, v) -> Path | None:
        """解析路径为绝对路径（处理空字符串）"""
        # 处理空字符串或 None
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None

        # 转换为 Path 对象
        if isinstance(v, str):
            v = Path(v)
        elif not isinstance(v, Path):
            return None

        if not v.is_absolute():
            # 相对路径转换为相对于项目根目录的绝对路径
            v = cls.get_project_root() / v
        return v.resolve()

    def ensure_dirs(self, strict: bool = False) -> None:
        """
        确保所有目录存在

        Args:
            strict: 如果为 True，创建失败时抛出异常；否则忽略错误
        """
        for field_name in [
            "output_dir",
            "download_dir",
            "temp_dir",
            "log_dir",
            "model_dir",
        ]:
            path = getattr(self, field_name)
            if path is None:
                continue
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                if strict:
                    raise RuntimeError(f"Failed to create directory {path}: {e}") from e
