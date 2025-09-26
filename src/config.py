import os
from typing import Optional

PROJECT_NAME = 'AutoVoiceCollation'
DEBUG_FLAG = False

OUTPUT_DIR = './out'  # 输出目录
DOWNLOAD_DIR = './download'  # 音频下载目录
TEMP_DIR = './temp'

OUTPUT_STYLE = 'pdf only'
OUTPUT_STYLE_SUPPORTED = ['pdf with img', 'img only', 'text only', 'pdf only']

ASR_MODEL = 'paraformer'  # ASR 模型
ASR_MODEL_SUPPORTED = ['sense_voice', 'paraformer']

DISABLE_LLM_POLISH = False  # 是否禁用 LLM 润色
DISABLE_LLM_SUMMARY = False  # 是否禁用 LLM 摘要
LLM_SERVER = 'deepseek'
LLM_SERVER_SUPPORTED = ['gemini', 'qwen3', 'deepseek-chat', 'deepseek-reasoner', 'qwen3-max', 'qwen3-plus', 'deepseek']
LOCAL_LLM_ENABLED = True  # 是否启用本地 LLM
LOCAL_LLM_SERVER_SUPPORTED = ['local:Qwen/Qwen2.5-1.5B-Instruct']
LLM_TEMPERATURE = 0.1
LLM_MAX_TOKENS = 6000
LLM_TOP_P = 0.95
LLM_TOP_K = 64
SPLIT_LIMIT = 1000  # 每段文本的最大字符数
ASYNC_FLAG = True  # 是否使用异步处理
if LOCAL_LLM_ENABLED:
    LLM_SERVER_SUPPORTED.extend(LOCAL_LLM_SERVER_SUPPORTED)

SUMMARY_LLM_TEMPERATURE = 1
SUMMARY_LLM_MAX_TOKENS = 8192
SUMMARY_LLM_SERVER = 'deepseek-reasoner'

WEB_SEVER_PORT: Optional[int] = None

assert LLM_SERVER in LLM_SERVER_SUPPORTED
assert OUTPUT_STYLE in OUTPUT_STYLE_SUPPORTED
assert SUMMARY_LLM_SERVER in LLM_SERVER_SUPPORTED
assert ASR_MODEL in ASR_MODEL_SUPPORTED

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
