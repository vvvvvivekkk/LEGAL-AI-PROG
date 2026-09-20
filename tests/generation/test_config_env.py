"""`.env` loading: values fill in missing env vars but never override set ones,
and the factory picks up LLM_MODEL."""

from __future__ import annotations

import src.config as config
from src.generation import factory


def _use_env_file(monkeypatch, tmp_path, text):
    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(config, "ENV_FILE", path)
    monkeypatch.setattr(config, "_loaded", False)
    return path


def test_env_file_fills_unset_vars(monkeypatch, tmp_path):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    _use_env_file(monkeypatch, tmp_path, "LLM_PROVIDER=openai\n")
    assert config.env("LLM_PROVIDER") == "openai"


def test_real_env_wins_over_file(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "claude")
    _use_env_file(monkeypatch, tmp_path, "LLM_PROVIDER=openai\n")
    assert config.env("LLM_PROVIDER") == "claude"


def test_empty_value_counts_as_unset(monkeypatch, tmp_path):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    _use_env_file(monkeypatch, tmp_path, "LLM_API_KEY=\n")
    assert config.env("LLM_API_KEY") is None
    assert config.env("LLM_API_KEY", "fallback") == "fallback"


def test_factory_reads_model_from_env_file(monkeypatch, tmp_path):
    for name in ("LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(name, raising=False)
    _use_env_file(monkeypatch, tmp_path, "LLM_PROVIDER=claude\nLLM_API_KEY=test-key\nLLM_MODEL=claude-opus-5\n")
    adapter = factory.get_adapter()
    assert type(adapter).__name__ == "ClaudeAdapter"
    assert adapter.api_key == "test-key"
    assert adapter.model == "claude-opus-5"


def test_missing_env_file_is_fine(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ENV_FILE", tmp_path / "absent.env")
    monkeypatch.setattr(config, "_loaded", False)
    assert config.load_env() is None
