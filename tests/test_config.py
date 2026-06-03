"""当前 Pydantic 配置系统测试。"""

from pathlib import Path

import pytest

from src.utils.config import AppConfig, ASRConfig, LLMConfig, PathConfig


def test_output_style_validation_rejects_unknown_style():
    with pytest.raises(ValueError, match="无效的输出样式"):
        AppConfig(output_style="unknown")


def test_path_config_resolves_project_relative_paths():
    config = PathConfig(output_dir="out")

    assert isinstance(config.output_dir, Path)
    assert config.output_dir.is_absolute()
    assert config.output_dir.name == "out"


def test_asr_model_normalized_and_validated():
    config = ASRConfig(asr_model="SENSE_VOICE")

    assert config.asr_model == "sense_voice"

    with pytest.raises(ValueError, match="不支持的 ASR 模型"):
        ASRConfig(asr_model="bad_asr")


def test_llm_numeric_fields_validate_ranges():
    with pytest.raises(ValueError):
        LLMConfig(llm_temperature=3.0)

    with pytest.raises(ValueError):
        LLMConfig(llm_max_tokens=0)
