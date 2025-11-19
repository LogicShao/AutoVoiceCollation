"""
配置管理模块单元测试
测试环境变量加载、类型转换、验证和配置快照功能
"""
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import (
    _str_to_bool,
    _get_env,
)


class TestStrToBool:
    """测试字符串转布尔值功能"""

    def test_true_values(self):
        """测试 True 值"""
        true_values = ["1", "true", "True", "TRUE", "yes", "Yes", "YES", "on", "On", "ON"]
        for val in true_values:
            result = _str_to_bool(val)
            assert result is True, f"Expected True for '{val}', got {result}"

    def test_false_values(self):
        """测试 False 值"""
        false_values = ["0", "false", "False", "FALSE", "no", "No", "NO", "off", "Off", "OFF", ""]
        for val in false_values:
            result = _str_to_bool(val)
            assert result is False, f"Expected False for '{val}', got {result}"

    def test_none_input(self):
        """测试 None 输入"""
        result = _str_to_bool(None)
        assert result is None

    def test_invalid_values(self):
        """测试无效值"""
        invalid_values = ["maybe", "unknown", "2", "invalid"]
        for val in invalid_values:
            result = _str_to_bool(val)
            assert result is None, f"Expected None for '{val}', got {result}"

    def test_whitespace_handling(self):
        """测试空格处理"""
        assert _str_to_bool("  true  ") is True
        assert _str_to_bool("  false  ") is False
        assert _str_to_bool("   ") is False  # 空白字符串视为 False

    def test_mixed_case(self):
        """测试混合大小写"""
        assert _str_to_bool("TrUe") is True
        assert _str_to_bool("FaLsE") is False
        assert _str_to_bool("YeS") is True
        assert _str_to_bool("nO") is False


class TestGetEnv:
    """测试环境变量获取和类型转换"""

    def test_get_env_string_default(self):
        """测试获取不存在的字符串环境变量"""
        with patch.dict(os.environ, {}, clear=True):
            result = _get_env("NONEXISTENT_VAR", default="default_value")
            assert result == "default_value"

    def test_get_env_string_exists(self):
        """测试获取存在的字符串环境变量"""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            result = _get_env("TEST_VAR", default="default")
            assert result == "test_value"

    def test_get_env_empty_string_uses_default(self):
        """测试空字符串使用默认值"""
        with patch.dict(os.environ, {"TEST_VAR": ""}):
            result = _get_env("TEST_VAR", default="default_value")
            assert result == "default_value"

    def test_get_env_int_conversion(self):
        """测试整数类型转换"""
        with patch.dict(os.environ, {"TEST_INT": "42"}):
            result = _get_env("TEST_INT", default=0, cast=int)
            assert result == 42
            assert isinstance(result, int)

    def test_get_env_int_invalid(self):
        """测试无效整数使用默认值"""
        with patch.dict(os.environ, {"TEST_INT": "not_a_number"}):
            result = _get_env("TEST_INT", default=10, cast=int)
            assert result == 10

    def test_get_env_float_conversion(self):
        """测试浮点数类型转换"""
        with patch.dict(os.environ, {"TEST_FLOAT": "3.14"}):
            result = _get_env("TEST_FLOAT", default=0.0, cast=float)
            assert result == 3.14
            assert isinstance(result, float)

    def test_get_env_float_invalid(self):
        """测试无效浮点数使用默认值"""
        with patch.dict(os.environ, {"TEST_FLOAT": "not_a_float"}):
            result = _get_env("TEST_FLOAT", default=1.5, cast=float)
            assert result == 1.5

    def test_get_env_bool_true(self):
        """测试布尔值 True"""
        with patch.dict(os.environ, {"TEST_BOOL": "true"}):
            result = _get_env("TEST_BOOL", default=False, cast=bool)
            assert result is True

    def test_get_env_bool_false(self):
        """测试布尔值 False"""
        with patch.dict(os.environ, {"TEST_BOOL": "false"}):
            result = _get_env("TEST_BOOL", default=True, cast=bool)
            assert result is False

    def test_get_env_bool_invalid(self):
        """测试无效布尔值使用默认值"""
        with patch.dict(os.environ, {"TEST_BOOL": "invalid"}):
            result = _get_env("TEST_BOOL", default=True, cast=bool)
            assert result is True

    def test_get_env_path_conversion(self):
        """测试 Path 类型转换"""
        with patch.dict(os.environ, {"TEST_PATH": "/tmp/test"}):
            result = _get_env("TEST_PATH", default=Path("/default"), cast=Path)
            assert isinstance(result, Path)
            # 在 Windows 上路径分隔符会被转换
            assert "tmp" in str(result) and "test" in str(result)

    def test_get_env_path_default(self):
        """测试 Path 默认值"""
        with patch.dict(os.environ, {}, clear=True):
            result = _get_env("TEST_PATH", default=Path("/default"), cast=Path)
            assert isinstance(result, Path)
            # 在 Windows 上路径分隔符会被转换
            assert "default" in str(result)

    def test_get_env_none_default(self):
        """测试 None 作为默认值"""
        with patch.dict(os.environ, {}, clear=True):
            result = _get_env("TEST_VAR", default=None)
            assert result is None

    def test_get_env_with_validation_pass(self):
        """测试验证通过"""
        with patch.dict(os.environ, {"TEST_VAR": "5"}):
            result = _get_env(
                "TEST_VAR",
                default=0,
                cast=int,
                validate=lambda v: v > 0
            )
            assert result == 5

    def test_get_env_with_validation_fail(self):
        """测试验证失败"""
        with patch.dict(os.environ, {"TEST_VAR": "-5"}):
            with pytest.raises(ValueError) as exc_info:
                _get_env(
                    "TEST_VAR",
                    default=0,
                    cast=int,
                    validate=lambda v: v > 0
                )
            assert "Invalid value for TEST_VAR" in str(exc_info.value)

    def test_get_env_validation_none_value(self):
        """测试验证函数不应用于 None 值"""
        with patch.dict(os.environ, {}, clear=True):
            # 不应该抛出异常，因为 None 值不会被验证
            result = _get_env(
                "TEST_VAR",
                default=None,
                cast=int,
                validate=lambda v: v > 0
            )
            assert result is None

    def test_get_env_validation_with_default(self):
        """测试默认值的验证"""
        with patch.dict(os.environ, {}, clear=True):
            # 默认值也会被验证
            with pytest.raises(ValueError):
                _get_env(
                    "TEST_VAR",
                    default=-5,
                    cast=int,
                    validate=lambda v: v > 0
                )


