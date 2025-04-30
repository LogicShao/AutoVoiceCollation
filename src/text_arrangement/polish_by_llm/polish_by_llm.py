import asyncio
import concurrent.futures
import logging
import os
import time
from collections import deque

from .polish_by_deepseek import polish_each_text as polish_each_text_deepseek
from .polish_by_gemini import polish_each_text as polish_each_text_gemini
from ..split_text import split_text_by_sentences
from ...config import LLM_TEMPERATURE, LLM_MAX_TOKENS, OUTPUT_DIR

MAX_RETRIES = 3
RETRY_BACKOFF = 2
MAX_CONCURRENT_REQUESTS = 5
MAX_REQUESTS_PER_MINUTE = 15

polish_each_text_dict = {
    'deepseek': polish_each_text_deepseek,
    'gemini': polish_each_text_gemini
}


class RateLimiter:
    def __init__(self, max_requests_per_minute):
        self.max_requests = max_requests_per_minute
        self.interval = 60.0
        self.timestamps = deque()

    async def wait_for_slot(self):
        while True:
            now = time.monotonic()
            while self.timestamps and now - self.timestamps[0] > self.interval:
                self.timestamps.popleft()

            if len(self.timestamps) < self.max_requests:
                self.timestamps.append(now)
                return
            else:
                sleep_time = self.interval - (now - self.timestamps[0]) + 0.01
                await asyncio.sleep(sleep_time)


def polish_text(txt: str, api_service: str = 'deepseek', temperature: float = LLM_TEMPERATURE,
                max_tokens: int = LLM_MAX_TOKENS, debug_flag: bool = False) -> str:
    """
    异步润色函数，支持每分钟请求限制 + 最大并发数控制 + 异常重试。
    :param txt: 要润色的文本
    :param api_service: 使用的API服务（deepseek 或 gemini）
    :param temperature: 温度参数
    :param max_tokens: 最大令牌数
    :param debug_flag: 是否开启调试模式
    :return: 润色后的文本
    """
    split_text = split_text_by_sentences(txt, max_tokens=max_tokens)
    polish_each_text = polish_each_text_dict.get(api_service)
    print(f"Using {api_service} API for polishing text.")
    rate_limiter = RateLimiter(MAX_REQUESTS_PER_MINUTE)

    async def safe_polish(chunk):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                await rate_limiter.wait_for_slot()  # ⏳ 等待速率许可
                return await loop.run_in_executor(executor, polish_each_text, chunk, temperature, max_tokens)
            except Exception as e:
                logging.warning(f"Error polishing chunk (attempt {attempt}): {e}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF * attempt)
                else:
                    logging.error(f"Failed to process chunk after {MAX_RETRIES} attempts.")
                    return chunk  # fallback: return original
        return chunk

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

    if debug_flag:
        debug_text = ""
        for i, polished, original in zip(range(len(polished_chunks)), polished_chunks, split_text):
            debug_text += f"Chunk {i + 1}:\n"
            debug_text += f"Original: {original}\n"
            debug_text += f"Polished: {polished}\n\n"
        debug_text_file = os.path.join(OUTPUT_DIR, "debug_polished_text.txt")
        with open(debug_text_file, "w", encoding="utf-8") as f:
            f.write(debug_text)

    return "\n\n".join(polished_chunks).strip()
