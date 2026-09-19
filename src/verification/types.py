"""Shared types for the V1-V6 verification chain.

Kept in one place so every layer speaks the same vocabulary (verdict labels,
per-claim result records) and the Proof Object (V6) can serialize them
uniformly.
"""

from __future__ import annotations

import re
from enum import Enum


class Entailment(str, Enum):
    ENTAILS = "ENTAILS"
    CONTRADICTS = "CONTRADICTS"
    NEUTRAL = "NEUTRAL"


def context_text_by_id(context_chunks: list[dict]) -> dict[str, str]:
    """Map chunk_id -> chunk text for the retrieved context."""
    return {c["chunk_id"]: c.get("text", "") for c in context_chunks}


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def token_jaccard(a: str, b: str) -> float:
    """Token-set Jaccard similarity, used for claim matching / span selection."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)
