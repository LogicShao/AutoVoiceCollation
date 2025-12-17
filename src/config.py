"""
配置管理模块 - 已废弃

⚠️ 警告：此模块已废弃，请使用新的配置系统。

新的配置系统基于 Pydantic v2，提供类型安全和自动验证功能。

## 迁移指南

### 旧的用法（已废弃）：
```python
from src.config import OUTPUT_DIR, ASR_MODEL, LLM_SERVER

print(OUTPUT_DIR)
print(ASR_MODEL)
```

### 新的用法：
```python
from src.utils.config import get_config

config = get_config()
print(config.paths.output_dir)    # Path 对象
print(config.asr.asr_model)       # 字符串
print(config.llm.llm_server)      # 字符串
```

## 配置访问映射

**路径配置 (config.paths.*)**:
- OUTPUT_DIR → config.paths.output_dir (Path)
- DOWNLOAD_DIR → config.paths.download_dir (Path)
- TEMP_DIR → config.paths.temp_dir (Path)
- LOG_DIR → config.paths.log_dir (Path)
- MODEL_DIR → config.paths.model_dir (Optional[Path])

**ASR 配置 (config.asr.*)**:
- ASR_MODEL → config.asr.asr_model
- DEVICE → config.asr.device
- USE_ONNX → config.asr.use_onnx
- ONNX_PROVIDERS → config.asr.get_onnx_providers_list()

**LLM 配置 (config.llm.*)**:
- LLM_SERVER → config.llm.llm_server
- LLM_SERVER_SUPPORTED → config.llm.llm_server_supported
- LLM_TEMPERATURE → config.llm.llm_temperature
- LLM_MAX_TOKENS → config.llm.llm_max_tokens
- LLM_TOP_P → config.llm.llm_top_p
- LLM_TOP_K → config.llm.llm_top_k
- SPLIT_LIMIT → config.llm.split_limit
- ASYNC_FLAG → config.llm.async_flag
- DISABLE_LLM_POLISH → config.llm.disable_llm_polish
- DISABLE_LLM_SUMMARY → config.llm.disable_llm_summary
- LOCAL_LLM_ENABLED → config.llm.local_llm_enabled

**应用配置 (config.*)**:
- OUTPUT_STYLE → config.output_style
- ZIP_OUTPUT_ENABLED → config.zip_output_enabled
- TEXT_ONLY_DEFAULT → config.text_only_default
- WEB_SERVER_PORT → config.web_server_port
- CACHE_TTL_SECONDS → config.cache_ttl_seconds
- DEBUG_FLAG → config.debug_flag
- ENABLE_STRICT_VALIDATION → config.enable_strict_validation

**日志配置 (config.logging.*)**:
- LOG_LEVEL → config.logging.log_level
- LOG_FILE → config.logging.log_file (Path)
- LOG_CONSOLE_OUTPUT → config.logging.log_console_output
- LOG_COLORED_OUTPUT → config.logging.log_colored_output

## 新配置系统的优势

1. **类型安全**：基于 Pydantic 的类型提示和自动验证
2. **结构化**：配置按功能模块组织（paths, llm, asr, logging）
3. **自动验证**：配置值在加载时自动验证，避免运行时错误
4. **更好的 IDE 支持**：完整的类型提示和自动补全

## 相关文档

- 配置系统架构：src/utils/config/
- 开发文档：docs/DEVELOPER_GUIDE.md
- 配置示例：.env.example
"""

# 为了向后兼容，仍然导出 get_config
# 但不再提供旧的配置变量
from src.utils.config import get_config

__all__ = ["get_config"]

# 如果有代码仍在尝试导入旧的配置变量，会收到友好的错误提示
def __getattr__(name):
    """拦截对旧配置变量的访问，提供迁移指导"""
    # 配置映射表
    migration_guide = {
        # 路径配置
        "OUTPUT_DIR": "config.paths.output_dir",
        "DOWNLOAD_DIR": "config.paths.download_dir",
        "TEMP_DIR": "config.paths.temp_dir",
        "LOG_DIR": "config.paths.log_dir",
        "MODEL_DIR": "config.paths.model_dir",
        # ASR 配置
        "ASR_MODEL": "config.asr.asr_model",
        "DEVICE": "config.asr.device",
        "USE_ONNX": "config.asr.use_onnx",
        "ONNX_PROVIDERS": "config.asr.get_onnx_providers_list()",
        # LLM 配置
        "LLM_SERVER": "config.llm.llm_server",
        "LLM_SERVER_SUPPORTED": "config.llm.llm_server_supported",
        "LLM_TEMPERATURE": "config.llm.llm_temperature",
        "LLM_MAX_TOKENS": "config.llm.llm_max_tokens",
        "LLM_TOP_P": "config.llm.llm_top_p",
        "LLM_TOP_K": "config.llm.llm_top_k",
        "SPLIT_LIMIT": "config.llm.split_limit",
        "ASYNC_FLAG": "config.llm.async_flag",
        "DISABLE_LLM_POLISH": "config.llm.disable_llm_polish",
        "DISABLE_LLM_SUMMARY": "config.llm.disable_llm_summary",
        "LOCAL_LLM_ENABLED": "config.llm.local_llm_enabled",
        # 摘要配置
        "SUMMARY_LLM_SERVER": "config.llm.summary_llm_server",
        "SUMMARY_LLM_TEMPERATURE": "config.llm.summary_llm_temperature",
        "SUMMARY_LLM_MAX_TOKENS": "config.llm.summary_llm_max_tokens",
        # 应用配置
        "OUTPUT_STYLE": "config.output_style",
        "ZIP_OUTPUT_ENABLED": "config.zip_output_enabled",
        "TEXT_ONLY_DEFAULT": "config.text_only_default",
        "WEB_SERVER_PORT": "config.web_server_port",
        "DEBUG_FLAG": "config.debug_flag",
        # 日志配置
        "LOG_LEVEL": "config.logging.log_level",
        "LOG_FILE": "config.logging.log_file",
        "LOG_CONSOLE_OUTPUT": "config.logging.log_console_output",
        "LOG_COLORED_OUTPUT": "config.logging.log_colored_output",
        "THIRD_PARTY_LOG_LEVEL": "config.logging.third_party_log_level",
    }

    if name in migration_guide:
        new_path = migration_guide[name]
        raise AttributeError(
            f"\n{'='*70}\n"
            f"配置变量 '{name}' 已废弃！\n\n"
            f"旧的用法:\n"
            f"  from src.config import {name}\n"
            f"  value = {name}\n\n"
            f"新的用法:\n"
            f"  from src.utils.config import get_config\n"
            f"  config = get_config()\n"
            f"  value = {new_path}\n\n"
            f"详细迁移指南请查看: src/config.py 文档\n"
            f"{'='*70}"
        )

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
