"""Groq adapter.

Groq serves open models (Llama and friends) behind an OpenAI-compatible
endpoint, so the `openai` SDK is reused with a different base URL rather than
pulling in a second client library. The SDK is imported lazily, so the package
is only required when this adapter is actually used.

Selected with LLM_PROVIDER=groq; the key comes from GROQ_API_KEY.
"""

from __future__ import annotations

import os

BASE_URL = "https://api.groq.com/openai/v1"

# Groq's catalogue varies by account. llama-3.3-70b-versatile is the obvious
# default but is not available on every key (404 model_not_found), so the
# default is a model this account can actually serve. Override with LLM_MODEL,
# and see `GroqAdapter.available_models()` for what a key can reach.
DEFAULT_MODEL = "openai/gpt-oss-120b"

# Citation-forced answers over a dozen retrieved chunks routinely run past a
# 1024-token reply, and a response cut off mid-citation is read downstream as
# an unsupported claim rather than a truncation.
DEFAULT_MAX_TOKENS = 4096


class GroqAdapter:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        client=None,
    ):
        # GROQ_API_KEY is the specific name; LLM_API_KEY is the generic one the
        # other adapters use, accepted so switching provider needs one edit.
        self.api_key = api_key or os.environ.get("GROQ_API_KEY") or os.environ.get("LLM_API_KEY")
        if not self.api_key and client is None:
            raise ValueError(
                "GroqAdapter requires an API key: set GROQ_API_KEY (or LLM_API_KEY) "
                "in the repo-root .env or the environment, then restart the server."
            )
        self.model = model
        self.max_tokens = max_tokens
        # A pre-built client can be injected (tests pass a stub); otherwise one
        # is created from the key on first use.
        self._client = client

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self.api_key, base_url=BASE_URL)
        return self._client

    def complete(self, system: str, user: str) -> str:
        response = self._get_client().chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        # `.content` is None when the response carried no text (e.g. filtered).
        return response.choices[0].message.content or ""

    def available_models(self) -> list[str]:
        """Model ids this key can actually reach — Groq's catalogue is per-account."""
        return sorted(m.id for m in self._get_client().models.list().data)
