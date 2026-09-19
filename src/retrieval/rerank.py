"""Cross-encoder reranking.

Bi-encoder retrieval (dense/FTS/hybrid) is recall-oriented and cheap; a
cross-encoder re-scores each (query, passage) pair jointly and is far more
precise, so we apply it to the fused top-N candidates before truncating to
top-k. The reranker is behind a thin interface (`Reranker`) so a different
model — or a stub in tests — can be swapped in without touching the retriever.
"""

from __future__ import annotations

from typing import Protocol

from src.retrieval.config import DEFAULT_RERANKER_MODEL


class Reranker(Protocol):
    """Anything that can reorder candidate rows for a query."""

    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        ...


def _passage_text(row: dict) -> str:
    """The text scored by the reranker: contextual summary + chunk text.

    Mirrors the SAC embedding input (src/indexing/build.py) so the reranker
    sees the same context the dense retriever encoded.
    """
    summary = row.get("contextual_summary", "") or ""
    text = row.get("text", "") or ""
    return f"{summary}\n{text}".strip()


_model_cache: dict = {}


def _get_cross_encoder(model_name: str):
    if model_name not in _model_cache:
        from sentence_transformers import CrossEncoder

        _model_cache[model_name] = CrossEncoder(model_name)
    return _model_cache[model_name]


class CrossEncoderReranker:
    """Reranker backed by a sentence-transformers CrossEncoder (default: BGE)."""

    def __init__(self, model_name: str = DEFAULT_RERANKER_MODEL):
        self.model_name = model_name

    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        if not candidates:
            return []
        model = _get_cross_encoder(self.model_name)
        pairs = [[query, _passage_text(row)] for row in candidates]
        scores = model.predict(pairs)
        ranked = sorted(
            zip(candidates, scores),
            key=lambda pair: float(pair[1]),
            reverse=True,
        )
        out: list[dict] = []
        for row, score in ranked:
            row = dict(row)
            row["rerank_score"] = float(score)
            out.append(row)
        return out
