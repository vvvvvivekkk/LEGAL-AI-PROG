"""Select an LLM adapter from environment configuration.

The pipeline calls get_adapter() and never names a provider itself. Which
backend is used is decided entirely by env vars:

    LLM_PROVIDER   one of: claude, openai   (default: claude)
    LLM_API_KEY    the provider API key

Real keys are a deployment/runtime concern — tests inject StubAdapter directly
rather than going through this factory.
"""

from __future__ import annotations

import os

from src.generation.base import LLMAdapter

_PROVIDERS = ("claude", "openai")


def get_adapter(provider: str | None = None, api_key: str | None = None) -> LLMAdapter:
    provider = (provider or os.environ.get("LLM_PROVIDER") or "claude").lower()
    api_key = api_key or os.environ.get("LLM_API_KEY")

    if provider == "claude":
        from src.generation.adapters.claude import ClaudeAdapter

        return ClaudeAdapter(api_key=api_key)
    if provider == "openai":
        from src.generation.adapters.openai import OpenAIAdapter

        return OpenAIAdapter(api_key=api_key)

    raise ValueError(f"Unknown LLM_PROVIDER {provider!r}; expected one of {_PROVIDERS}")
