import re


def split_text_by_sentences(txt: str, split_len: int) -> list[str]:
    """
    通过句子切分文本，确保每段不超过 max_tokens 字符。
    句子通过标点符号（. ? !）来分割。
    :param txt: 要分割的文本
    :param split_len: 每段文本的最大字符数
    :return: 分割后的文本列表
    """
    if not txt:
        return []

    # 使用正则表达式分割文本为句子（句号、问号、感叹号 / 换行后切分）
    # NOTE: 文本未以标点结尾或完全没有标点时，必须保留尾部内容，否则会出现 0 chunks 导致润色为空。
    pattern = r"([.。!！？?\n])"

    parts = re.split(pattern, txt)
    delimiters = {".", "。", "!", "！", "?", "？", "\n"}

    sentences: list[str] = []
    buf = ""
    for part in parts:
        if not part:
            continue
        if part in delimiters:
            buf += part
            if buf:
                sentences.append(buf)
            buf = ""
        else:
            buf += part

    if buf.strip():
        sentences.append(buf)

    split_texts: list[str] = []
    current_chunk = ""

    for sentence in sentences:
        if not sentence.strip():
            continue

        # 如果单个“句子”本身就超过分段长度（常见于 ASR 无标点输出），回退到按长度切分，避免空 chunk 或超长 chunk。
        if len(sentence) > split_len:
            if current_chunk.strip():
                split_texts.append(current_chunk.strip())
                current_chunk = ""
            for sub in smart_split(sentence, split_len=split_len):
                sub = sub.strip()
                if sub:
                    split_texts.append(sub)
            continue

        extra_sep = 1 if current_chunk else 0
        if len(current_chunk) + len(sentence) + extra_sep > split_len:
            if current_chunk.strip():
                split_texts.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk = f"{current_chunk}{sentence}" if current_chunk else sentence

    if current_chunk.strip():
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
                if current[j].isspace() or is_chinese(current[j]) and is_chinese(current[j - 1]):
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
