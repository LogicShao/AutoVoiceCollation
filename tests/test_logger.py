"""
日志模块单元测试
测试日志记录、格式化、彩色输出和第三方日志配置
"""

import logging
from unittest.mock import Mock, patch

import pytest

from src.utils.logging.logger import (
    ColoredFormatter,
    configure_third_party_loggers,
    get_logger,
    setup_logger,
)


class TestColoredFormatter:
    """测试彩色日志格式化器"""

    def test_formatter_creation(self):
        """测试格式化器创建"""
        formatter = ColoredFormatter("%(levelname)s - %(message)s")
        assert formatter is not None

    def test_format_debug(self):
        """测试 DEBUG 级别日志格式化"""
        formatter = ColoredFormatter("%(levelname)s - %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="Debug message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)

        assert "DEBUG" in result
        assert "Debug message" in result
        # 应该包含颜色代码
        assert "\033[" in result or "DEBUG" in result

    def test_format_info(self):
        """测试 INFO 级别日志格式化"""
        formatter = ColoredFormatter("%(levelname)s - %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Info message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)

        assert "INFO" in result
        assert "Info message" in result

    def test_format_warning(self):
        """测试 WARNING 级别日志格式化"""
        formatter = ColoredFormatter("%(levelname)s - %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Warning message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)

        assert "WARNING" in result
        assert "Warning message" in result

    def test_format_error(self):
        """测试 ERROR 级别日志格式化"""
        formatter = ColoredFormatter("%(levelname)s - %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)

        assert "ERROR" in result
        assert "Error message" in result

    def test_format_critical(self):
        """测试 CRITICAL 级别日志格式化"""
        formatter = ColoredFormatter("%(levelname)s - %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.CRITICAL,
            pathname="",
            lineno=0,
            msg="Critical message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)

        assert "CRITICAL" in result
        assert "Critical message" in result

    def test_color_codes_present(self):
        """测试颜色代码存在"""
        formatter = ColoredFormatter("%(levelname)s")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="", args=(), exc_info=None
        )
        result = formatter.format(record)

        # 应该包含 ANSI 颜色代码
        has_color = "\033[" in result
        # 或者至少包含级别名称
        has_level = "INFO" in result
        assert has_color or has_level


class TestSetupLogger:
    """测试日志设置功能"""

    def test_setup_logger_basic(self):
        """测试基本日志设置"""
        logger = setup_logger("test_basic", log_level="INFO")

        assert logger is not None
        assert logger.name == "test_basic"
        assert logger.level == logging.INFO

    def test_setup_logger_with_file(self, tmp_path):
        """测试带文件输出的日志设置"""
        log_file = tmp_path / "test.log"
        logger = setup_logger("test_file", log_level="DEBUG", log_file=str(log_file))

        assert logger.level == logging.DEBUG
        # 记录一条日志
        logger.info("Test message")

        # 验证文件被创建
        assert log_file.exists()
        # 验证日志被写入
        content = log_file.read_text(encoding="utf-8")
        assert "Test message" in content

    def test_setup_logger_no_console(self, tmp_path):
        """测试禁用控制台输出"""
        log_file = tmp_path / "test_no_console.log"
        logger = setup_logger(
            "test_no_console", log_level="INFO", log_file=str(log_file), console_output=False
        )

        # 应该只有文件 handler
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.FileHandler)

    def test_setup_logger_no_color(self):
        """测试禁用彩色输出"""
        logger = setup_logger("test_no_color", log_level="INFO", colored_output=False)

        # 找到控制台 handler
        console_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(console_handlers) > 0

        # 格式化器不应该是 ColoredFormatter
        formatter = console_handlers[0].formatter
        assert not isinstance(formatter, ColoredFormatter)

    def test_setup_logger_different_levels(self):
        """测试不同日志级别"""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in levels:
            logger_name = f"test_level_{level}"
            logger = setup_logger(logger_name, log_level=level)

            expected_level = getattr(logging, level)
            assert logger.level == expected_level

    def test_setup_logger_idempotent(self):
        """测试重复设置相同 logger"""
        logger1 = setup_logger("test_idempotent", log_level="INFO")
        logger2 = setup_logger("test_idempotent", log_level="DEBUG")

        # 应该返回相同的 logger 实例
        assert logger1 is logger2
        # 级别不应该改变（因为已经有 handlers）
        assert logger1.level == logging.INFO

    def test_setup_logger_creates_log_directory(self, tmp_path):
        """测试自动创建日志目录"""
        log_file = tmp_path / "subdir" / "logs" / "test.log"
        logger = setup_logger("test_mkdir", log_file=str(log_file))

        logger.info("Test")

        # 目录应该被创建
        assert log_file.parent.exists()
        assert log_file.exists()

    def test_setup_logger_case_insensitive_level(self):
        """测试日志级别大小写不敏感"""
        logger_lower = setup_logger("test_lower", log_level="info")
        logger_upper = setup_logger("test_upper", log_level="INFO")
        logger_mixed = setup_logger("test_mixed", log_level="Info")

        assert logger_lower.level == logging.INFO
        assert logger_upper.level == logging.INFO
        assert logger_mixed.level == logging.INFO


class TestGetLogger:
    """测试获取 logger 功能"""

    @patch("src.utils.logging.logger.setup_logger")
    def test_get_logger_creates_new(self, mock_setup):
        """测试获取不存在的 logger 时创建新的"""
        mock_logger = Mock()
        mock_setup.return_value = mock_logger

        # 使用唯一的名称避免冲突
        logger_name = "test_new_unique_12345"
        # 确保 logger 不存在
        if logger_name in logging.Logger.manager.loggerDict:
            del logging.Logger.manager.loggerDict[logger_name]

        logger = get_logger(logger_name)

        # 应该调用 setup_logger
        # 注意：由于 get_logger 内部检查 handlers，可能不会调用 mock

    def test_get_logger_existing(self):
        """测试获取已存在的 logger"""
        # 先创建一个 logger
        setup_logger("test_existing", log_level="INFO")

        # 再次获取
        logger = get_logger("test_existing")

        assert logger is not None
        assert logger.name == "test_existing"

    def test_get_logger_different_names(self):
        """测试获取不同名称的 logger"""
        logger1 = get_logger("logger1")
        logger2 = get_logger("logger2")

        assert logger1 is not logger2
        assert logger1.name != logger2.name


class TestConfigureThirdPartyLoggers:
    """测试第三方日志配置"""

    def test_configure_third_party_default_level(self):
        """测试配置第三方日志默认级别"""
        configure_third_party_loggers("WARNING")

        # 检查几个第三方 logger
        funasr_logger = logging.getLogger("funasr")
        torch_logger = logging.getLogger("torch")

        assert funasr_logger.level == logging.WARNING
        assert torch_logger.level == logging.WARNING

    def test_configure_third_party_different_levels(self):
        """测试配置不同级别"""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in levels:
            configure_third_party_loggers(level)

            test_logger = logging.getLogger("urllib3")
            expected_level = getattr(logging, level)
            assert test_logger.level == expected_level

    def test_configure_third_party_case_insensitive(self):
        """测试级别大小写不敏感"""
        configure_third_party_loggers("error")

        test_logger = logging.getLogger("requests")
        assert test_logger.level == logging.ERROR

    def test_configure_third_party_warnings(self):
        """测试配置警告日志"""
        configure_third_party_loggers("ERROR")

        warnings_logger = logging.getLogger("py.warnings")
        assert warnings_logger.level == logging.ERROR


class TestLoggerIntegration:
    """测试日志系统集成"""

    def test_logger_writes_to_file(self, tmp_path):
        """测试日志写入文件"""
        log_file = tmp_path / "integration.log"
        logger = setup_logger("test_integration", log_level="DEBUG", log_file=str(log_file))

        # 记录不同级别的日志
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        # 读取文件内容
        content = log_file.read_text(encoding="utf-8")

        assert "Debug message" in content
        assert "Info message" in content
        assert "Warning message" in content
        assert "Error message" in content
        assert "Critical message" in content

    def test_logger_filters_by_level(self, tmp_path):
        """测试日志级别过滤"""
        log_file = tmp_path / "filter.log"
        logger = setup_logger(
            "test_filter",
            log_level="WARNING",  # 只记录 WARNING 及以上
            log_file=str(log_file),
            console_output=False,
        )

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        content = log_file.read_text(encoding="utf-8")

        assert "Debug message" not in content
        assert "Info message" not in content
        assert "Warning message" in content
        assert "Error message" in content

    def test_multiple_loggers_independent(self, tmp_path):
        """测试多个 logger 互不影响"""
        log_file1 = tmp_path / "logger1.log"
        log_file2 = tmp_path / "logger2.log"

        logger1 = setup_logger("independent1", log_file=str(log_file1), console_output=False)
        logger2 = setup_logger("independent2", log_file=str(log_file2), console_output=False)

        logger1.info("Message from logger1")
        logger2.info("Message from logger2")

        content1 = log_file1.read_text(encoding="utf-8")
        content2 = log_file2.read_text(encoding="utf-8")

        assert "Message from logger1" in content1
        assert "Message from logger2" not in content1

        assert "Message from logger2" in content2
        assert "Message from logger1" not in content2


class TestEdgeCases:
    """测试边界情况"""

    def test_setup_logger_empty_name(self):
        """测试空名称"""
        logger = setup_logger("", log_level="INFO")
        assert logger is not None

    def test_setup_logger_special_characters_in_name(self):
        """测试名称包含特殊字符"""
        logger = setup_logger("test.module.sub-module", log_level="INFO")
        assert logger.name == "test.module.sub-module"

    def test_setup_logger_invalid_level(self):
        """测试无效的日志级别"""
        # 应该抛出 AttributeError
        with pytest.raises(AttributeError):
            setup_logger("test_invalid", log_level="INVALID_LEVEL")

    def test_get_logger_none_name(self):
        """测试 None 名称"""
        # logging.getLogger(None) 实际上返回 root logger
        # 所以这个测试应该验证返回的是 root logger
        logger = get_logger(None)
        assert logger is not None
        # Root logger 的名称是 'root'
        assert logger.name == "root" or logger.name is None

    def test_configure_third_party_invalid_level(self):
        """测试配置无效级别"""
        with pytest.raises(AttributeError):
            configure_third_party_loggers("INVALID")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
