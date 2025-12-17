"""
配置管理模块（向后兼容层）

本模块提供与旧版本兼容的配置接口，同时内部使用新的 Pydantic 配置系统。

新代码建议使用：
    from src.utils.config import get_config
    config = get_config()
    config.llm.deepseek_api_key

旧代码兼容（本模块）：
    from src.config import DEEPSEEK_API_KEY
"""

import os
from pathlib import Path
from typing import Optional, Any

from dotenv import load_dotenv

# 加载 .env 文件
project_root = Path(__file__).resolve().parent.parent
dotenv_path = project_root / ".env"
if dotenv_path.exists():
    print("load dotenv on", dotenv_path)
    load_dotenv(dotenv_path)
else:
    print("dotenv not found on", dotenv_path)

# 导入新的配置系统
try:
    from src.utils.config import get_config

    _use_new_config = True
    _config = get_config()
except Exception as e:
    print(f"⚠️ 警告: 无法加载新配置系统，回退到旧实现: {e}")
    _use_new_config = False
    _config = None


# ---------- 辅助函数（保留用于回退） ----------
def _str_to_bool(s: Optional[str]) -> Optional[bool]:
    """字符串转布尔值"""
    if s is None:
        return None
    s2 = str(s).strip().lower()
    if s2 in ("1", "true", "yes", "on"):
        return True
    if s2 in ("0", "false", "no", "off", ""):
        return False
    return None


def _get_env(key: str, default: Any = None, cast: type = str, validate=None):
    """从环境变量获取配置（回退函数）"""
    raw = os.getenv(key, None)
    if raw is None:
        val = default
    else:
        # treat empty string as missing -> fallback to default
        if raw == "":
            val = default
        else:
            try:
                if cast is bool:
                    val = _str_to_bool(raw)
                    if val is None:
                        raise ValueError()
                elif cast is Path:
                    val = Path(raw)
                else:
                    val = cast(raw)
            except Exception:
                val = default
    if validate and val is not None and not validate(val):
        raise ValueError(f"Invalid value for {key}: {val}")
    return val


# ---------- 配置导出（向后兼容） ----------
if _use_new_config and _config:
    # 使用新配置系统
    DEEPSEEK_API_KEY = _config.llm.deepseek_api_key
    GEMINI_API_KEY = _config.llm.gemini_api_key
    DASHSCOPE_API_KEY = _config.llm.dashscope_api_key
    CEREBRAS_API_KEY = _config.llm.cerebras_api_key

    OUTPUT_DIR = _config.paths.output_dir
    DOWNLOAD_DIR = _config.paths.download_dir
    TEMP_DIR = _config.paths.temp_dir
    MODEL_DIR = _config.paths.model_dir
    LOG_DIR = _config.paths.log_dir

    LOG_LEVEL = _config.logging.log_level
    LOG_FILE = (
        _config.logging.log_file
        if _config.logging.log_file
        else (LOG_DIR / "AutoVoiceCollation.log")
    )
    LOG_CONSOLE_OUTPUT = _config.logging.log_console_output
    LOG_COLORED_OUTPUT = _config.logging.log_colored_output
    THIRD_PARTY_LOG_LEVEL = _config.logging.third_party_log_level

    ASR_MODEL = _config.asr.asr_model
    OUTPUT_STYLE = _config.output_style
    ZIP_OUTPUT_ENABLED = _config.zip_output_enabled

    DEVICE = _config.asr.device
    USE_ONNX = _config.asr.use_onnx
    ONNX_PROVIDERS = _config.asr.onnx_providers

    LLM_SERVER = _config.llm.llm_server
    LLM_TEMPERATURE = _config.llm.llm_temperature
    LLM_MAX_TOKENS = _config.llm.llm_max_tokens
    LLM_TOP_P = _config.llm.llm_top_p
    LLM_TOP_K = _config.llm.llm_top_k
    SPLIT_LIMIT = _config.llm.split_limit
    ASYNC_FLAG = _config.llm.async_flag
    LLM_SERVER_SUPPORTED = _config.llm.llm_server_supported

    SUMMARY_LLM_SERVER = _config.llm.summary_llm_server
    SUMMARY_LLM_TEMPERATURE = _config.llm.summary_llm_temperature
    SUMMARY_LLM_MAX_TOKENS = _config.llm.summary_llm_max_tokens

    DISABLE_LLM_POLISH = _config.llm.disable_llm_polish
    DISABLE_LLM_SUMMARY = _config.llm.disable_llm_summary
    LOCAL_LLM_ENABLED = _config.llm.local_llm_enabled
    DEBUG_FLAG = _config.debug_flag
    ENABLE_STRICT_VALIDATION = _config.enable_strict_validation

    WEB_SERVER_PORT = _config.web_server_port
    CACHE_TTL_SECONDS = _config.cache_ttl_seconds

    # 导出配置快照
    ALL_CONFIG = _config.to_legacy_dict()

