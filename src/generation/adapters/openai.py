"""OpenAI adapter.

Wired in purely by supplying an API key — no pipeline code changes. The
openai SDK is imported lazily so the package is only required when this
adapter is actually used.
"""

from __future__ import annotations

import os

DEFAULT_MODEL = "gpt-4o"


class OpenAIAdapter:
    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL, max_tokens: int = 1024):
        self.api_key = api_key or os.environ.get("LLM_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAIAdapter requires an API key (LLM_API_KEY env var or api_key arg)")
        self.model = model
        self.max_tokens = max_tokens

    def complete(self, system: str, user: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""
