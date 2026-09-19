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
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class QueryMetrics:
    query: str
    precision: float
    recall: float
    f1: float
    hit: bool
    retrieved_ids: list[str]
    relevant_ids: list[str]


@dataclass
class AggregateMetrics:
    n_queries: int
    precision: float
    recall: float
    f1: float
    retrieval_rate: float


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
    )


def load_queryset(path: str | Path) -> list[dict]:
    """Load the labeled query set: [{"query": ..., "relevant_chunk_ids": [...]}]."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["queries"] if isinstance(data, dict) else data


def evaluate_queryset(retriever, queryset: list[dict]) -> tuple[AggregateMetrics, list[QueryMetrics]]:
    """Run every labeled query through `retriever` and score it.

    `retriever` is anything with `.retrieve(query) -> list[row dict]`; each row
    must carry a "chunk_id". Returns (aggregate, per-query) metrics.
    """
    per_query: list[QueryMetrics] = []
    for entry in queryset:
        rows = retriever.retrieve(entry["query"])
        retrieved_ids = [r["chunk_id"] for r in rows]
        per_query.append(
            score_query(entry["query"], retrieved_ids, entry["relevant_chunk_ids"])
        )
    return aggregate(per_query), per_query


def metrics_to_dict(agg: AggregateMetrics, per_query: list[QueryMetrics]) -> dict:
    return {
        "aggregate": asdict(agg),
        "per_query": [asdict(m) for m in per_query],
    }
