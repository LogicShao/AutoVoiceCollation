import os

PROJECT_NAME = 'AutoVoiceCollation'
DEBUG_FLAG = True  # 是否开启调试模式

OUTPUT_DIR = './out'  # 输出目录
DOWNLOAD_DIR = './download'  # 音频下载目录

OUTPUT_STYLE = 'pdf only'
OUTPUT_STYLE_SUPPORTED = ['pdf with img', 'img only', 'text only', 'pdf only']

DISABLE_LLM_POLISH = False  # 是否禁用 LLM 润色
DISABLE_LLM_SUMMARY = False  # 是否禁用 LLM 摘要
LLM_SERVER = 'gemini'
LLM_SERVER_SUPPORTED = ['gemini', 'deepseek']
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 6000
SPLIT_LIMIT = 1000  # 每段文本的最大字符数

assert LLM_SERVER in LLM_SERVER_SUPPORTED
assert OUTPUT_STYLE in OUTPUT_STYLE_SUPPORTED

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
