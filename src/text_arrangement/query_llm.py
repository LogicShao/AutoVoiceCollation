import os
from dataclasses import dataclass

import requests
from google import genai
from google.genai import types


@dataclass
class LLMQueryParams:
    content: str
    system_instruction: str = "You are a helpful assistant."
    temperature: float = 0.7
    max_tokens: int = 1000
    top_k: int = 100
    top_p: float = 0.9
    api_server: str = "gemini"  # Default to Gemini, can be overridden


def query_deepseek(params: LLMQueryParams) -> str:
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


_gemini_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))


def query_gemini(params: LLMQueryParams) -> str:
    """Query the Gemini API with a parameter object."""
    response = _gemini_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=params.content,
        config=types.GenerateContentConfig(
            temperature=params.temperature,
            max_output_tokens=params.max_tokens,
            system_instruction=params.system_instruction,
        ),
    )
    return response.text.strip()


def query_llm(params: LLMQueryParams) -> str:
    """Query the LLM based on the specified API server."""
    if params.api_server.lower() == 'deepseek':
        return query_deepseek(params)
    elif params.api_server.lower() == 'gemini':
        return query_gemini(params)
    else:
        raise ValueError(f"Unsupported API server: {params.api_server}")
