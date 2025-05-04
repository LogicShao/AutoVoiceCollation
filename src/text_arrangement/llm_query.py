import os

import requests
from google import genai
from google.genai import types


class LLMQueryParams:
    def __init__(self, content: str, system_instruction: str = None, temperature: float = 0.7, max_tokens: int = 100):
        self.content = content
        self.system_instruction = system_instruction or "You are a helpful assistant."  # Default system instruction
        self.temperature = temperature
        self.max_tokens = max_tokens


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
    return response.text
