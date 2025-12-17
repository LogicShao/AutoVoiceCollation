import os
from typing import Optional

from src.utils.logging.logger import get_logger

logger = get_logger(__name__)


def display_api_key(
    api_key: Optional[str], front_display_num: int = 6, back_display_num: int = 4
) -> str:
    """
    显示 API 密钥的部分内容，前后各显示指定数量的字符。
    :param api_key: API 密钥
    :param front_display_num: 前面显示的字符数
    :param back_display_num: 后面显示的字符数
    :return: 显示的 API 密钥
    """
    if api_key is None:
        return "未设置"
    if len(api_key) <= front_display_num + back_display_num:
        return "*" * len(api_key)  # 如果密钥长度小于等于前后显示字符数之和，则全部隐藏
    else:
        return (
            api_key[:front_display_num]
            + "*" * (len(api_key) - front_display_num - back_display_num)
            + api_key[-back_display_num:]
        )


def check_api_keys(debug: bool = False):
    """
    从环境变量中加载 API 密钥，并显示部分内容。
    :param debug: 是否显示API密钥详情（默认False，生产环境不应开启）
    :return: None
    """
    # 读取API密钥
    _deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    _gemini_api_key = os.getenv("GEMINI_API_KEY")
    _dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
    _cerebras_api_key = os.getenv("CEREBRAS_API_KEY")

    # 验证至少有一个API密钥被设置
    if not any(
        [_deepseek_api_key, _gemini_api_key, _dashscope_api_key, _cerebras_api_key]
    ):
        logger.warning("未检测到任何 API 密钥！")
        logger.warning("请在 .env 文件或系统环境变量中设置以下至少一个变量：")
        logger.warning("  - DEEPSEEK_API_KEY")
        logger.warning("  - GEMINI_API_KEY")
        logger.warning("  - DASHSCOPE_API_KEY")
        logger.warning("  - CEREBRAS_API_KEY")
        return

    # 仅在 debug 模式下显示密钥详情
    if debug:
        logger.info("API 密钥加载状态（DEBUG模式）:")
        logger.info(f"  deepseek api 密钥: {display_api_key(_deepseek_api_key)}")
        logger.info(f"  gemini api 密钥: {display_api_key(_gemini_api_key)}")
        logger.info(f"  dashscope api 密钥: {display_api_key(_dashscope_api_key)}")
        logger.info(f"  cerebras api 密钥: {display_api_key(_cerebras_api_key)}")
    else:
        # 生产模式只显示是否已设置
        logger.info("API 密钥加载状态:")
        logger.info(f"  deepseek:   {'[已设置]' if _deepseek_api_key else '[未设置]'}")
        logger.info(f"  gemini:     {'[已设置]' if _gemini_api_key else '[未设置]'}")
        logger.info(f"  dashscope:  {'[已设置]' if _dashscope_api_key else '[未设置]'}")
        logger.info(f"  cerebras:   {'[已设置]' if _cerebras_api_key else '[未设置]'}")
