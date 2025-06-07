import re


def split_text_by_sentences(txt: str, split_len: int) -> list[str]:
    """
    通过句子切分文本，确保每段不超过 max_tokens 字符。
    句子通过标点符号（. ? !）来分割。
    :param txt: 要分割的文本
    :param split_len: 每段文本的最大字符数
    :return: 分割后的文本列表
    """
    # 使用正则表达式分割文本为句子（句号、问号、感叹号后切分）
    split_ch = ".。!！？?"
    pattern = r"([{}])".format(split_ch)
    sentences = re.split(pattern, txt)[:-1]  # 保留分隔符
    sentences = [sentences[i] + sentences[i + 1] for i in range(0, len(sentences), 2)]

    split_texts = []
    current_chunk = ""

    for sentence in sentences:
        # 如果加上当前句子的文本后超过了最大字符数，就分割成新的一段
        if len(current_chunk) + len(sentence) + 1 > split_len:
            split_texts.append(current_chunk.strip())
            current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += sentence
            else:
                current_chunk = sentence

    # 处理剩余的部分
    if current_chunk:
        split_texts.append(current_chunk.strip())

    return split_texts


def clean_asr_text(asr_result_text: str):
    # 移除所有 <|...|> 标签
    no_tags = re.sub(r"<\|.*?\|>", "", asr_result_text)
    return no_tags
