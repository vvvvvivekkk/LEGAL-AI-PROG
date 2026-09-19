"""Stub LLM adapter for tests and offline development.

No network, no API key. Either returns a fixed canned response, or delegates
to a supplied function of (system, user) so a test can assert on the exact
prompt the pipeline built.
"""

from __future__ import annotations

from typing import Callable


class StubAdapter:
    def __init__(
        self,
        response: str | None = None,
        responder: Callable[[str, str], str] | None = None,
    ):
        if response is None and responder is None:
            raise ValueError("StubAdapter needs either a response or a responder")
        self._response = response
        self._responder = responder
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if self._responder is not None:
            return self._responder(system, user)
        return self._response  # type: ignore[return-value]
