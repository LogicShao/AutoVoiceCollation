import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

import requests
from google import genai
from google.genai import types
from openai import OpenAI


# TODO: 接入ChatGPT等模型

class LLMApiSupported(StrEnum):
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"  # 默认使用 deepseek-chat 模型
    DEEPSEEK_CHAT = "deepseek-chat"
    DEEPSEEK_REASONER = "deepseek-reasoner"
    QWEN3 = "qwen3"  # 默认使用 qwen3-plus 模型
    QWEN3_PLUS = "qwen3-plus"
    QWEN3_MAX = "qwen3-max"


@dataclass
class LLMQueryParams:
    content: str
    system_instruction: str = "You are a helpful assistant."
    temperature: float = 0.3
    max_tokens: int = 1024
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    api_server: LLMApiSupported = "gemini"


_deepseek_client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")


def query_deepseek_chat(params: LLMQueryParams) -> str:
    """Query the DeepSeek API with a parameter object."""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
        "Content-Type": "application/json"
    }

    messages = [
        {"role": "system", "content": params.system_instruction},
        {"role": "user", "content": params.content}
    ]

    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": params.temperature,
        "split_len": params.max_tokens,
        "stream": False
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    else:
        raise Exception(f"Request failed with status code: {response.status_code}, error: {response.text}")


def query_deepseek_reasoner(params: LLMQueryParams) -> str:
    """Query the DeepSeek API with a parameter object."""
    response = _deepseek_client.chat.completions.create(
        model="deepseek-reasoner",
        messages=[
            {"role": "system", "content": params.system_instruction},
            {"role": "user", "content": params.content}
        ],
        temperature=params.temperature,
        max_tokens=params.max_tokens,
        stream=False
    )
    return response.choices[0].message.content.strip()


_gemini_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))


def query_gemini(params: LLMQueryParams) -> str:
    """Query the Gemini API with a parameter object."""
    config_params_dict = {
        "temperature": params.temperature,
        "max_output_tokens": params.max_tokens,
        "system_instruction": params.system_instruction,
    }

    if params.top_k:
        config_params_dict["top_k"] = params.top_k
    if params.top_p:
        config_params_dict["top_p"] = params.top_p

    response = _gemini_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=params.content,
        config=types.GenerateContentConfig(**config_params_dict),
    )
    return response.text.strip()


_dashscope_client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


def query_qwen3_plus(params: LLMQueryParams) -> str:
    response = _dashscope_client.chat.completions.create(
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
    response = _dashscope_client.chat.completions.create(
        model="qwen-max",
        messages=[
            {"role": "system", "content": params.system_instruction},
            {"role": "user", "content": params.content},
        ],
        temperature=params.temperature,
        max_tokens=params.max_tokens,
    )
    return response.choices[0].message.content.strip()


_support_LLM_api_query_func = {
    "deepseek": query_deepseek_chat,
    "deepseek-reasoner": query_deepseek_reasoner,
    "deepseek-chat": query_deepseek_chat,
    "gemini": query_gemini,
    "qwen3": query_qwen3_plus,
    "qwen3-plus": query_qwen3_plus,
    "qwen3-max": query_qwen3_max,
}


def query_llm(params: LLMQueryParams) -> str:
    """Query the LLM based on the specified API server."""
    query_api = params.api_server
    if query_api not in _support_LLM_api_query_func:
        raise Exception(f"Unsupported API server: {query_api}")
    return _support_LLM_api_query_func[query_api](params)
