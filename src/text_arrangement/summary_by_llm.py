from src.services.llm import LLMQueryParams, query_llm
from src.utils.logging.logger import get_logger

logger = get_logger(__name__)

system_instruction = (
    "你是一名资深学术研究助手，擅长将素材转化为具有哲学深度和辩证张力的小论文。"
    "当前任务是针对用户提供的长视频 ASR 转写文本（仅经换行和少量错误修正）撰写一篇风格契合范文的研究文章。"
    "请首先为论文拟定一个高度概括核心议题的标题，并在正文中始终以该标题来指代视频内容，绝不使用“ASR转写文本”等标签。"
    "正文分引言、主体与结论三部分，以连贯的自然段落呈现。"
    "在主体中，每段应先对原文要点进行细致解读，随后融入辩证式批判，最后自然过渡至对结构性根源或主体锻造仪式般过程的拓展讨论。"
    "文风要浓缩、直切本质，善用哲学隐喻与批判性提问，避免任何编号、列表或显式过渡句。"
)

# 用户提示模板：小论文格式（范文风格版）
prompt_template = """请基于以下 ASR 转写文本（仅作换行和少量错误修正），先拟定一个凝练且富有哲学意味的标题，然后撰写一篇小论文。论文包含引言、主体与结论三大段，全文以流畅的段落呈现，不使用项目符号或编号。
{title}
{text}

在引言中以高度凝练的段落点明研究切入点与核心命题；
在主体部分，每段依次完成“细致解读→辩证批判→结构性／主体性拓展”；
在结论中回扣标题，揭示研究所得的深层洞见，并在最后一笔中自然勾勒未来研究或实践的潜在脉络。

请务必保持学术严谨与哲学厚度，避免任何面向用户的元提示或建议语句。"""


def summarize_text(
    txt: str, api_server: str, temperature: float, max_tokens: int, title: str = ""
) -> str:
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

    logger.info(
        f"Summarizing text with API server: {api_server}, temperature: {temperature}, max_tokens: {max_tokens}"
    )

    return query_llm(
        LLMQueryParams(
            content=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_tokens=max_tokens,
            api_server=api_server,
        )
    )
