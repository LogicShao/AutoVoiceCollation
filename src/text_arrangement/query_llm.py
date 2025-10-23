import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

import requests
from cerebras.cloud.sdk import Cerebras
from google import genai
from google.genai import types
from openai import OpenAI
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

from config import LOCAL_LLM_ENABLED, DEBUG_FLAG
from src.load_api_key import check_api_keys
from src.logger import get_logger

logger = get_logger(__name__)

check_api_keys(debug=DEBUG_FLAG)


class LLMApiSupported(StrEnum):
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"  # 默认使用 deepseek-chat 模型
    DEEPSEEK_CHAT = "deepseek-chat"
    DEEPSEEK_REASONER = "deepseek-reasoner"
    QWEN3 = "qwen3"  # 默认使用 qwen3-plus 模型
    QWEN3_PLUS = "qwen3-plus"
    QWEN3_MAX = "qwen3-max"
    CEREBRAS_QWEN3_32B = "Cerebras:Qwen-3-32B"
    CEREBRAS_QWEN3_235B_INSTRUCT = "Cerebras:Qwen-3-235B-Instruct"
    CEREBRAS_QWEN3_235B_THINKING = "Cerebras:Qwen-3-235B-Thinking"
    LOCAL_QWEN2_5 = "local:Qwen/Qwen2.5-1.5B-Instruct"


def is_local_llm(api_name: str) -> bool:
    return api_name.startswith("local:")


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
        "max_tokens": params.max_tokens,
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


def query_gemini_2_0_flash(params: LLMQueryParams) -> str:
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


_cerebras_client = Cerebras(api_key=os.getenv("CEREBRAS_API_KEY"))


def query_cerebras_qwen3_32b(params: LLMQueryParams) -> str:
    """Query Cerebras API with Qwen 3 32B model."""
    response = _cerebras_client.chat.completions.create(
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
    """Query Cerebras API with Qwen 3 235B Instruct model."""
    response = _cerebras_client.chat.completions.create(
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
    """Query Cerebras API with Qwen 3 235B Thinking model."""
    response = _cerebras_client.chat.completions.create(
        model="qwen-3-235b-a22b-thinking-2507",
        messages=[
            {"role": "system", "content": params.system_instruction},
            {"role": "user", "content": params.content},
        ],
        temperature=params.temperature,
        max_tokens=params.max_tokens,
    )
    return response.choices[0].message.content.strip()


_support_LLM_api_query_func = {
    "deepseek-reasoner": query_deepseek_reasoner,
    "deepseek-chat": query_deepseek_chat,
    "gemini-2.0-flash": query_gemini_2_0_flash,
    "qwen3-plus": query_qwen3_plus,
    "qwen3-max": query_qwen3_max,
    "Cerebras:Qwen-3-32B": query_cerebras_qwen3_32b,
    "Cerebras:Qwen-3-235B-Instruct": query_cerebras_qwen3_235b_instruct,
    "Cerebras:Qwen-3-235B-Thinking": query_cerebras_qwen3_235b_thinking,
}

if LOCAL_LLM_ENABLED:
    local_qwen2_5_model_name = "Qwen/Qwen2.5-1.5B-Instruct"
    logger.info(f"Loading local model: {local_qwen2_5_model_name} ... This may take a while.")
    local_qwen2_5tokenizer = AutoTokenizer.from_pretrained(local_qwen2_5_model_name)
    local_qwen2_5model = AutoModelForCausalLM.from_pretrained(
        local_qwen2_5_model_name,
        device_map="auto",
        dtype="auto"
    )


    def query_local_qwen2_5(params: LLMQueryParams) -> str:
        pipe = pipeline("text-generation", model=local_qwen2_5model, tokenizer=local_qwen2_5tokenizer)
        messages = [
            {"role": "system", "content": params.system_instruction},
            {"role": "user", "content": params.content},
        ]
        out = pipe(messages, temperature=params.temperature, max_new_tokens=params.max_tokens, do_sample=True)
        return out[0]['generated_text'][-1]['content'].strip()


    _support_LLM_api_query_func["local:Qwen/Qwen2.5-1.5B-Instruct"] = query_local_qwen2_5


def query_llm(params: LLMQueryParams) -> str:
    """Query the LLM based on the specified API server."""
    query_api = params.api_server
    if query_api not in _support_LLM_api_query_func:
        raise Exception(f"Unsupported API server: {query_api}")
    return _support_LLM_api_query_func[query_api](params)
