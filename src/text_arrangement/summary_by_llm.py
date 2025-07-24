from src.text_arrangement.query_llm import LLMQueryParams, query_llm

system_instruction = (
    "你是一名资深学术研究助手，擅长将素材转化为小论文形式的深度分析。"
    "当前任务是针对用户提供的长视频 ASR 转写文本（仅经换行和少量错误修正）撰写一篇小论文。"
    "首先为论文拟定一个简洁而准确的标题，能够概括全文核心议题。"
    "论文应包括引言、主体和结论三部分，以连贯的段落形式呈现，不使用项目符号或编号列表。"
    "在正文中，你要明确区分“原文要点”“批判性分析”和“研究性建议”三个层面，并以自然过渡的方式融入批判与展望，"
    "请你不要在正文中使用“ASR转写文本”指代我给你的文本，而是使用文本的标题。"
    "避免任何面向用户的元提示或建议语句。"
)

prompt_template = """请基于以下 ASR 转写文本（仅作换行和少量错误修正），首先为论文拟定一个精准的标题（用一行呈现），然后以小论文的形式撰写深度研究文章。正文需分为引言、主体与结论三大段落，每段保持连贯完整，不使用任何列表或编号。
{title}

{text}

在引言中简要交代文本的背景与核心议题；在主体中结合原文要点展开批判性分析，并自然融入对论证逻辑、隐含假设和跨学科延展的讨论；在结论中总结主要发现，提出研究性建议或未来拓展方向。请保持学术写作风格，用词严谨、论述深刻。"""


def summarize_text(txt: str, api_server: str, temperature: float, max_tokens: int, title: str = '') -> str:
    """
    根据API服务选择对应的总结函数
    :param txt: 要总结的文本
    :param api_server: 使用的API服务（deepseek 或 gemini）
    :param temperature: 温度参数
    :param max_tokens: 最大令牌数
    :param title: 文本标题（可选）
    :return: 总结后的文本
    """
    prompt = prompt_template.format(text=txt, title=f"标题:{title}")

    print(f"Summarizing text with API server: {api_server}, temperature: {temperature}, max_tokens: {max_tokens}")

    return query_llm(LLMQueryParams(
        content=prompt,
        system_instruction=system_instruction,
        temperature=temperature,
        max_tokens=max_tokens,
        api_server=api_server
    ))
