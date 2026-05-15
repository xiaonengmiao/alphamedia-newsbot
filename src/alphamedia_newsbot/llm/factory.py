from __future__ import annotations

from ..config import Settings
from .base import LLMClient


def build_llm(settings: Settings) -> LLMClient:
    provider = settings.llm_provider
    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        from .anthropic import AnthropicClient

        return AnthropicClient(settings.anthropic_api_key, settings.llm_model)
    if provider == "deepseek":
        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is required when LLM_PROVIDER=deepseek")
        from .deepseek import DeepSeekClient

        return DeepSeekClient(settings.deepseek_api_key, settings.llm_model)
    if provider == "stub":
        from .stub import StubLLMClient

        return StubLLMClient()
    raise ValueError(f"Unsupported LLM_PROVIDER: {provider!r}")
