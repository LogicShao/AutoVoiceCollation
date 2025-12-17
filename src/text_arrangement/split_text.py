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


def is_chinese(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff"


def smart_split(txt: str, split_len: int) -> list[str]:
    result = []
    current = ""

    # 遍历每一个字符
    i = 0
    while i < len(txt):
        current += txt[i]

        # 达到分段长度限制
        if len(current) >= split_len:
            # 倒着寻找一个合适的断点（空格 或 两个中文之间）
            j = len(current) - 1
            while j > 0:
                if current[j].isspace():
                    break
                # 判断两个中文之间
                elif is_chinese(current[j]) and is_chinese(current[j - 1]):
                    break
                j -= 1

            # 如果找到了合适的断点
            if j > 0:
                result.append(current[: j + 1].strip())
                txt = current[j + 1 :] + txt[i + 1 :]
                current = ""
                i = -1  # 从头开始处理剩下的 txt
            else:
                # 没找到合适断点，只能硬切
                result.append(current.strip())
                current = ""
        i += 1

    if current:
        result.append(current.strip())

    return result
