import asyncio
import logging
import os

from src.core.exceptions import TaskCancelledException
from src.services.llm import (
    LLMQueryParams,
    is_local_llm,
    query_llm,
    query_llm_async,
)
from src.services.llm.models import LLM_MODELS
from src.services.llm.prompts import PromptSpec, get_prompt
from src.text_arrangement.split_text import split_text_by_sentences
from src.utils.config import get_config
from src.utils.helpers.task_manager import get_task_manager
from src.utils.logging.logger import get_logger

logger = get_logger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 30
MAX_CONCURRENT_REQUESTS = 5


def _supports_async(api_server: str) -> bool:
    cfg = LLM_MODELS.get(api_server)
    if not cfg:
        return False
    return cfg["provider"] in ("deepseek", "dashscope", "cerebras")


def polish_each_text(
    txt: str,
    api_server: str,
    temperature: float,
    max_tokens: int,
    prompt_spec: PromptSpec | None = None,
) -> str:
    prompt_spec = prompt_spec or get_prompt("polish")
    prompt = prompt_spec.render_user(text=txt)
    return query_llm(
        LLMQueryParams(
            content=prompt,
            system_instruction=prompt_spec.system,
            temperature=temperature,
            max_tokens=max_tokens,
            api_server=api_server,
        )
    )


async def _polish_each_text_async(
    txt: str,
    api_server: str,
    temperature: float,
    max_tokens: int,
    prompt_spec: PromptSpec | None = None,
) -> str:
    prompt_spec = prompt_spec or get_prompt("polish")
    prompt = prompt_spec.render_user(text=txt)
    return await query_llm_async(
        LLMQueryParams(
            content=prompt,
            system_instruction=prompt_spec.system,
            temperature=temperature,
            max_tokens=max_tokens,
            api_server=api_server,
        )
    )


def polish_text(
    txt: str,
    api_service: str,
    split_len: int,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    debug_flag: bool = False,
    task_id: str | None = None,
    async_flag: bool = True,
) -> str:
    assert split_len <= max_tokens * 0.7, "分段长度不能超过最大令牌数的70%，可能导致输出不完整。"

    task_manager = get_task_manager() if task_id else None
    logger.info(f"Using {api_service} API for polishing text.")
    logger.info(f"Temperature: {temperature}, Max tokens: {max_tokens}, Split length: {split_len}")
    prompt_spec = get_prompt("polish")
    split_text = split_text_by_sentences(txt, split_len=split_len)
    logger.info(f"Splitting text into {len(split_text)} chunks for processing.")

    use_async = async_flag and _supports_async(api_service) and not is_local_llm(api_service)

    if not use_async:
        logger.info("Running in synchronous mode.")
        polish_chunks = []
        for i, chunk in enumerate(split_text):
            if task_id:
                task_manager.check_cancellation(task_id)
            logger.info(f"processing chunk {i + 1}/{len(split_text)}")
            polish_chunks.append(
                polish_each_text(chunk, api_service, temperature, max_tokens, prompt_spec)
            )
            logger.info(f"Chunk {i + 1} polished successfully.")
        return "\n\n".join(polish_chunks).strip()

    logger.info("Running in asynchronous mode (aiohttp).")

    async def safe_polish(chunk: str, chunk_id: int):
        if task_id:
            task_manager.check_cancellation(task_id)
        logger.info(f"Processing chunk {chunk_id + 1}/{len(split_text)}")
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if task_id:
                    task_manager.check_cancellation(task_id)
                ret = await _polish_each_text_async(
                    chunk, api_service, temperature, max_tokens, prompt_spec
                )
                logger.info(f"Chunk {chunk_id + 1} polished successfully.")
                return ret
            except TaskCancelledException:
                raise
            except Exception as e:
                logging.warning(f"Error polishing chunk (attempt {attempt}): {e}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF * attempt)
        logging.error(f"Failed to process chunk after {MAX_RETRIES} attempts.")
        return chunk

    async def polish_all():
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async def sem_safe(chunk, chunk_id):
            async with semaphore:
                return await safe_polish(chunk, chunk_id)

        tasks = [sem_safe(chunk, i) for i, chunk in enumerate(split_text)]
        return await asyncio.gather(*tasks)

    polished_chunks = asyncio.run(polish_all())

    if debug_flag:
        config = get_config()
        debug_text = ""
        for i, polished, original in zip(range(len(polished_chunks)), polished_chunks, split_text):
            debug_text += f"Chunk {i + 1}:\n"
            debug_text += f"Original: {original}\n"
            debug_text += f"Polished: {polished}\n\n"
        debug_text_file = os.path.join(str(config.paths.output_dir), "debug_polished_text.txt")
        with open(debug_text_file, "w", encoding="utf-8") as f:
            f.write(debug_text)

    return "\n\n".join(polished_chunks).strip()
