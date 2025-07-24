import os

from dotenv import load_dotenv


def display_api_key(api_key: str, front_display_num: int = 6, back_display_num: int = 4) -> str:
    """
    显示 API 密钥的部分内容，前后各显示指定数量的字符。
    :param api_key: API 密钥
    :param front_display_num: 前面显示的字符数
    :param back_display_num: 后面显示的字符数
    :return: 显示的 API 密钥
    """
    if len(api_key) <= front_display_num + back_display_num:
        return '*' * (len(api_key))  # 如果密钥长度小于等于前后显示字符数之和，则全部隐藏
    else:
        return api_key[:front_display_num] + '*' * (len(api_key) - front_display_num -
                                                    back_display_num) + api_key[-back_display_num:]


def load_api_keys(dotenv_file: str = '.env'):
    """
    从环境变量中加载 API 密钥，并显示部分内容。
    :return: None
    """
    # 加载 .env 文件中的环境变量
    if os.path.exists(dotenv_file):
        load_dotenv(dotenv_file)
        print('检测到 dotenv 文件 {}，已加载环境变量。'.format(dotenv_file))
    else:
        print('未检测到 dotenv 文件，直接从系统环境变量加载。')

    try:
        _deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        _gemini_api_key = os.getenv('GEMINI_API_KEY')
        _dashscope_api_key = os.getenv('DASHSCOPE_API_KEY')
        print('检测到 deepseek api 密钥:', display_api_key(_deepseek_api_key))
        print('检测到 gemini api 密钥:', display_api_key(_gemini_api_key))
        print('检测到 dashscope api 密钥:', display_api_key(_dashscope_api_key))
    except Exception as e:
        print(f"读取环境变量时发生错误: {e}")
        print("请确保 .env 文件中包含 DEEPSEEK_API_KEY, GEMINI_API_KEY 和 DASHSCOPE_API_KEY 变量，")
        print("或者直接在系统环境变量中设置这些变量。")
