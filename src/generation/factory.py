"""Select an LLM adapter from environment configuration.

The pipeline calls get_adapter() and never names a provider itself. Which
backend is used is decided entirely by env vars:

    LLM_PROVIDER   one of: claude, openai   (default: claude)
    LLM_API_KEY    the provider API key
    LLM_MODEL      optional model id; each adapter has its own default

These are read from the environment, or from the repo-root `.env` file (see
`.env.example`) via src.config. Real keys are a deployment/runtime concern —
tests inject StubAdapter directly rather than going through this factory.
"""

from __future__ import annotations

from src.config import env
from src.generation.base import LLMAdapter

_PROVIDERS = ("claude", "openai")


def get_adapter(
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> LLMAdapter:
    provider = (provider or env("LLM_PROVIDER") or "claude").lower()
    api_key = api_key or env("LLM_API_KEY")
    model = model or env("LLM_MODEL")

    if provider == "claude":
        from src.generation.adapters.claude import ClaudeAdapter

        return ClaudeAdapter(api_key=api_key, **({"model": model} if model else {}))
    if provider == "openai":
        from src.generation.adapters.openai import OpenAIAdapter

        return OpenAIAdapter(api_key=api_key, **({"model": model} if model else {}))

    raise ValueError(f"Unknown LLM_PROVIDER {provider!r}; expected one of {_PROVIDERS}")
