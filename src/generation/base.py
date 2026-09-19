"""Thin, provider-agnostic LLM interface.

Every backend implements `complete(system, user) -> str`. The pipeline depends
only on this interface, never on a concrete provider — Claude / GPT / Llama /
Gemini are selected at the edge (src/generation/factory.py) via env vars, so
swapping providers is a config change, not a code change.
"""

from __future__ import annotations

from typing import Protocol


class LLMAdapter(Protocol):
    """Anything that can turn a (system, user) prompt pair into text."""

    def complete(self, system: str, user: str) -> str:
        ...
