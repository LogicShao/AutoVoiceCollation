from src.text_arrangement.query_llm import LLMQueryParams, query_llm

system_instruction = (
    "你是一个专业的文本结构分析与摘要助手。"
    "你的任务是从用户提供的文本中，客观地提炼出其结构与要点，"
    "不进行主观创造、改写、优化语言，仅做结构化总结与信息抽取。"
    "请尊重原始语言风格，包括其中的口语、重复和语气，不做润色。"
)

prompt_template = """请你对以下文本进行结构与内容分析，仅提取信息，不进行语言优化：

{text}

请从以下四个方面进行客观说明（不添加主观判断）：
1. **核心主题**：该文本集中表达的核心话题或主旨是什么？
2. **结构逻辑**：文本是否存在明显的段落结构？如：引入、展开、转折、总结等。
3. **语言特征**：是否包含明显的口语表达、重复句式、语气词或情绪性用语？
4. **文体风格**：该文本整体风格更接近哪种类型？如：正式文体、口语叙述、说明类文本等。
"""


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
