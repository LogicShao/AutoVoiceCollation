"""
统一的日志管理模块
提供项目范围内的日志记录功能
"""

import logging
import sys
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器（仅在终端输出时使用）"""

    # ANSI 颜色代码
    COLORS = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[32m",  # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record):
        # 创建 record 的副本，避免影响其他 handler
        record_copy = logging.makeLogRecord(record.__dict__)

        # 只对 levelname 添加颜色
        levelname = record_copy.levelname
        if levelname in self.COLORS:
            record_copy.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record_copy)


def setup_logger(
    name: str,
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    console_output: bool = True,
    colored_output: bool = True,
) -> logging.Logger:
    """
    设置并返回一个配置好的 logger

    :param name: logger 名称（通常使用 __name__）
    :param log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    :param log_file: 日志文件路径，如果为 None 则不写入文件
    :param console_output: 是否输出到控制台
    :param colored_output: 控制台输出是否使用彩色
    :return: 配置好的 logger 对象
    """
    logger = logging.getLogger(name)

    # 如果 logger 已经有 handlers，说明已经配置过，直接返回
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, log_level.upper()))
    logger.propagate = False  # 防止日志传播到父 logger

    # 日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))

        if colored_output:
            console_formatter = ColoredFormatter(log_format, datefmt=date_format)
        else:
            console_formatter = logging.Formatter(log_format, datefmt=date_format)

        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # 文件处理器 - 始终使用无颜色的格式
    if log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, log_level.upper()))
        # 文件输出不使用颜色格式
        file_formatter = logging.Formatter(log_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取已配置的 logger，如果不存在则使用默认配置创建

    :param name: logger 名称（通常使用 __name__）
    :return: logger 对象
    """
    logger = logging.getLogger(name)

    # 如果 logger 还没有配置，使用默认配置
    if not logger.handlers:
        # 延迟导入配置，避免循环导入
        # 当 src.config 正在初始化时，使用默认值
        try:
            from src.config import (
                LOG_LEVEL,
                LOG_FILE,
                LOG_CONSOLE_OUTPUT,
                LOG_COLORED_OUTPUT,
            )

            log_level = LOG_LEVEL
            log_file = LOG_FILE
            console_output = LOG_CONSOLE_OUTPUT
            colored_output = LOG_COLORED_OUTPUT
        except (ImportError, AttributeError):
            # 配置模块未完全加载，使用默认值
            log_level = "INFO"
            log_file = None
            console_output = True
            colored_output = True

        return setup_logger(
            name=name,
            log_level=log_level,
            log_file=log_file,
            console_output=console_output,
            colored_output=colored_output,
        )

    return logger


def configure_third_party_loggers(log_level: str = "WARNING"):
    """
    配置第三方库的日志级别，避免其输出过多信息

    :param log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # 常见的第三方库日志名称
    third_party_loggers = [
        "funasr",
        "modelscope",
        "torch",
        "transformers",
        "tensorflow",
        "PIL",
        "matplotlib",
        "urllib3",
        "requests",
        "httpx",
        "httpcore",
    ]

    level = getattr(logging, log_level.upper())

    for logger_name in third_party_loggers:
        third_party_logger = logging.getLogger(logger_name)
        third_party_logger.setLevel(level)

    # 特别处理 root logger 的 WARNING 消息
    logging.captureWarnings(True)
    warnings_logger = logging.getLogger("py.warnings")
    warnings_logger.setLevel(level)
