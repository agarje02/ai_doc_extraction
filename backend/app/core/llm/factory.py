"""Build an ``LLMProvider`` from settings."""
from __future__ import annotations

from app.config import Settings, get_settings

from .base import LLMError, LLMProvider
from .mock_provider import MockProvider


def build_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    provider = settings.llm_provider.lower().strip()

    if provider == "mock":
        return MockProvider()
    if provider == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(settings.openai_api_key)
    if provider == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(settings.anthropic_api_key)
    if provider == "ollama":
        from .ollama_provider import OllamaProvider

        return OllamaProvider(settings.ollama_base_url)

    raise LLMError(
        f"Unknown LLM_PROVIDER {provider!r}. "
        "Expected one of: mock, openai, anthropic, ollama."
    )
