import os
import requests
from openai import OpenAI  # used for OpenRouter via base_url
from typing import List, Dict, Any
from .utils import retry_with_backoff

class LLMClient:
    """Abstract base for LLM API calls with retries."""
    @retry_with_backoff(max_retries=5, base_delay=1.0)
    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
        raise NotImplementedError

class OpenRouterClient(LLMClient):
    def __init__(self, model: str = "openai/gpt-oss-120b:free"):
        api_key = os.environ.get("OPENROUTER_API_KEY")
        # api_key = ""
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model = model

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

def get_client(provider: str, model: str = None) -> LLMClient:
    provider = provider.lower()
    if provider in ("openrouter", "open_router"):
        return OpenRouterClient(model=model or "openai/gpt-oss-120b:free")
    else:
        raise ValueError(f"Unsupported provider: {provider}")