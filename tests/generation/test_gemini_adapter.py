"""GeminiAdapter: prompt wiring and factory selection, with a stub client so
no network call or real key is needed."""

from __future__ import annotations

import pytest

from src.generation import factory
from src.generation.adapters.gemini import DEFAULT_MAX_TOKENS, DEFAULT_MODEL, GeminiAdapter


class _Response:
    def __init__(self, text):
        self.text = text


class _StubModels:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        return _Response(self.text)


class StubClient:
    def __init__(self, text="The statute addresses the question [c1]."):
        self.models = _StubModels(text)


def test_complete_passes_system_and_user_through():
    client = StubClient()
    adapter = GeminiAdapter(client=client)
    out = adapter.complete("You must cite sources.", "What is the deposit period?")

    assert out == "The statute addresses the question [c1]."
    (call,) = client.models.calls
    assert call["model"] == DEFAULT_MODEL
    assert call["contents"] == "What is the deposit period?"
    assert call["config"].system_instruction == "You must cite sources."
    assert call["config"].max_output_tokens == DEFAULT_MAX_TOKENS


def test_default_model_is_flash_tier():
    assert "flash" in DEFAULT_MODEL


def test_empty_response_text_becomes_empty_string():
    adapter = GeminiAdapter(client=StubClient(text=None))
    assert adapter.complete("s", "u") == ""


def test_requires_key_when_no_client_is_injected(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiAdapter()


def test_key_comes_from_gemini_api_key_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    adapter = GeminiAdapter()
    assert adapter.api_key == "g-key"


def test_factory_selects_gemini(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    monkeypatch.setenv("LLM_MODEL", "gemini-2.5-flash-lite")
    adapter = factory.get_adapter()
    assert isinstance(adapter, GeminiAdapter)
    assert adapter.api_key == "g-key"
    assert adapter.model == "gemini-2.5-flash-lite"


def test_default_token_budget_leaves_room_for_reasoning():
    """2.5-series reasoning tokens come out of max_output_tokens before any
    answer text, so a small budget truncates the answer mid-citation and the
    citation parser sees no supported claims. Keep headroom.
    """
    assert DEFAULT_MAX_TOKENS >= 4096
