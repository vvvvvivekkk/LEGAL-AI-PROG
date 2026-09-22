"""Retrieval-only evaluation: Precision / Recall / F1 and Retrieval Rate.

Metrics are computed against a hand-labeled query set (data/eval/
retrieval_queryset.json) whose entries name the chunk ids that are genuinely
relevant to each query. No generation is involved — this measures retrieval
quality in isolation, feeding the phase-6 ablation (dense vs hybrid, rerank
on/off, k/N sweeps).

Definitions (per query, over the top-k retrieved ids):
  precision = |retrieved ∩ relevant| / |retrieved|
  recall    = |retrieved ∩ relevant| / |relevant|
  f1        = harmonic mean of the two
  hit       = 1 if at least one relevant id is in the top-k, else 0

Retrieval Rate (RR%) = mean hit over the query set — the share of queries for
which retrieval surfaced *any* correct chunk.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

# Text-based relevance matching. The query set labels relevance by SAC chunk id
# (`act::s4:b`), which cannot string-match the paragraph ids a non-SAC chunker
# produces (`act::p12`). To compare chunkers fairly we resolve each labeled id
# to its text and count a retrieved chunk as relevant when it substantially
# contains that text -- applied identically to both arms.
_WHITESPACE = re.compile(r"\s+")
_TOKEN = re.compile(r"[a-z0-9]+")
DEFAULT_OVERLAP_THRESHOLD = 0.8


@dataclass
class QueryMetrics:
    query: str
    precision: float
    recall: float
    f1: float
    hit: bool
    retrieved_ids: list[str]
    relevant_ids: list[str]
    # Total characters of retrieved context. Precision at a fixed k is
    # granularity-sensitive -- a chunker with 5x larger chunks is capped at a
    # 5x lower precision even when it returns the same answer text -- so the
    # size of the context actually handed downstream is reported alongside it.
    retrieved_chars: int = 0


@dataclass
class AggregateMetrics:
    n_queries: int
    precision: float
    recall: float
    f1: float
    retrieval_rate: float
    mean_retrieved_chars: float = 0.0


def precision_recall_f1(
    retrieved_ids: list[str], relevant_ids: list[str]
) -> tuple[float, float, float]:
    relevant = set(relevant_ids)
    retrieved = list(retrieved_ids)
    if not retrieved:
        return 0.0, 0.0, 0.0
    hits = sum(1 for cid in retrieved if cid in relevant)
    precision = hits / len(retrieved)
    recall = hits / len(relevant) if relevant else 0.0
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def normalize(text: str) -> str:
    """Lowercase + collapse whitespace, so formatting differences don't matter."""
    return _WHITESPACE.sub(" ", text.lower()).strip()


def text_matches(
    labeled_text: str, chunk_text: str, threshold: float = DEFAULT_OVERLAP_THRESHOLD
) -> bool:
    """True if `chunk_text` substantially carries `labeled_text`.

    Either the labeled clause appears verbatim inside the chunk (the usual case
    when a paragraph chunk swallows a whole section), the chunk is itself a
    fragment of the labeled clause, or at least `threshold` of the labeled
    clause's tokens appear in the chunk.
    """
    labeled = normalize(labeled_text)
    chunk = normalize(chunk_text)
    if not labeled or not chunk:
        return False
    if labeled in chunk or chunk in labeled:
        return True
    labeled_tokens = set(_TOKEN.findall(labeled))
    if not labeled_tokens:
        return False
    chunk_tokens = set(_TOKEN.findall(chunk))
    return len(labeled_tokens & chunk_tokens) / len(labeled_tokens) >= threshold


