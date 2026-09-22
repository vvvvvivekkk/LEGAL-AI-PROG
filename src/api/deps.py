"""Shared API dependencies.

Everything the routes need from the pipeline is provided through these
functions so tests can override them (FastAPI dependency_overrides) with fakes
— a hashing embedder, a stub LLM adapter, a rule-based NLI — and run fast and
offline without downloading models or needing an API key.
"""

from __future__ import annotations

import os
from functools import lru_cache

from src.embedding.base import EmbeddingModel
from src.chat.store import DEFAULT_CHATS_DIR, ChatStore
from src.indexing.build import DEFAULT_DB_PATH


class ApiState:
    """Process-wide, overridable settings (the LanceDB location).

    chats_dir holds the Ask page's conversation history -- separate from the
    document index, which is rebuilt whenever the corpus changes.

    LEGAL_AI_DB_PATH points the API at a different index without touching the
    default one -- used by scripts/batch_ask_check.py so a batch run gets a
    clean, isolated corpus.
    """

    db_path: str = os.environ.get("LEGAL_AI_DB_PATH") or DEFAULT_DB_PATH
    chats_dir: str = os.environ.get("LEGAL_AI_CHATS_DIR") or str(DEFAULT_CHATS_DIR)


def get_db_path() -> str:
    return ApiState.db_path


def get_chat_store() -> ChatStore:
    return ChatStore(ApiState.chats_dir)


@lru_cache(maxsize=4)
def _cached_embedder(model_marker: str) -> EmbeddingModel:
    from src.embedding.sentence_transformer import SentenceTransformerEmbedder

    return SentenceTransformerEmbedder()


def get_embedder() -> EmbeddingModel:
    """Default embedding backend (cached). Overridden with a fake in tests.

    Constructing the backend can fail before any request work happens (e.g.
    sentence-transformers not installed). Surface that as a 503 with the real
    reason instead of an unhandled dependency error.
    """
    try:
        return _cached_embedder("default")
    except Exception as exc:  # noqa: BLE001
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail=f"embedding model unavailable: {type(exc).__name__}: {exc}",
        ) from exc


# The reranker / LLM adapter / NLI model are heavy and only some routes use
# them. They're exposed as zero-arg factories so a route resolves them lazily
# (inside the handler, only when actually needed) rather than on every request
# — FastAPI otherwise resolves declared dependencies eagerly. Tests override
# these factories to return fakes.

def get_reranker_factory():
    def _make():
        from src.retrieval.rerank import CrossEncoderReranker

        return CrossEncoderReranker()

    return _make


def get_adapter_factory():
    def _make():
        from src.generation.factory import get_adapter as _factory

        return _factory()

    return _make


def get_nli_factory():
    def _make():
        from src.verification.nli import RobertaMNLI

        return RobertaMNLI()

    return _make
