OUTPUT_DIR = './out'
DOWNLOAD_DIR = './download'

OUTPUT_STYLE = 'pdf only'
OUTPUT_STYLE_SUPPORTED = ['pdf with img', 'img only', 'text only', 'pdf only']

DISABLE_LLM_POLISH = False  # 是否禁用 LLM 润色
LLM_SERVER = 'gemini'
LLM_SERVER_SUPPORTED = ['gemini', 'deepseek']
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 6000
SPLIT_LIMIT = 4000  # 每段文本的最大字符数

PROJECT_NAME = 'AutoVoiceCollation'
DEBUG_FLAG = True  # 是否开启调试模式
LOAD_TEXT_FROM_LOCAL = True  # 是否从本地加载文本

assert LLM_SERVER in LLM_SERVER_SUPPORTED
assert OUTPUT_STYLE in OUTPUT_STYLE_SUPPORTED
