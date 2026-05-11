"""
LLM服务工厂

统一管理所有LLM提供商的查询接口。
模型定义来自 models.LLM_MODELS（单一数据源）。
"""

from collections.abc import Callable
from functools import partial

from src.utils.config import get_config
from src.utils.logging.logger import get_logger

from .models import LLM_MODELS, LLMQueryParams, is_local_llm

logger = get_logger(__name__)

# 获取配置
config = get_config()

# ============= 客户端初始化 =============

_deepseek_client = None
_gemini_client = None
_dashscope_client = None
_cerebras_client = None


def _get_deepseek_client():
    global _deepseek_client
    if _deepseek_client is None:
        from openai import OpenAI

        _deepseek_client = OpenAI(
            api_key=config.llm.deepseek_api_key, base_url="https://api.deepseek.com"
        )
    return _deepseek_client


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai

        _gemini_client = genai.Client(api_key=config.llm.gemini_api_key)
    return _gemini_client


def _get_dashscope_client():
    global _dashscope_client
    if _dashscope_client is None:
        from openai import OpenAI

        _dashscope_client = OpenAI(
            api_key=config.llm.dashscope_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    return _dashscope_client


def _get_cerebras_client():
    global _cerebras_client
    if _cerebras_client is None:
        from cerebras.cloud.sdk import Cerebras

        _cerebras_client = Cerebras(api_key=config.llm.cerebras_api_key)
    return _cerebras_client


# ============= 通用查询函数 =============

_PROVIDER_CLIENTS: dict[str, Callable] = {
    "deepseek": _get_deepseek_client,
    "dashscope": _get_dashscope_client,
    "cerebras": _get_cerebras_client,
}


def _query_openai_compatible(params: LLMQueryParams, model_id: str, client_getter: Callable) -> str:
    client = client_getter()
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": params.system_instruction},
            {"role": "user", "content": params.content},
        ],
        temperature=params.temperature,
        max_tokens=params.max_tokens,
        stream=False,
    )
    return response.choices[0].message.content.strip()


def _query_gemini(params: LLMQueryParams, model_id: str) -> str:
    from google.genai import types

    client = _get_gemini_client()
    config_params = {
        "temperature": params.temperature,
        "max_output_tokens": params.max_tokens,
        "system_instruction": params.system_instruction,
    }
    if params.top_k:
        config_params["top_k"] = params.top_k
    if params.top_p:
        config_params["top_p"] = params.top_p

    response = client.models.generate_content(
        model=model_id,
        contents=params.content,
        config=types.GenerateContentConfig(**config_params),
    )
    return response.text.strip()


# ============= 本地LLM支持（可选）=============

_local_llm_initialized = False
_local_llm_func = None


def _init_local_llm():
    global _local_llm_initialized, _local_llm_func
    if _local_llm_initialized:
        return
    if not config.llm.local_llm_enabled:
        _local_llm_initialized = True
        return

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

        model_name = "Qwen/Qwen2.5-1.5B-Instruct"
        logger.info(f"Loading local model: {model_name} ... This may take a while.")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto", dtype="auto")

        def _query_local(params: LLMQueryParams) -> str:
            pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
            messages = [
                {"role": "system", "content": params.system_instruction},
                {"role": "user", "content": params.content},
            ]
            out = pipe(messages, temperature=params.temperature, max_new_tokens=params.max_tokens, do_sample=True)
            return out[0]["generated_text"][-1]["content"].strip()

        _local_llm_func = _query_local
        logger.info("Local LLM loaded successfully")
    except Exception as e:
        logger.warning(f"Failed to load local LLM: {e}")

    _local_llm_initialized = True


# ============= LLM服务注册表（自动生成）=============


def _build_registry() -> dict[str, Callable[[LLMQueryParams], str]]:
    registry: dict[str, Callable[[LLMQueryParams], str]] = {}
    for name, cfg in LLM_MODELS.items():
        provider = cfg["provider"]
        model_id = cfg["model_id"]
        if provider == "gemini":
            registry[name] = partial(_query_gemini, model_id=model_id)
        elif provider in _PROVIDER_CLIENTS:
            registry[name] = partial(
                _query_openai_compatible,
                model_id=model_id,
                client_getter=_PROVIDER_CLIENTS[provider],
            )
    return registry


_llm_registry: dict[str, Callable[[LLMQueryParams], str]] = _build_registry()


def query_llm(params: LLMQueryParams) -> str:
    """
    查询LLM（统一接口）

    Args:
        params: LLM查询参数

    Returns:
        str: LLM返回的文本

    Raises:
        ValueError: 不支持的LLM提供商
    """
    api_server = params.api_server

    # 处理本地LLM
    if is_local_llm(api_server):
        _init_local_llm()
        if _local_llm_func is None:
            raise ValueError("Local LLM is not enabled or failed to load")
        return _local_llm_func(params)

    # 处理云端LLM
    if api_server not in _llm_registry:
        raise ValueError(
            f"Unsupported LLM API: {api_server}. Supported: {list(_llm_registry.keys())}"
        )

    query_func = _llm_registry[api_server]
    return query_func(params)


# ============= 异步查询（用于 polish 并发优化）=============

_PROVIDER_BASE_URLS: dict[str, str] = {
    "deepseek": "https://api.deepseek.com/v1",
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "cerebras": "https://api.cerebras.ai/v1",
}

_PROVIDER_API_KEYS: dict[str, str] = {
    "deepseek": "deepseek_api_key",
    "dashscope": "dashscope_api_key",
    "cerebras": "cerebras_api_key",
}


def _get_api_key(provider: str) -> str:
    field = _PROVIDER_API_KEYS.get(provider, "")
    return getattr(config.llm, field, "") or ""


async def _query_openai_compatible_async(
    params: LLMQueryParams,
    model_id: str,
    base_url: str,
    api_key: str,
) -> str:
    import aiohttp

    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": params.system_instruction or ""},
            {"role": "user", "content": params.content},
        ],
        "temperature": params.temperature,
        "max_tokens": params.max_tokens,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session, session.post(
        f"{base_url}/chat/completions", json=payload, headers=headers
    ) as resp:
        data = await resp.json()
        if "choices" not in data:
            raise RuntimeError(f"LLM API error: {data}")
        return data["choices"][0]["message"]["content"].strip()


async def query_llm_async(params: LLMQueryParams) -> str:
    api_server = params.api_server
    if api_server not in LLM_MODELS:
        raise ValueError(
            f"Unsupported LLM API: {api_server}. Supported: {list(LLM_MODELS.keys())}"
        )
    cfg = LLM_MODELS[api_server]
    provider = cfg["provider"]
    model_id = cfg["model_id"]
    if provider in _PROVIDER_BASE_URLS:
        base_url = _PROVIDER_BASE_URLS[provider]
        api_key = _get_api_key(provider)
        return await _query_openai_compatible_async(params, model_id, base_url, api_key)
    raise ValueError(f"Async not supported for provider: {provider}")
