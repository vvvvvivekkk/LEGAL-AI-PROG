"""Select an LLM adapter from environment configuration.

The pipeline calls get_adapter() and never names a provider itself. Which
backend is used is decided entirely by env vars:

    LLM_PROVIDER     one of: claude, openai, gemini, groq   (default: claude)
    LLM_API_KEY      the provider API key (claude / openai / groq)
    GEMINI_API_KEY   the Google AI Studio key (gemini)
    GROQ_API_KEY     the Groq key (groq); LLM_API_KEY is used if it is unset
    LLM_MODEL        optional model id; each adapter has its own default

These are read from the environment, or from the repo-root `.env` file (see
`.env.example`) via src.config. Real keys are a deployment/runtime concern —
tests inject StubAdapter directly rather than going through this factory.
"""

from __future__ import annotations

from src.config import env
from src.generation.base import LLMAdapter

_PROVIDERS = ("claude", "openai", "gemini", "groq")


def get_adapter(
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> LLMAdapter:
    provider = (provider or env("LLM_PROVIDER") or "claude").lower()
    model = model or env("LLM_MODEL")
    model_kw = {"model": model} if model else {}

    if provider == "claude":
        from src.generation.adapters.claude import ClaudeAdapter

        return ClaudeAdapter(api_key=api_key or env("LLM_API_KEY"), **model_kw)
    if provider == "openai":
        from src.generation.adapters.openai import OpenAIAdapter

        return OpenAIAdapter(api_key=api_key or env("LLM_API_KEY"), **model_kw)
    if provider == "gemini":
        from src.generation.adapters.gemini import GeminiAdapter

        return GeminiAdapter(api_key=api_key or env("GEMINI_API_KEY"), **model_kw)
    if provider == "groq":
        from src.generation.adapters.groq import GroqAdapter

        return GroqAdapter(
            api_key=api_key or env("GROQ_API_KEY") or env("LLM_API_KEY"), **model_kw
        )

    raise ValueError(f"Unknown LLM_PROVIDER {provider!r}; expected one of {_PROVIDERS}")


# Which env var supplies each provider's key. The first name is the provider's
# own variable; the generic LLM_API_KEY is accepted as a fallback for the
# providers that have no separate key of their own historically.
PROVIDER_KEY_ENV: dict[str, tuple[str, ...]] = {
    "claude": ("LLM_API_KEY",),
    "openai": ("LLM_API_KEY",),
    "gemini": ("GEMINI_API_KEY",),
    "groq": ("GROQ_API_KEY", "LLM_API_KEY"),
}


def selected_provider() -> str:
    return (env("LLM_PROVIDER") or "claude").lower()


def missing_key_message(provider: str | None = None) -> str | None:
    """Why the selected provider is unusable, or None if its key is present.

    Checked at startup so a misnamed or absent key is obvious immediately,
    rather than surfacing as a 503 on the first question somebody asks.
    """
    provider = (provider or selected_provider()).lower()
    if provider not in _PROVIDERS:
        return (
            f"LLM_PROVIDER is {provider!r}, which is not one of {', '.join(_PROVIDERS)}."
        )
    names = PROVIDER_KEY_ENV[provider]
    if any(env(name) for name in names):
        return None
    expected = names[0] if len(names) == 1 else f"{names[0]} (or {names[1]})"
    return (
        f"LLM_PROVIDER={provider} but no API key is set. "
        f"Expected the environment variable {expected}, in the repo-root .env or the "
        f"real environment. Note .env is read once at process start -- restart the "
        f"server after editing it."
    )
