"""Retrieval stage: fetch → (rerank) → truncate to top-k context.

Wraps the phase-2 query helpers (src/indexing/query.py) and adds optional
cross-encoder reranking on the fused top-N. Behaviour is driven entirely by
RetrievalConfig so the same object can serve dense-only / hybrid / no-rerank
ablations by swapping the config.
"""

from __future__ import annotations

from lancedb.table import Table

from src.embedding.base import EmbeddingModel
from src.embedding.sentence_transformer import SentenceTransformerEmbedder
from src.indexing.query import search_dense, search_fts, search_hybrid
from src.retrieval.config import RetrievalConfig
from src.retrieval.rerank import CrossEncoderReranker, Reranker


class Retriever:
    def __init__(
        self,
        table: Table,
        config: RetrievalConfig | None = None,
        embedder: EmbeddingModel | None = None,
        reranker: Reranker | None = None,
    ):
        self.table = table
        self.config = config or RetrievalConfig()
        self.embedder = embedder or SentenceTransformerEmbedder()
        # Only build the (heavy) cross-encoder if reranking is actually on and
        # the caller didn't inject one.
        self._reranker = reranker
        if self.config.use_reranker and self._reranker is None:
            self._reranker = CrossEncoderReranker(self.config.reranker_model)

    def _fetch(self, query: str, limit: int) -> list[dict]:
        mode = self.config.mode
        if mode == "dense":
            return search_dense(self.table, query, k=limit, embedder=self.embedder)
        if mode == "fts":
            return search_fts(self.table, query, k=limit)
        return search_hybrid(self.table, query, k=limit, embedder=self.embedder)

    def retrieve(self, query: str) -> list[dict]:
        """Return the ranked, reranked top-k context rows for a query.

        With reranking on, N candidates are fetched, re-scored, and truncated
        to k. With it off, k are fetched directly.
        """
        cfg = self.config
        fetch_n = cfg.n if cfg.use_reranker else cfg.k
        candidates = self._fetch(query, fetch_n)

        if cfg.use_reranker and self._reranker is not None:
            candidates = self._reranker.rerank(query, candidates)

        return candidates[: cfg.k]
