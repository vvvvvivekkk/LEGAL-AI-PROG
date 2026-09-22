"""Query helpers: dense-only, FTS-only, and hybrid (RRF-fused) search over a
LanceDB chunks table, for comparison (feeds the Retrieval UI page and the
retrieval ablation in later phases).
"""

from __future__ import annotations

import json

from lancedb.table import Table

from src.embedding.base import EmbeddingModel
from src.embedding.sentence_transformer import SentenceTransformerEmbedder


def row_to_dict(row: dict) -> dict:
    """Normalise a raw LanceDB row: decode the JSON metadata column."""
    row = dict(row)
    metadata = row.get("metadata")
    if isinstance(metadata, str):
        try:
            row["metadata"] = json.loads(metadata)
        except json.JSONDecodeError:
            pass
    return row


# Kept as the original private spelling for existing call sites.
_row_to_dict = row_to_dict


def search_dense(
    table: Table,
    query_text: str,
    k: int = 5,
    embedder: EmbeddingModel | None = None,
) -> list[dict]:
    """Dense-only vector search."""
    embedder = embedder or SentenceTransformerEmbedder()
    vector = embedder.embed([query_text])[0]
    results = table.search(vector).limit(k).to_list()
    return [_row_to_dict(r) for r in results]


def search_fts(table: Table, query_text: str, k: int = 5) -> list[dict]:
    """Full-text (BM25-backed) keyword search. Requires an FTS index on "text"."""
    results = table.search(query_text, query_type="fts").limit(k).to_list()
    return [_row_to_dict(r) for r in results]


def search_hybrid(
    table: Table,
    query_text: str,
    k: int = 5,
    embedder: EmbeddingModel | None = None,
) -> list[dict]:
    """Hybrid search: vector + FTS, fused with LanceDB's default RRF reranker."""
    embedder = embedder or SentenceTransformerEmbedder()
    vector = embedder.embed([query_text])[0]
    results = (
        table.search(query_type="hybrid")
        .vector(vector)
        .text(query_text)
        .limit(k)
        .to_list()
    )
    return [_row_to_dict(r) for r in results]


def compare_search(
    table: Table,
    query_text: str,
    k: int = 5,
    embedder: EmbeddingModel | None = None,
) -> dict[str, list[dict]]:
    """Run dense, FTS, and hybrid search for the same query, side by side."""
    embedder = embedder or SentenceTransformerEmbedder()
    return {
        "dense": search_dense(table, query_text, k, embedder),
        "fts": search_fts(table, query_text, k),
        "hybrid": search_hybrid(table, query_text, k, embedder),
    }
