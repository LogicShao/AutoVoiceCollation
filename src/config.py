import configparser

config_file = '../config.ini'
config = configparser.ConfigParser()
config.read(config_file, encoding='utf-8')


def display_api_key(api_key: str, front_display_num: int = 6, back_display_num: int = 4) -> str:
    """
    显示 API 密钥的部分内容，前后各显示指定数量的字符。
    :param api_key: API 密钥
    :param front_display_num: 前面显示的字符数
    :param back_display_num: 后面显示的字符数
    :return: 显示的 API 密钥
    """
    if len(api_key) <= front_display_num + back_display_num:
        return api_key
    else:
        return api_key[:front_display_num] + '*' * (len(api_key) - front_display_num -
                                                    back_display_num) + api_key[-back_display_num:]


try:
    DEEPSEEK_API = config['deepseek'].get('api_key')
    print("检测到 DeepSeek API 密钥：", display_api_key(DEEPSEEK_API))
except KeyError:
    raise KeyError("请在 config.ini 文件中配置 'deepseek' 部分的 'api_key'")

try:
    GEMINI_API = config['gemini'].get('api_key')
    print("检测到 Gemini API 密钥：", display_api_key(GEMINI_API))
except KeyError:
    raise KeyError("请在 config.ini 文件中配置 'gemini' 部分的 'api_key'")

OUTPUT_DIR = '../out'
DOWNLOAD_DIR = '../download'

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
