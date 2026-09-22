"""Google Gemini adapter.

Wired in purely by supplying an API key -- no pipeline code changes. The
google-genai SDK is imported lazily so the package is only required when this
adapter is actually used. Defaults to the Flash tier: fast and cheap, which
suits a pipeline that may resample generations for self-consistency (V4).
"""

from __future__ import annotations

import os

DEFAULT_MODEL = "gemini-2.5-flash"

# On the 2.5 models, reasoning tokens are drawn from max_output_tokens before
# any answer text is emitted -- a RAG prompt routinely spends 1-2k tokens
# thinking. A 1024 budget therefore returned finish_reason=MAX_TOKENS with the
# answer cut off mid-citation, which the citation parser then read as "no
# supported claims" and the chain turned into a spurious ABSTAIN.
DEFAULT_MAX_TOKENS = 4096

# The free tier returns 503 UNAVAILABLE under load fairly often. That is
# transient, unlike a 429 quota error, so it is worth a couple of retries.
_RETRY_STATUSES = (503,)
_MAX_RETRIES = 3


class GeminiAdapter:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        client=None,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key and client is None:
            raise ValueError("GeminiAdapter requires an API key (GEMINI_API_KEY env var or api_key arg)")
        self.model = model
        self.max_tokens = max_tokens
        # A pre-built client can be injected (tests pass a stub); otherwise one
        # is created from the key on first use.
        self._client = client

    def _get_client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def complete(self, system: str, user: str) -> str:
        import time

        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=self.max_tokens,
        )
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = self._get_client().models.generate_content(
                    model=self.model, contents=user, config=config
                )
                # `.text` is None when the response carried no text part
                # (e.g. blocked, or the whole budget went to reasoning).
                return response.text or ""
            except Exception as exc:  # noqa: BLE001 - re-raised below if not retryable
                if getattr(exc, "code", None) not in _RETRY_STATUSES:
                    raise
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
        raise last_exc  # type: ignore[misc]
