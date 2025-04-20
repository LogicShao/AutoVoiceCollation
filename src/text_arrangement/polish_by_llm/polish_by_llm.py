import asyncio
import concurrent.futures
import logging

from .polish_by_deepseek import polish_each_text as polish_each_text_deepseek
from .polish_by_gemini import polish_each_text as polish_each_text_gemini
from ..split_text import split_text_by_sentences
from ...config import LLM_TEMPERATURE, LLM_MAX_TOKENS

polish_each_text_dict = {
    'deepseek': polish_each_text_deepseek,
    'gemini': polish_each_text_gemini
}

MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds
MAX_CONCURRENT_REQUESTS = 5  # 根据API限制进行调整


def polish_text(txt: str, api_service: str = 'deepseek', temperature: float = LLM_TEMPERATURE,
                max_tokens: int = LLM_MAX_TOKENS) -> str:
    """
    异步优化：对文本进行润色处理，分段、删除口头禅、修改错别字等。
    支持并发加速，并包含异常重试机制。
    :param txt: 要处理的文本
    :param api_service: 使用的API服务（'deepseek'或'gemini'）
    :param temperature: 温度参数
    :param max_tokens: 最大输出字符数
    :return: 处理后的文本
    """
    split_text = split_text_by_sentences(txt)
    polish_each_text = polish_each_text_dict.get(api_service)
    print(f"Using {api_service} API for polishing text.")

    async def safe_polish(chunk):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return await loop.run_in_executor(executor, polish_each_text, chunk, temperature, max_tokens)
            except Exception as e:
                logging.warning(f"Error polishing chunk (attempt {attempt}): {e}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF * attempt)
                else:
                    logging.error(f"Failed to process chunk after {MAX_RETRIES} attempts.")
                    return chunk  # fallback: return original text if failed

    async def polish_all():
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async def sem_safe_polish(chunk):
            async with semaphore:
                return await safe_polish(chunk)

        tasks = [sem_safe_polish(chunk) for chunk in split_text]
        results = await asyncio.gather(*tasks)
        return results

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        polished_chunks = loop.run_until_complete(polish_all())

    return "\n\n".join(polished_chunks).strip()
