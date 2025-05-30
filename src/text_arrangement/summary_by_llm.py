from src.text_arrangement.query_llm import LLMQueryParams, query_llm

system_instruction = (
    "你是一个专业的内容分析助手，请根据用户提供的文本内容，"
    "提炼出内容的主题、主要讨论点，并简洁概括其结构与要点。"
    "请尽量保留原文语言风格，不进行创作或过度润饰，只做结构和重点的总结。"
)

prompt_template = """请你根据以下文本进行总结和结构说明：

{text}

请从以下几个方面进行说明：
1. 文本的核心主题是什么？
2. 是否存在结构上的段落逻辑（比如介绍、展开、结论）？
3. 是否包含较多口语表达、重复或情绪性语言？
4. 整体风格偏向正式、口语、叙述或说明？"""


def summarize_text(txt: str, api_server: str, temperature: float, max_tokens: int) -> str:
    """
    根据API服务选择对应的总结函数
    :param txt: 要总结的文本
    :param api_server: 使用的API服务（deepseek 或 gemini）
    :param temperature: 温度参数
    :param max_tokens: 最大令牌数
    :return: 总结后的文本
    """
    prompt = prompt_template.format(text=txt)

    return query_llm(LLMQueryParams(
        content=prompt,
        system_instruction=system_instruction,
        temperature=temperature,
        max_tokens=max_tokens,
        api_server=api_server
    ))
