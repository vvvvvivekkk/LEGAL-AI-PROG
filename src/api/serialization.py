"""Turn internal pipeline row/record objects into JSON-safe API payloads.

The LanceDB query helpers return rows that include the raw embedding vector and
backend-specific score columns (_distance / _relevance_score). The API strips
the vector (large, not useful to the UI) and normalises the score into a single
optional field.
"""

from __future__ import annotations

# rerank_score first: if a row was cross-encoder reranked, that score is the
# authoritative one, even though the row still carries the upstream hybrid score.
_SCORE_KEYS = ("rerank_score", "_relevance_score", "_distance", "_score")


def chunk_row(row: dict) -> dict:
    """Serialize a retrieval result row for the API."""
    score = None
    score_kind = None
    for key in _SCORE_KEYS:
        if key in row and row[key] is not None:
            score = float(row[key])
            score_kind = key.lstrip("_")
            break
    return {
        "chunk_id": row.get("chunk_id"),
        "text": row.get("text"),
        "contextual_summary": row.get("contextual_summary"),
        "metadata": row.get("metadata") or {},
        "score": score,
        "score_kind": score_kind,
    }


def chunk_rows(rows: list[dict]) -> list[dict]:
    return [chunk_row(r) for r in rows]


def new_chunk(chunk_dict: dict) -> dict:
    """Serialize a freshly-ingested chunk record (from ChunkRecord.to_dict())."""
    return {
        "chunk_id": chunk_dict["chunk_id"],
        "text": chunk_dict["text"],
        "contextual_summary": chunk_dict["contextual_summary"],
        "metadata": chunk_dict.get("metadata") or {},
    }
