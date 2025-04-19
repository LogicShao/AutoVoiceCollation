from .polish_by_deepseek import polish_each_text as polish_each_text_deepseek
from .polish_by_gemini import polish_each_text as polish_each_text_gemini
from ..split_text import split_text_by_sentences
from ...config import LLM_TEMPERATURE, LLM_MAX_TOKENS

polish_each_text_dict = {
    'deepseek': polish_each_text_deepseek,
    'gemini': polish_each_text_gemini
}


def polish_text(txt: str, api_service: str = 'deepseek', temperature: float = LLM_TEMPERATURE,
                max_tokens: int = LLM_MAX_TOKENS) -> str:
    """
    对文本进行润色处理，分段、删除口头禅、修改错别字等。
    :param txt: 要处理的文本
    :param api_service: 使用的API服务（'deepseek'或'gemini'）
    :param temperature: 温度参数
    :param max_tokens: 最大输出字符数
    :return: 处理后的文本
    """
    # 分割文本为句子
    split_text = split_text_by_sentences(txt)

    polished_text = ""
    polish_each_text = polish_each_text_dict.get(api_service)

    for text_chunk in split_text:
        polished_chunk = polish_each_text(text_chunk, temperature, max_tokens)
        polished_text += polished_chunk + "\n\n"  # 添加段落间距

    return polished_text.strip()