class TestConfigVariables:
    """测试配置变量的加载"""

    def test_api_keys_loaded(self):
        """测试 API Keys 加载"""
        # conftest.py 已经设置了测试环境变量
        from src import config

        # 这些在测试环境中应该被设置
        assert config.DEEPSEEK_API_KEY is not None
        assert config.GEMINI_API_KEY is not None

    def test_directories_are_paths(self):
        """测试目录配置是 Path 对象"""
        from src import config

        assert isinstance(config.OUTPUT_DIR, Path)
        assert isinstance(config.DOWNLOAD_DIR, Path)
        assert isinstance(config.TEMP_DIR, Path)
        assert isinstance(config.LOG_DIR, Path)

    def test_log_level_is_uppercase(self):
        """测试日志级别被转为大写"""
        from src import config

        assert config.LOG_LEVEL == config.LOG_LEVEL.upper()
        assert config.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def test_boolean_flags(self):
        """测试布尔标志"""
        from src import config

        assert isinstance(config.ZIP_OUTPUT_ENABLED, bool)
        assert isinstance(config.USE_ONNX, bool)
        assert isinstance(config.ASYNC_FLAG, bool)
        assert isinstance(config.DISABLE_LLM_POLISH, bool)
        assert isinstance(config.DISABLE_LLM_SUMMARY, bool)

    def test_numeric_values(self):
        """测试数值配置"""
        from src import config

        assert isinstance(config.LLM_TEMPERATURE, float)
        assert isinstance(config.LLM_MAX_TOKENS, int)
        assert isinstance(config.LLM_TOP_P, float)
        assert isinstance(config.LLM_TOP_K, int)
        assert isinstance(config.SPLIT_LIMIT, int)

    def test_llm_temperature_range(self):
        """测试 LLM 温度范围"""
        from src import config

        assert 0.0 <= config.LLM_TEMPERATURE <= 2.0

    def test_llm_top_p_range(self):
        """测试 LLM top_p 范围"""
        from src import config

        assert 0.0 <= config.LLM_TOP_P <= 1.0

    def test_split_limit_positive(self):
        """测试分割限制为正数"""
        from src import config

        assert config.SPLIT_LIMIT > 0

    def test_llm_supported_list(self):
        """测试支持的 LLM 列表"""
        from src import config

        assert isinstance(config.LLM_SERVER_SUPPORTED, list)
        assert len(config.LLM_SERVER_SUPPORTED) > 0
        assert "deepseek-chat" in config.LLM_SERVER_SUPPORTED
        assert "gemini-2.0-flash" in config.LLM_SERVER_SUPPORTED

    def test_all_config_dict(self):
        """测试配置快照字典"""
        from src import config

        assert isinstance(config.ALL_CONFIG, dict)
        assert "LLM_SERVER" in config.ALL_CONFIG
        assert "OUTPUT_DIR" in config.ALL_CONFIG
        assert "LOG_LEVEL" in config.ALL_CONFIG