def score_query_by_text(
    query: str,
    retrieved_rows: list[dict],
    relevant_ids: list[str],
    relevant_texts: list[str],
    threshold: float = DEFAULT_OVERLAP_THRESHOLD,
) -> QueryMetrics:
    """Score one query by chunk *text* rather than chunk id.

    precision = share of retrieved chunks carrying some labeled clause;
    recall    = share of labeled clauses carried by some retrieved chunk.
    """
    retrieved_ids = [row["chunk_id"] for row in retrieved_rows]
    if not retrieved_rows:
        return QueryMetrics(query, 0.0, 0.0, 0.0, False, retrieved_ids, list(relevant_ids), 0)
    matched_rows = sum(
        1 for row in retrieved_rows
        if any(text_matches(t, row["text"], threshold) for t in relevant_texts)
    )
    matched_labels = sum(
        1 for t in relevant_texts
        if any(text_matches(t, row["text"], threshold) for row in retrieved_rows)
    )
    precision = matched_rows / len(retrieved_rows)
    recall = matched_labels / len(relevant_texts) if relevant_texts else 0.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return QueryMetrics(
        query=query,
        precision=precision,
        recall=recall,
        f1=f1,
        hit=matched_rows > 0,
        retrieved_ids=retrieved_ids,
        relevant_ids=list(relevant_ids),
        retrieved_chars=sum(len(row["text"]) for row in retrieved_rows),
    )


def score_query(query: str, retrieved_ids: list[str], relevant_ids: list[str]) -> QueryMetrics:
    precision, recall, f1 = precision_recall_f1(retrieved_ids, relevant_ids)
    relevant = set(relevant_ids)
    hit = any(cid in relevant for cid in retrieved_ids)
    return QueryMetrics(
        query=query,
        precision=precision,
        recall=recall,
        f1=f1,
        hit=hit,
        retrieved_ids=list(retrieved_ids),
        relevant_ids=list(relevant_ids),
    )


def aggregate(per_query: list[QueryMetrics]) -> AggregateMetrics:
    n = len(per_query)
    if n == 0:
        return AggregateMetrics(0, 0.0, 0.0, 0.0, 0.0)
    return AggregateMetrics(
        n_queries=n,
        precision=sum(m.precision for m in per_query) / n,
        recall=sum(m.recall for m in per_query) / n,
        f1=sum(m.f1 for m in per_query) / n,
        retrieval_rate=sum(1 for m in per_query if m.hit) / n,
        mean_retrieved_chars=sum(m.retrieved_chars for m in per_query) / n,
    )


def load_queryset(path: str | Path) -> list[dict]:
    """Load the labeled query set: [{"query": ..., "relevant_chunk_ids": [...]}]."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["queries"] if isinstance(data, dict) else data


def evaluate_queryset(
    retriever,
    queryset: list[dict],
    text_by_chunk_id: dict[str, str] | None = None,
    threshold: float = DEFAULT_OVERLAP_THRESHOLD,
) -> tuple[AggregateMetrics, list[QueryMetrics]]:
    """Run every labeled query through `retriever` and score it.

    `retriever` is anything with `.retrieve(query) -> list[row dict]`; each row
    must carry a "chunk_id" (and, for text matching, a "text"). Pass
    `text_by_chunk_id` (labeled chunk id -> its text) to score by text instead
    of by exact id -- required when comparing chunkers whose ids differ.
    Returns (aggregate, per-query) metrics.
    """
    per_query: list[QueryMetrics] = []
    for entry in queryset:
        rows = retriever.retrieve(entry["query"])
        relevant_ids = entry["relevant_chunk_ids"]
        if text_by_chunk_id is None:
            per_query.append(
                score_query(entry["query"], [r["chunk_id"] for r in rows], relevant_ids)
            )
            continue
        missing = [cid for cid in relevant_ids if cid not in text_by_chunk_id]
        if missing:
            raise KeyError(f"labeled chunk ids not found in the chunk text map: {missing}")
        per_query.append(
            score_query_by_text(
                entry["query"],
                rows,
                relevant_ids,
                [text_by_chunk_id[cid] for cid in relevant_ids],
                threshold,
            )
        )
    return aggregate(per_query), per_query


def metrics_to_dict(agg: AggregateMetrics, per_query: list[QueryMetrics]) -> dict:
    return {
        "aggregate": asdict(agg),
        "per_query": [asdict(m) for m in per_query],
    }
