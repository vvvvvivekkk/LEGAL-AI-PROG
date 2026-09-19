"""Anthropic Claude adapter.

Wired in purely by supplying an API key — no pipeline code changes. The
anthropic SDK is imported lazily so the package is only required when this
adapter is actually used (tests run against the stub adapter instead).
"""

from __future__ import annotations

import os

DEFAULT_MODEL = "claude-sonnet-4-6"


class ClaudeAdapter:
    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL, max_tokens: int = 1024):
        self.api_key = api_key or os.environ.get("LLM_API_KEY")
        if not self.api_key:
            raise ValueError("ClaudeAdapter requires an API key (LLM_API_KEY env var or api_key arg)")
        self.model = model
        self.max_tokens = max_tokens

    def complete(self, system: str, user: str) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        message = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in message.content if block.type == "text")
