from src.services.llm.models import LLMQueryParams
from src.services.llm.prompts import get_prompt
from src.utils.logging.logger import get_logger

logger = get_logger(__name__)


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
    prompt_spec = get_prompt("summary")
    prompt = prompt_spec.render_user(text=txt, title=f"标题:{title}")

    logger.info(
        f"Summarizing text with API server: {api_server}, temperature: {temperature}, max_tokens: {max_tokens}"
    )

    from src.services.llm import query_llm

    return query_llm(
        LLMQueryParams(
            content=prompt,
            system_instruction=prompt_spec.render_system(),
            temperature=temperature,
            max_tokens=max_tokens,
            api_server=api_server,
        )
    )
