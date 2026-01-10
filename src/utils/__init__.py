"""
工具模块

提供配置、日志、设备管理等通用功能
"""

# 配置管理
from .config import AppConfig, get_config

# 设备管理
from .device import detect_device, get_onnx_providers, print_device_info

# 日志系统
from .logging import get_logger

# 辅助工具 - 延迟导入，避免循环依赖
# 使用方式: from src.utils.helpers import get_task_manager

__all__ = [
    # 配置
    "get_config",
    "AppConfig",
    # 日志
    "get_logger",
    # 设备
    "detect_device",
    "get_onnx_providers",
    "print_device_info",
]
