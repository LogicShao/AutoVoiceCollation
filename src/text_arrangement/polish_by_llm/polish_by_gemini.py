from google import genai
from google.genai import types

from ...config import GEMINI_API

API_KEY = GEMINI_API
client = genai.Client(api_key=API_KEY)

system_prompt = """你是一个高级语言处理助手，专注于文本清理、分段与拼写修正。请按照以下要求处理以下文本：
1. **去除冗余内容**：删除所有的口吃、语气词、重复的词汇或无关的表达（例如：“呃”，“嗯”，“啊”）。
2. **合理分段**：根据上下文将文本分段，使其更加清晰易懂。
3. **拼写和语法修正**：自动修正拼写错误、语法错误和标点符号问题。
4. **保留原意和风格**：在修改过程中，请尽量保留文本的原意和风格，不做任何不必要的改写。
5. **简化和优化**：适当去除冗余、重复的内容，但确保不改变原文的核心信息。
根据这些要求，处理下面的文本：
"""


def polish_each_text(txt: str, temperate: float, max_tokens: int) -> str:
    """
    使用 Gemini 对单段文本进行整理。
    :param txt: 语音识别生成的中文文本
    :param temperate: 温度参数
    :param max_tokens: 最大输出字符数
    :return: 整理后的文本
    """
    prompt = f"以下是语音识别的原始文本：\n{txt}\n\n请输出整理后的文本。"

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperate,
            system_instruction=system_prompt
        )
    )
    return response.text
