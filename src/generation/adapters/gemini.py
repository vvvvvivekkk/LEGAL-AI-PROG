"""Google Gemini adapter.

Wired in purely by supplying an API key -- no pipeline code changes. The
google-genai SDK is imported lazily so the package is only required when this
adapter is actually used. Defaults to the Flash tier: fast and cheap, which
suits a pipeline that may resample generations for self-consistency (V4).
"""

from __future__ import annotations

import os

DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiAdapter:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 1024,
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
        from google.genai import types

        response = self._get_client().models.generate_content(
            model=self.model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=self.max_tokens,
            ),
        )
        # `.text` is None when the response carried no text part (e.g. blocked).
        return response.text or ""
