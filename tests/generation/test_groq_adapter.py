"""GroqAdapter: prompt wiring and factory selection, with a stub client so no
network call or real key is needed."""

from __future__ import annotations

import pytest

from src.generation import factory
from src.generation.adapters.groq import (
    BASE_URL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    GroqAdapter,
)


class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Response:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _StubCompletions:
    def __init__(self, content):
        self.content = content
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _Response(self.content)


class StubClient:
    def __init__(self, content="The statute addresses the question [c1]."):
        self.chat = type("_Chat", (), {"completions": _StubCompletions(content)})()

    @property
    def calls(self):
        return self.chat.completions.calls


def test_complete_passes_system_and_user_through():
    client = StubClient()
    adapter = GroqAdapter(client=client)
    out = adapter.complete("You must cite sources.", "What is the deposit period?")

    assert out == "The statute addresses the question [c1]."
    (call,) = client.calls
    assert call["model"] == DEFAULT_MODEL
    assert call["max_tokens"] == DEFAULT_MAX_TOKENS
    assert call["messages"] == [
        {"role": "system", "content": "You must cite sources."},
        {"role": "user", "content": "What is the deposit period?"},
    ]


def test_default_model_is_set():
    """Groq's catalogue is per-account, so the default is whatever this key can
    actually serve — llama-3.3-70b-versatile 404s on some keys."""
    assert DEFAULT_MODEL


def test_points_at_the_groq_openai_compatible_endpoint():
    assert BASE_URL == "https://api.groq.com/openai/v1"


def test_token_budget_leaves_room_for_a_cited_answer():
    """A reply cut off mid-citation reads downstream as an unsupported claim."""
    assert DEFAULT_MAX_TOKENS >= 4096


def test_empty_response_content_becomes_empty_string():
    adapter = GroqAdapter(client=StubClient(content=None))
    assert adapter.complete("sys", "user") == ""


def test_model_override_is_passed_to_the_client():
    client = StubClient()
    GroqAdapter(client=client, model="llama-3.1-8b-instant").complete("sys", "user")
    assert client.calls[0]["model"] == "llama-3.1-8b-instant"


def test_missing_key_raises_rather_than_failing_at_call_time(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        GroqAdapter()


def test_key_is_read_from_the_environment(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    assert GroqAdapter().api_key == "gsk-test"


def test_generic_llm_api_key_is_accepted_as_a_fallback(monkeypatch):
    """The other adapters use LLM_API_KEY, so a .env written for them works."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "gsk-generic")
    assert GroqAdapter().api_key == "gsk-generic"


def test_specific_key_wins_over_the_generic_one(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk-specific")
    monkeypatch.setenv("LLM_API_KEY", "gsk-generic")
    assert GroqAdapter().api_key == "gsk-specific"


def test_factory_selects_groq_from_the_provider_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    adapter = factory.get_adapter()
    assert isinstance(adapter, GroqAdapter)
    assert adapter.model == DEFAULT_MODEL


def test_factory_passes_a_model_override_through(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    monkeypatch.setenv("LLM_MODEL", "llama-3.1-8b-instant")

    assert factory.get_adapter().model == "llama-3.1-8b-instant"


def test_groq_is_listed_as_a_valid_provider():
    assert "groq" in factory._PROVIDERS


# ---------------------------------------------------------------------------
# Startup configuration check
# ---------------------------------------------------------------------------

def test_missing_key_message_names_the_exact_env_var(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    problem = factory.missing_key_message()
    assert problem is not None
    assert "GROQ_API_KEY" in problem
    assert "LLM_API_KEY" in problem
    assert "restart" in problem.lower()


def test_missing_key_message_is_none_when_configured(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    assert factory.missing_key_message() is None


def test_gemini_needs_its_own_key_not_the_generic_one(monkeypatch):
    """GEMINI_API_KEY has no LLM_API_KEY fallback — the message must say so."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "not-a-gemini-key")

    problem = factory.missing_key_message()
    assert problem is not None and "GEMINI_API_KEY" in problem


def test_unknown_provider_is_reported(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "notaprovider")
    problem = factory.missing_key_message()
    assert problem is not None and "notaprovider" in problem


def test_health_reports_llm_configuration(monkeypatch):
    from fastapi.testclient import TestClient

    from src.api.main import app

    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with TestClient(app) as client:
        body = client.get("/health").json()

    assert body["status"] == "ok"
    assert body["llm"]["provider"] == "groq"
    assert body["llm"]["configured"] is False
    assert "GROQ_API_KEY" in body["llm"]["problem"]
