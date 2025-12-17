"""
配置基类

提供统一的配置加载和验证机制
"""

from pathlib import Path
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class BaseConfig(BaseSettings):
    """
    配置基类

    所有配置类应继承此基类以获得：
    - 自动从 .env 文件加载配置
    - 类型验证和转换
    - 环境变量覆盖支持
    """

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # 允许额外字段
        extra="ignore",
        # 验证赋值
        validate_assignment=True,
    )

    @classmethod
    def get_project_root(cls) -> Path:
        """获取项目根目录"""
        # 从当前文件向上查找项目根目录
        current = Path(__file__).resolve()
        while current.parent != current:
            if (current / ".env.example").exists() or (
                current / "requirements.txt"
            ).exists():
                return current
            current = current.parent
        return Path.cwd()