class TestConfigEdgeCases:
    """测试配置边界情况"""

    def test_model_dir_can_be_none(self):
        """测试 MODEL_DIR 可以为 None"""
        from src import config

        # MODEL_DIR 默认为 None
        # 在测试环境中可能被设置，但应该支持 None
        assert config.MODEL_DIR is None or isinstance(config.MODEL_DIR, Path)

    def test_log_file_fallback(self):
        """测试日志文件回退"""
        from src import config

        # LOG_FILE 应该有默认值
        assert isinstance(config.LOG_FILE, Path)

    def test_web_server_port_can_be_none(self):
        """测试 Web 服务器端口可以为 None"""
        from src import config

        # WEB_SERVER_PORT 可以为 None（使用默认端口）
        assert config.WEB_SERVER_PORT is None or isinstance(config.WEB_SERVER_PORT, int)

    @patch.dict(os.environ, {"LLM_TEMPERATURE": "5.0"})
    def test_temperature_validation_fail(self):
        """测试温度验证失败"""
        # 重新加载配置会触发验证
        # 由于配置在模块级别加载，这个测试需要特殊处理
        with pytest.raises(ValueError):
            _get_env(
                "LLM_TEMPERATURE",
                default=0.1,
                cast=float,
                validate=lambda v: 0.0 <= v <= 2.0
            )

    @patch.dict(os.environ, {"LLM_TOP_P": "1.5"})
    def test_top_p_validation_fail(self):
        """测试 top_p 验证失败"""
        with pytest.raises(ValueError):
            _get_env(
                "LLM_TOP_P",
                default=0.95,
                cast=float,
                validate=lambda v: 0.0 <= v <= 1.0
            )

    @patch.dict(os.environ, {"SPLIT_LIMIT": "0"})
    def test_split_limit_validation_fail(self):
        """测试分割限制验证失败"""
        with pytest.raises(ValueError):
            _get_env(
                "SPLIT_LIMIT",
                default=1000,
                cast=int,
                validate=lambda v: v > 0
            )


class TestConfigIntegration:
    """测试配置集成"""

    def test_directories_created(self):
        """测试目录被创建"""
        from src import config

        # 在测试环境中，这些目录应该被创建
        # conftest.py 设置了临时目录
        assert config.TEMP_DIR.exists() or not config.ENABLE_STRICT_VALIDATION
        assert config.OUTPUT_DIR.exists() or not config.ENABLE_STRICT_VALIDATION

    def test_config_snapshot_completeness(self):
        """测试配置快照完整性"""
        from src import config

        # 检查重要配置是否都在快照中
        important_keys = [
            "LLM_SERVER", "OUTPUT_DIR", "LOG_LEVEL",
            "ASR_MODEL", "DEVICE", "LLM_TEMPERATURE"
        ]

        for key in important_keys:
            assert key in config.ALL_CONFIG, f"{key} not in ALL_CONFIG"

    def test_config_values_consistent(self):
        """测试配置值一致性"""
        from src import config

        # 快照中的值应该与变量一致
        assert config.ALL_CONFIG["LLM_SERVER"] == config.LLM_SERVER
        assert config.ALL_CONFIG["LOG_LEVEL"] == config.LOG_LEVEL
        assert config.ALL_CONFIG["ASYNC_FLAG"] == config.ASYNC_FLAG


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
