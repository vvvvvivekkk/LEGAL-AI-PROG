"""chat_model_from_env must build every provider's model without a network call."""

from __future__ import annotations

import pytest

from lc import generation
from lc.generation import chat_model_from_env


@pytest.mark.parametrize("provider", ["claude", "openai", "gemini", "groq"])
def test_each_provider_constructs(monkeypatch, provider):
    keys = {"LLM_API_KEY": "test-key", "GEMINI_API_KEY": "test-key", "GROQ_API_KEY": "test-key"}
    monkeypatch.setattr(generation, "env", lambda name, default=None: keys.get(name, default))
    assert chat_model_from_env(provider) is not None


def test_groq_uses_the_api_default_temperature(monkeypatch):
    monkeypatch.setattr(generation, "env", lambda name, default=None: "test-key" if "KEY" in name else default)
    assert chat_model_from_env("groq").temperature == 1.0
