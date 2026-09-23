"""Injectable dependencies for the LangChain API (same names as src/api/deps.py).

Tests override these with FastAPI dependency_overrides exactly as they do for
src/, and may hand in either LangChain objects or src/-style duck-typed ones
(embed(), rerank(), complete(), classify()); the pipeline adapts both.
"""

from __future__ import annotations

import os

from src.chat.store import ChatStore

# Its own index and chat history, so the experiment never touches src/'s.
DEFAULT_DB_PATH = "data/lancedb_lc"
DEFAULT_CHATS_DIR = "data/chats_lc"


class ApiState:
    db_path: str = os.environ.get("LEGAL_AI_LC_DB_PATH") or DEFAULT_DB_PATH
    chats_dir: str = os.environ.get("LEGAL_AI_LC_CHATS_DIR") or DEFAULT_CHATS_DIR


def get_db_path() -> str:
    return ApiState.db_path


def get_chat_store() -> ChatStore:
    return ChatStore(ApiState.chats_dir)


def get_embedder():
    try:
        from lc.embeddings import default_embeddings

        return default_embeddings()
    except Exception as exc:  # noqa: BLE001
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail=f"embedding model unavailable: {type(exc).__name__}: {exc}",
        ) from exc


# Heavy models are handed out as zero-arg factories so a route builds them only
# when it needs them (FastAPI resolves declared dependencies eagerly).

def get_reranker_factory():
    def _make():
        from lc.retrieval import default_cross_encoder_compressor

        return default_cross_encoder_compressor()

    return _make


def get_adapter_factory():
    def _make():
        from lc.generation import chat_model_from_env

        return chat_model_from_env()

    return _make


def get_nli_factory():
    def _make():
        from src.verification.nli import RobertaMNLI

        return RobertaMNLI()

    return _make
