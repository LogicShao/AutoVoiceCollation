"""
LLM服务工厂

统一管理所有LLM提供商的查询接口
"""

import os
from typing import Callable, Dict

from cerebras.cloud.sdk import Cerebras
from google import genai
from google.genai import types
from openai import OpenAI

from src.utils.logging.logger import get_logger
from .models import LLMQueryParams, is_local_llm
from src.utils.config import get_config

logger = get_logger(__name__)

# 获取配置
config = get_config()

# ============= 客户端初始化 =============

_deepseek_client = None
_gemini_client = None
_dashscope_client = None
_cerebras_client = None


def _get_deepseek_client():
    """获取DeepSeek客户端（延迟初始化）"""
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com"
        )
    return _deepseek_client


def _get_gemini_client():
    """获取Gemini客户端（延迟初始化）"""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _gemini_client


def _get_dashscope_client():
    """获取Dashscope客户端（延迟初始化）"""
    global _dashscope_client
    if _dashscope_client is None:
        _dashscope_client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    return _dashscope_client


def _get_cerebras_client():
    """获取Cerebras客户端（延迟初始化）"""
    global _cerebras_client
    if _cerebras_client is None:
        _cerebras_client = Cerebras(api_key=os.getenv("CEREBRAS_API_KEY"))
    return _cerebras_client


# ============= LLM查询函数 =============


def query_deepseek_chat(params: LLMQueryParams) -> str:
    """查询DeepSeek Chat模型"""
    client = _get_deepseek_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": params.system_instruction},
            {"role": "user", "content": params.content},
        ],
        temperature=params.temperature,
        max_tokens=params.max_tokens,
        stream=False,
    )
    return response.choices[0].message.content.strip()


def query_deepseek_reasoner(params: LLMQueryParams) -> str:
    """查询DeepSeek Reasoner模型"""
    client = _get_deepseek_client()
    response = client.chat.completions.create(
        model="deepseek-reasoner",
        messages=[
            {"role": "system", "content": params.system_instruction},
            {"role": "user", "content": params.content},
        ],
        temperature=params.temperature,
        max_tokens=params.max_tokens,
        stream=False,
    )
    return response.choices[0].message.content.strip()


def query_gemini_2_0_flash(params: LLMQueryParams) -> str:
    """查询Gemini 2.0 Flash模型"""
    client = _get_gemini_client()

    config_params_dict = {
        "temperature": params.temperature,
        "max_output_tokens": params.max_tokens,
        "system_instruction": params.system_instruction,
    }

    if params.top_k:
        config_params_dict["top_k"] = params.top_k
    if params.top_p:
        config_params_dict["top_p"] = params.top_p

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=params.content,
        config=types.GenerateContentConfig(**config_params_dict),
    )
    return response.text.strip()


def query_qwen3_plus(params: LLMQueryParams) -> str:
    """查询Qwen3 Plus模型"""
    client = _get_dashscope_client()
    response = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": params.system_instruction},
            {"role": "user", "content": params.content},
        ],
        temperature=params.temperature,
        max_tokens=params.max_tokens,
    )
    return response.choices[0].message.content.strip()


def query_qwen3_max(params: LLMQueryParams) -> str:
    """查询Qwen3 Max模型"""
    client = _get_dashscope_client()
    response = client.chat.completions.create(
        model="qwen-max",
        messages=[
            {"role": "system", "content": params.system_instruction},
            {"role": "user", "content": params.content},
        ],
        temperature=params.temperature,
        max_tokens=params.max_tokens,
    )
    return response.choices[0].message.content.strip()


def query_cerebras_qwen3_32b(params: LLMQueryParams) -> str:
    """查询Cerebras Qwen3 32B模型"""
    client = _get_cerebras_client()
    response = client.chat.completions.create(
        model="qwen-3-32b",
        messages=[
            {"role": "system", "content": params.system_instruction},
            {"role": "user", "content": params.content},
        ],
        temperature=params.temperature,
        max_tokens=params.max_tokens,
    )
    return response.choices[0].message.content.strip()


def query_cerebras_qwen3_235b_instruct(params: LLMQueryParams) -> str:
    """查询Cerebras Qwen3 235B Instruct模型"""
    client = _get_cerebras_client()
    response = client.chat.completions.create(
        model="qwen-3-235b-a22b-instruct-2507",
        messages=[
            {"role": "system", "content": params.system_instruction},
            {"role": "user", "content": params.content},
        ],
        temperature=params.temperature,
        max_tokens=params.max_tokens,
    )
    return response.choices[0].message.content.strip()


def query_cerebras_qwen3_235b_thinking(params: LLMQueryParams) -> str:
    """查询Cerebras Qwen3 235B Thinking模型"""
    client = _get_cerebras_client()
    response = client.chat.completions.create(
        model="qwen-3-235b-a22b-thinking-2507",
        messages=[
            {"role": "system", "content": params.system_instruction},
            {"role": "user", "content": params.content},
        ],
        temperature=params.temperature,
        max_tokens=params.max_tokens,
    )
    return response.choices[0].message.content.strip()


# ============= 本地LLM支持（可选）=============

_local_llm_initialized = False
_local_llm_func = None


def _init_local_llm():
    """初始化本地LLM（延迟加载）"""
    global _local_llm_initialized, _local_llm_func

    if _local_llm_initialized:
        return

    if not config.llm.local_llm_enabled:
        _local_llm_initialized = True
        return

    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

        model_name = "Qwen/Qwen2.5-1.5B-Instruct"
        logger.info(f"Loading local model: {model_name} ... This may take a while.")

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name, device_map="auto", dtype="auto"
        )

        def query_local_qwen2_5(params: LLMQueryParams) -> str:
            pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
            messages = [
                {"role": "system", "content": params.system_instruction},
                {"role": "user", "content": params.content},
            ]
            out = pipe(
                messages,
                temperature=params.temperature,
                max_new_tokens=params.max_tokens,
                do_sample=True,
            )
            return out[0]["generated_text"][-1]["content"].strip()

        _local_llm_func = query_local_qwen2_5
        logger.info("Local LLM loaded successfully")

    except Exception as e:
        logger.warning(f"Failed to load local LLM: {e}")

    _local_llm_initialized = True


# ============= LLM服务注册表 =============

_llm_registry: Dict[str, Callable[[LLMQueryParams], str]] = {
    "deepseek-chat": query_deepseek_chat,
    "deepseek-reasoner": query_deepseek_reasoner,
    "gemini-2.0-flash": query_gemini_2_0_flash,
    "qwen3-plus": query_qwen3_plus,
    "qwen3-max": query_qwen3_max,
    "Cerebras:Qwen-3-32B": query_cerebras_qwen3_32b,
    "Cerebras:Qwen-3-235B-Instruct": query_cerebras_qwen3_235b_instruct,
    "Cerebras:Qwen-3-235B-Thinking": query_cerebras_qwen3_235b_thinking,
}


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
            f"Unsupported LLM API: {api_server}. "
            f"Supported: {list(_llm_registry.keys())}"
        )

    query_func = _llm_registry[api_server]
    return query_func(params)
