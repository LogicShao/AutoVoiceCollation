import asyncio
import concurrent.futures
import logging
import os
import time
from collections import deque

from src.config import OUTPUT_DIR
from src.text_arrangement.query_llm import LLMQueryParams, query_llm
from src.text_arrangement.split_text import split_text_by_sentences

MAX_RETRIES = 3
RETRY_BACKOFF = 30
MAX_CONCURRENT_REQUESTS = 5
MAX_REQUESTS_PER_MINUTE = 10

system_prompt = """你是一个高级语言处理助手，专注于文本清理、分段与拼写修正。请按照以下要求处理以下文本：
1. **去除冗余内容**：删除所有的口吃、语气词、重复的词汇或无关的表达（例如：“呃”，“嗯”，“啊”）。
2. **合理分段**：根据上下文将文本分段，使其更加清晰易懂。
3. **拼写和语法修正**：自动修正拼写错误、语法错误和标点符号问题。
4. **保留原意和风格**：在修改过程中，请尽量保留文本的原意和风格，不做任何不必要的改写。
5. **简化和优化**：适当去除冗余、重复的内容，但确保不改变原文的核心信息。
根据这些要求，处理下面的文本：
"""


def polish_each_text(txt: str, api_server: str, temperature: float, max_tokens: int) -> str:
    """
    根据API服务选择对应的润色函数
    :param txt: 要润色的文本
    :param api_server: 使用的API服务（deepseek 或 gemini）
    :param temperature: 温度参数
    :param max_tokens: 最大令牌数
    :return: 润色后的文本
    """
    prompt = (f"以下是语音识别的原始文本：\n{txt}\n\n"
              f"请你仅仅输出整理后的文本，不要增加多余的文字，"
              f"也不要使用任何markdown形式的文字，只使用plain text的形式。")

    return query_llm(LLMQueryParams(
        content=prompt,
        system_instruction=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        api_server=api_server
    ))


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


def polish_text(txt: str, api_service: str, temperature: float, split_len: int, max_tokens: int,
                debug_flag: bool, async_flag: bool = True) -> str:
    """
    异步润色函数，支持每分钟请求限制 + 最大并发数控制 + 异常重试。
    :param txt: 要润色的文本
    :param api_service: 使用的API服务（deepseek 或 gemini）
    :param temperature: 温度参数
    :param split_len: 分段长度
    :param max_tokens: 最大令牌数
    :param debug_flag: 是否开启调试模式
    :param async_flag: 是否使用异步方式
    :return: 润色后的文本
    """
    assert split_len <= max_tokens * 0.7, "分段长度不能超过最大令牌数的70%，可能导致输出不完整。"

    # TODO: 改进异步调用
    print(f"Using {api_service} API for polishing text.")
    print(f"Temperature: {temperature}, Max tokens: {max_tokens}, Split length: {split_len}")
    split_text = split_text_by_sentences(txt, split_len=split_len)
    print(f"Splitting text into {len(split_text)} chunks for processing.")

    if not async_flag:
        # 如果不使用异步方式，直接调用同步函数
        print("Running in synchronous mode.")
        polish_chunks = []
        for i, chunk in enumerate(split_text):
            print(f"processing chunk {i + 1}/{len(split_text)}")
            polish_chunks.append(polish_each_text(chunk, api_service, temperature, max_tokens))
            print(f"Chunk {i + 1} polished successfully.")
        return "\n\n".join(polish_chunks).strip()

    print("Running in asynchronous mode.")
    rate_limiter = RateLimiter(MAX_REQUESTS_PER_MINUTE)

    async def safe_polish(chunk: str, task_id: int):
        print(f"Processing chunk {task_id + 1}/{len(split_text)}")
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                await rate_limiter.wait_for_slot()  # ⏳ 等待速率许可
                ret = await loop.run_in_executor(executor, polish_each_text, chunk, api_service, temperature,
                                                 max_tokens)
                print(f"Chunk {task_id + 1} polished successfully.")
                return ret
            except Exception as e:
                logging.warning(f"Error polishing chunk (attempt {attempt}): {e}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF * attempt)
        logging.error(f"Failed to process chunk after {MAX_RETRIES} attempts.")
        return chunk

    async def polish_all():
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async def sem_safe_polish(chunk, task_id):
            async with semaphore:
                return await safe_polish(chunk, task_id)

        tasks = [sem_safe_polish(chunk, task_id) for task_id, chunk in enumerate(split_text)]
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
