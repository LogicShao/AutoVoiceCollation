import os

from dotenv import load_dotenv

from .scripts import display_api_key


def load_api_keys():
    """
    从环境变量中加载 API 密钥，并显示部分内容。
    :return: None
    """
    # 加载 .env 文件中的环境变量
    if os.path.exists('.env'):
        load_dotenv('.env')
        print('检测到 .env 文件，已加载环境变量。')
    else:
        print('未检测到 .env 文件，从系统环境变量加载。')

    try:
        _deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        _gemini_api_key = os.getenv('GEMINI_API_KEY')
        print('检测到deepseek api密钥:', display_api_key(_deepseek_api_key))
        print('检测到gemini api密钥:', display_api_key(_gemini_api_key))
    except Exception as e:
        print(f"读取环境变量时发生错误: {e}")
