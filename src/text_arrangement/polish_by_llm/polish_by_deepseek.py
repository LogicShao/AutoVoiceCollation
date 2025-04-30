import os

import requests

API_KEY = os.environ['DEEPSEEK_API_KEY']
API_URL = 'https://api.deepseek.com/v1/chat/completions'

system_prompt = """你是一个高级语言模型，专注于中文文本的整理与优化。你的任务是对以下文本进行处理，要求如下：
1. 删除口吃、语气词：如“呃”，“嗯”，“啊”，“就是说”，“这个”。
2. 优化文本分段：根据语义合理分段，确保文本流畅易读。
3. 修正拼写和语法错误：如果发现明显的拼写或语法错误，进行修正。
4. 保留原文风格：不要进行内容的扩写或润色，只做必要的修改和调整。
5. 简化冗余内容：如果有多余或重复的部分，请适当简化，但不要改变原意。
请在保留原意和风格的前提下，优化以下文本：
"""


def polish_each_text(txt: str, temperature: float, max_tokens: int) -> str:
    """
    使用 DeepSeek API 对语音识别生成的中文文本进行整理。
    :param txt: 语音识别生成的中文文本
    :param temperature: 温度参数
    :param max_tokens: 最大输出字符数
    :return: 整理后的文本
    """
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }

    prompt = f"以下是语音识别的原始文本：\n{txt}\n\n请你仅仅输出整理后的文本，不要增加多余的文字，也不要使用任何markdown形式的文字，只使用plain text的形式。"

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }

    response = requests.post(API_URL, headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    else:
        raise Exception(f"请求失败，状态码: {response.status_code}, 错误信息: {response.text}")
