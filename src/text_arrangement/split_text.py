import re


def split_text_for_api(txt: str, max_tokens: int = 4000) -> list[str]:
    """
    将文本按 max_tokens 分割，确保每段文本长度不会超过 max_tokens 字符。
    尝试按段落、句子或字符进行分割，以保持文本的可读性和完整性。
    :param txt: 要分割的文本
    :param max_tokens: 每段文本的最大字符数
    :return: 分割后的文本列表
    """
    paragraphs = txt.split('\n')
    split_text = []
    current_chunk = ""

    for para in paragraphs:
        # 如果加上当前段落的文本后超过了最大字符数，就分割成新的一段
        if len(current_chunk) + len(para) + 1 > max_tokens:
            split_text.append(current_chunk.strip())
            current_chunk = para
        else:
            if current_chunk:
                current_chunk += '\n' + para
            else:
                current_chunk = para

    # 处理剩余的部分
    if current_chunk:
        split_text.append(current_chunk.strip())

    return split_text


def split_text_by_sentences(txt: str, max_tokens: int = 4000) -> list[str]:
    """
    通过句子切分文本，确保每段不超过 max_tokens 字符。
    句子通过标点符号（. ? !）来分割。
    :param txt: 要分割的文本
    :param max_tokens: 每段文本的最大字符数
    :return: 分割后的文本列表
    """
    # 使用正则表达式分割文本为句子（句号、问号、感叹号后切分）
    sentences = re.split(r'([.!?])', txt)  # 保留分隔符
    sentences = [s.strip() + (sentences[i + 1] if i + 1 < len(sentences) else '') for i, s in enumerate(sentences) if
                 s.strip()]

    split_text = []
    current_chunk = ""

    for sentence in sentences:
        # 如果加上当前句子的文本后超过了最大字符数，就分割成新的一段
        if len(current_chunk) + len(sentence) + 1 > max_tokens:
            split_text.append(current_chunk.strip())
            current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += ' ' + sentence
            else:
                current_chunk = sentence

    # 处理剩余的部分
    if current_chunk:
        split_text.append(current_chunk.strip())

    return split_text
