import os
from pathlib import Path
from typing import Optional, Any

from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent
dotenv_path = project_root / ".env"
if dotenv_path.exists():
    print("load dotenv on", dotenv_path)
    load_dotenv(dotenv_path)
else:
    print("dotenv not found on", dotenv_path)


def _str_to_bool(s: Optional[str]) -> Optional[bool]:
    if s is None:
        return None
    s2 = str(s).strip().lower()
    if s2 in ("1", "true", "yes", "on"):
        return True
    if s2 in ("0", "false", "no", "off", ""):
        return False
    return None


def _get_env(key: str, default: Any = None, cast: type = str, validate=None):
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


# ---------- 目录与 API Keys ----------
DEEPSEEK_API_KEY = _get_env("DEEPSEEK_API_KEY", default=None, cast=str)
GEMINI_API_KEY = _get_env("GEMINI_API_KEY", default=None, cast=str)
DASHSCOPE_API_KEY = _get_env("DASHSCOPE_API_KEY", default=None, cast=str)
CEREBRAS_API_KEY = _get_env("CEREBRAS_API_KEY", default=None, cast=str)

OUTPUT_DIR = _get_env("OUTPUT_DIR", default=str(project_root / "out"), cast=Path)
DOWNLOAD_DIR = _get_env("DOWNLOAD_DIR", default=str(project_root / "download"), cast=Path)
TEMP_DIR = _get_env("TEMP_DIR", default=str(project_root / "temp"), cast=Path)
MODEL_DIR = _get_env("MODEL_DIR", default=None, cast=Path)  # None 表示使用依赖库默认缓存
LOG_DIR = _get_env("LOG_DIR", default=project_root / "logs", cast=Path)

# ---------- 日志 ----------
LOG_LEVEL = _get_env("LOG_LEVEL", default="INFO", cast=str).upper()
LOG_FILE_RAW = _get_env("LOG_FILE", default="", cast=str)
LOG_FILE = Path(LOG_FILE_RAW) if LOG_FILE_RAW else (LOG_DIR / "AutoVoiceCollation.log")
LOG_CONSOLE_OUTPUT = _get_env("LOG_CONSOLE_OUTPUT", default=True, cast=bool)
LOG_COLORED_OUTPUT = _get_env("LOG_COLORED_OUTPUT", default=True, cast=bool)
THIRD_PARTY_LOG_LEVEL = _get_env("THIRD_PARTY_LOG_LEVEL", default="ERROR", cast=str).upper()

# ---------- ASR / 输出样式 ----------
ASR_MODEL = _get_env("ASR_MODEL", default="paraformer", cast=str)
OUTPUT_STYLE = _get_env("OUTPUT_STYLE", default="pdf only", cast=str)
ZIP_OUTPUT_ENABLED = _get_env("ZIP_OUTPUT_ENABLED", default=False, cast=bool)

# ---------- 设备与推理配置 ----------
# 设备选择：auto, cpu, cuda, cuda:0, cuda:1 等
# auto 表示自动检测，优先使用 GPU
DEVICE = _get_env("DEVICE", default="auto", cast=str)

# 是否使用 ONNX 推理：true 或 false
USE_ONNX = _get_env("USE_ONNX", default=False, cast=bool)

# ONNX 推理提供者优先级（逗号分隔）
# 可选：CUDAExecutionProvider, CPUExecutionProvider, TensorrtExecutionProvider 等
ONNX_PROVIDERS = _get_env("ONNX_PROVIDERS", default="", cast=str)

# ---------- LLM ----------
LLM_SERVER = _get_env("LLM_SERVER", default="Cerebras:Qwen-3-235B-Instruct", cast=str)
LLM_TEMPERATURE = _get_env("LLM_TEMPERATURE", default=0.1, cast=float, validate=lambda v: 0.0 <= v <= 2.0)
LLM_MAX_TOKENS = _get_env("LLM_MAX_TOKENS", default=6000, cast=int, validate=lambda v: v >= 0)
LLM_TOP_P = _get_env("LLM_TOP_P", default=0.95, cast=float, validate=lambda v: 0.0 <= v <= 1.0)
LLM_TOP_K = _get_env("LLM_TOP_K", default=64, cast=int, validate=lambda v: v >= 0)
SPLIT_LIMIT = _get_env("SPLIT_LIMIT", default=1000, cast=int, validate=lambda v: v > 0)
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

# ---------- 摘要 ----------
SUMMARY_LLM_SERVER = _get_env("SUMMARY_LLM_SERVER", default="Cerebras:Qwen-3-235B-Thinking", cast=str)
SUMMARY_LLM_TEMPERATURE = _get_env("SUMMARY_LLM_TEMPERATURE", default=1.0, cast=float,
                                   validate=lambda v: 0.0 <= v <= 2.0)
SUMMARY_LLM_MAX_TOKENS = _get_env("SUMMARY_LLM_MAX_TOKENS", default=8192, cast=int, validate=lambda v: v >= 0)

# ---------- 功能开关 ----------
DISABLE_LLM_POLISH = _get_env("DISABLE_LLM_POLISH", default=False, cast=bool)
DISABLE_LLM_SUMMARY = _get_env("DISABLE_LLM_SUMMARY", default=False, cast=bool)
LOCAL_LLM_ENABLED = _get_env("LOCAL_LLM_ENABLED", default=False, cast=bool)
DEBUG_FLAG = _get_env("DEBUG_FLAG", default=False, cast=bool)
ENABLE_STRICT_VALIDATION = _get_env("ENABLE_STRICT_VALIDATION", default=False, cast=bool)

# ---------- 其它 ----------
WEB_SERVER_PORT = _get_env("WEB_SERVER_PORT", default=None, cast=int)
CACHE_TTL_SECONDS = _get_env("CACHE_TTL_SECONDS", default=3600, cast=int, validate=lambda v: v >= 0)


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


# 优先创建 OUTPUT/DOWNLOAD/TEMP/LOG 目录（非严格模式下忽略错误）
_ensure_dir(OUTPUT_DIR)
_ensure_dir(DOWNLOAD_DIR)
_ensure_dir(TEMP_DIR)
if MODEL_DIR:
    _ensure_dir(MODEL_DIR)
_ensure_dir(LOG_DIR)
_ensure_dir(LOG_FILE.parent)

# ---------- 导出配置快照 ----------
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
