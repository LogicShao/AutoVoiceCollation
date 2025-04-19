import configparser

config_file = '../config.ini'
config = configparser.ConfigParser()
config.read(config_file, encoding='utf-8')

try:
    DEEPSEEK_API = config['deepseek'].get('api_key')
except KeyError:
    raise KeyError("请在 config.ini 文件中配置 'deepseek' 部分的 'api_key'")

try:
    GEMINI_API = config['gemini'].get('api_key')
except KeyError:
    raise KeyError("请在 config.ini 文件中配置 'gemini' 部分的 'api_key'")

OUTPUT_DIR = '../out'
DOWNLOAD_DIR = '../download'

LLM_SERVER = 'gemini'
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 2048