else:
    # 回退到旧实现
    print("⚠️ 使用旧配置系统")

    DEEPSEEK_API_KEY = _get_env("DEEPSEEK_API_KEY", default=None, cast=str)
    GEMINI_API_KEY = _get_env("GEMINI_API_KEY", default=None, cast=str)
    DASHSCOPE_API_KEY = _get_env("DASHSCOPE_API_KEY", default=None, cast=str)
    CEREBRAS_API_KEY = _get_env("CEREBRAS_API_KEY", default=None, cast=str)

    OUTPUT_DIR = _get_env("OUTPUT_DIR", default=str(project_root / "out"), cast=Path)
    DOWNLOAD_DIR = _get_env(
        "DOWNLOAD_DIR", default=str(project_root / "download"), cast=Path
    )
    TEMP_DIR = _get_env("TEMP_DIR", default=str(project_root / "temp"), cast=Path)
    MODEL_DIR = _get_env("MODEL_DIR", default=None, cast=Path)
    LOG_DIR = _get_env("LOG_DIR", default=project_root / "logs", cast=Path)

    LOG_LEVEL = _get_env("LOG_LEVEL", default="INFO", cast=str).upper()
    LOG_FILE_RAW = _get_env("LOG_FILE", default="", cast=str)
    LOG_FILE = (
        Path(LOG_FILE_RAW) if LOG_FILE_RAW else (LOG_DIR / "AutoVoiceCollation.log")
    )
    LOG_CONSOLE_OUTPUT = _get_env("LOG_CONSOLE_OUTPUT", default=True, cast=bool)
    LOG_COLORED_OUTPUT = _get_env("LOG_COLORED_OUTPUT", default=True, cast=bool)
    THIRD_PARTY_LOG_LEVEL = _get_env(
        "THIRD_PARTY_LOG_LEVEL", default="ERROR", cast=str
    ).upper()

    ASR_MODEL = _get_env("ASR_MODEL", default="paraformer", cast=str)
    OUTPUT_STYLE = _get_env("OUTPUT_STYLE", default="pdf only", cast=str)
    ZIP_OUTPUT_ENABLED = _get_env("ZIP_OUTPUT_ENABLED", default=False, cast=bool)

    DEVICE = _get_env("DEVICE", default="auto", cast=str)
    USE_ONNX = _get_env("USE_ONNX", default=False, cast=bool)
    ONNX_PROVIDERS = _get_env("ONNX_PROVIDERS", default="", cast=str)

    LLM_SERVER = _get_env(
        "LLM_SERVER", default="Cerebras:Qwen-3-235B-Instruct", cast=str
    )
    LLM_TEMPERATURE = _get_env(
        "LLM_TEMPERATURE", default=0.1, cast=float, validate=lambda v: 0.0 <= v <= 2.0
    )
    LLM_MAX_TOKENS = _get_env(
        "LLM_MAX_TOKENS", default=6000, cast=int, validate=lambda v: v >= 0
    )
    LLM_TOP_P = _get_env(
        "LLM_TOP_P", default=0.95, cast=float, validate=lambda v: 0.0 <= v <= 1.0
    )
    LLM_TOP_K = _get_env("LLM_TOP_K", default=64, cast=int, validate=lambda v: v >= 0)
    SPLIT_LIMIT = _get_env(
        "SPLIT_LIMIT", default=1000, cast=int, validate=lambda v: v > 0
    )
    ASYNC_FLAG = _get_env("ASYNC_FLAG", default=True, cast=bool)
    LLM_SERVER_SUPPORTED = [
        "qwen3-plus",
        "qwen3-max",
        "deepseek-chat",
        "deepseek-reasoner",
        "Cerebras:Qwen-3-32B",
        "Cerebras:Qwen-3-235B-Instruct",
        "Cerebras:Qwen-3-235B-Thinking",
        "gemini-2.0-flash",
        "local:Qwen/Qwen2.5-1.5B-Instruct",
    ]

    SUMMARY_LLM_SERVER = _get_env(
        "SUMMARY_LLM_SERVER", default="Cerebras:Qwen-3-235B-Thinking", cast=str
    )
    SUMMARY_LLM_TEMPERATURE = _get_env(
        "SUMMARY_LLM_TEMPERATURE",
        default=1.0,
        cast=float,
        validate=lambda v: 0.0 <= v <= 2.0,
    )
    SUMMARY_LLM_MAX_TOKENS = _get_env(
        "SUMMARY_LLM_MAX_TOKENS", default=8192, cast=int, validate=lambda v: v >= 0
    )

    DISABLE_LLM_POLISH = _get_env("DISABLE_LLM_POLISH", default=False, cast=bool)
    DISABLE_LLM_SUMMARY = _get_env("DISABLE_LLM_SUMMARY", default=False, cast=bool)
    LOCAL_LLM_ENABLED = _get_env("LOCAL_LLM_ENABLED", default=False, cast=bool)
    DEBUG_FLAG = _get_env("DEBUG_FLAG", default=False, cast=bool)
    ENABLE_STRICT_VALIDATION = _get_env(
        "ENABLE_STRICT_VALIDATION", default=False, cast=bool
    )

    WEB_SERVER_PORT = _get_env("WEB_SERVER_PORT", default=None, cast=int)
    CACHE_TTL_SECONDS = _get_env(
        "CACHE_TTL_SECONDS", default=3600, cast=int, validate=lambda v: v >= 0
    )

    # ---------- 目录创建与校验 ----------
    def _ensure_dir(p: Optional[Path]):
        if p is None:
            return
        try:
            p = p.resolve()
            if not p.exists():
                p.mkdir(parents=True, exist_ok=True)
        except Exception:
            if ENABLE_STRICT_VALIDATION:
                raise

    _ensure_dir(OUTPUT_DIR)
    _ensure_dir(DOWNLOAD_DIR)
    _ensure_dir(TEMP_DIR)
    if MODEL_DIR:
        _ensure_dir(MODEL_DIR)
    _ensure_dir(LOG_DIR)
    _ensure_dir(LOG_FILE.parent)

    # 导出配置快照
    ALL_CONFIG = {
        "DEEPSEEK_API_KEY": DEEPSEEK_API_KEY,
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "DASHSCOPE_API_KEY": DASHSCOPE_API_KEY,
        "CEREBRAS_API_KEY": CEREBRAS_API_KEY,
        "OUTPUT_DIR": str(OUTPUT_DIR),
        "DOWNLOAD_DIR": str(DOWNLOAD_DIR),
        "TEMP_DIR": str(TEMP_DIR),
        "MODEL_DIR": str(MODEL_DIR) if MODEL_DIR else None,
        "LOG_DIR": str(LOG_DIR),
        "LOG_FILE": str(LOG_FILE),
        "LOG_LEVEL": LOG_LEVEL,
        "LOG_CONSOLE_OUTPUT": LOG_CONSOLE_OUTPUT,
        "LOG_COLORED_OUTPUT": LOG_COLORED_OUTPUT,
        "THIRD_PARTY_LOG_LEVEL": THIRD_PARTY_LOG_LEVEL,
        "ASR_MODEL": ASR_MODEL,
        "OUTPUT_STYLE": OUTPUT_STYLE,
        "ZIP_OUTPUT_ENABLED": ZIP_OUTPUT_ENABLED,
        "DEVICE": DEVICE,
        "USE_ONNX": USE_ONNX,
        "ONNX_PROVIDERS": ONNX_PROVIDERS,
        "LLM_SERVER": LLM_SERVER,
        "LLM_TEMPERATURE": LLM_TEMPERATURE,
        "LLM_MAX_TOKENS": LLM_MAX_TOKENS,
        "LLM_TOP_P": LLM_TOP_P,
        "LLM_TOP_K": LLM_TOP_K,
        "SPLIT_LIMIT": SPLIT_LIMIT,
        "ASYNC_FLAG": ASYNC_FLAG,
        "SUMMARY_LLM_SERVER": SUMMARY_LLM_SERVER,
        "SUMMARY_LLM_TEMPERATURE": SUMMARY_LLM_TEMPERATURE,
        "SUMMARY_LLM_MAX_TOKENS": SUMMARY_LLM_MAX_TOKENS,
        "DISABLE_LLM_POLISH": DISABLE_LLM_POLISH,
        "DISABLE_LLM_SUMMARY": DISABLE_LLM_SUMMARY,
        "LOCAL_LLM_ENABLED": LOCAL_LLM_ENABLED,
        "DEBUG_FLAG": DEBUG_FLAG,
        "WEB_SERVER_PORT": WEB_SERVER_PORT,
        "CACHE_TTL_SECONDS": CACHE_TTL_SECONDS,
    }
