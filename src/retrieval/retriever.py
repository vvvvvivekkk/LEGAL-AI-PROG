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
from src.indexing.query import row_to_dict, search_dense, search_fts, search_hybrid
from src.retrieval.config import RetrievalConfig
from src.retrieval.neighbors import expand_with_neighbors
from src.retrieval.rerank import CrossEncoderReranker, Reranker

# Upper bound on how many chunks of one source document a neighbour lookup will
# pull back. Expansion only ever needs a handful of them, but the ordering has
# to be built from the whole document, so this is a safety valve rather than a
# tuning knob.
MAX_SIBLINGS_PER_SOURCE = 20_000


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

    def _fetch_siblings(self, source_id: str) -> list[dict]:
        """Every indexed chunk of one source document, for neighbour lookup.

        Matched on the chunk-id prefix. LIKE treats "_" and "%" as wildcards
        and source ids are filenames, so the SQL predicate may over-match --
        the exact prefix check afterwards is what makes this correct. A table
        that does not support filtered scans (a test double, say) degrades to
        "no neighbours" rather than failing the query.
        """
        prefix = f"{source_id}::"
        escaped = prefix.replace("'", "''")
        try:
            rows = (
                self.table.search()
                .where(f"chunk_id LIKE '{escaped}%'")
                .limit(MAX_SIBLINGS_PER_SOURCE)
                .to_list()
            )
        except Exception:  # noqa: BLE001 - backend/filter support varies
            return []
        return [row_to_dict(r) for r in rows if str(r.get("chunk_id", "")).startswith(prefix)]

    def retrieve(self, query: str) -> list[dict]:
        """Return the ranked, reranked top-k context rows for a query.

        With reranking on, N candidates are fetched, re-scored, and truncated
        to k. With it off, k are fetched directly.

        If neighbour expansion is on (config.neighbor_window > 0), each of the
        selected k chunks then pulls in its adjacent siblings from the same
        document. Expansion runs *after* the truncation to k, so neighbours add
        to the context instead of evicting ranked results: turning expansion on
        never removes a chunk that was retrieved without it.
        """
        cfg = self.config
        fetch_n = cfg.n if cfg.use_reranker else cfg.k
        candidates = self._fetch(query, fetch_n)

        if cfg.use_reranker and self._reranker is not None:
            candidates = self._reranker.rerank(query, candidates)

        context = candidates[: cfg.k]
        if cfg.neighbor_window > 0:
            context = expand_with_neighbors(context, self._fetch_siblings, cfg.neighbor_window)
        return context
