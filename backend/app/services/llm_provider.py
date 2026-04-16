"""LLM provider abstraction: OpenAI and OpenRouter (OpenAI-compatible API)."""
from openai import AsyncOpenAI

from app.core.config import settings


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_llm_client(provider: str, api_key: str | None) -> AsyncOpenAI:
    """
    Return AsyncOpenAI client for the given provider.
    For openrouter, uses OPENROUTER_BASE_URL and api_key (OPENROUTER_API_KEY).
    For openai, uses default base URL and api_key (OPENAI_API_KEY).
    """
    if provider == "openrouter":
        key = api_key or settings.OPENROUTER_API_KEY
        return AsyncOpenAI(api_key=key or "dummy", base_url=OPENROUTER_BASE_URL)
    key = api_key or settings.OPENAI_API_KEY
    return AsyncOpenAI(api_key=key or "dummy")


def get_default_model(provider: str) -> str:
    """Default model name for the provider."""
    if provider == "openrouter":
        return "openai/gpt-4o-mini"
    return "gpt-4o-mini"
