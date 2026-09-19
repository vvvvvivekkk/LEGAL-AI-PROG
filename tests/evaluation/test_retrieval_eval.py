"""evaluate_queryset tests using a fake retriever (no model / network)."""

from pathlib import Path

from src.evaluation.retrieval_eval import evaluate_queryset, load_queryset

_REPO_ROOT = Path(__file__).resolve().parents[2]
_QUERYSET = _REPO_ROOT / "data" / "eval" / "retrieval_queryset.json"


class FakeRetriever:
    """Returns caller-supplied rows keyed by query."""

    def __init__(self, mapping: dict[str, list[str]]):
        self.mapping = mapping

    def retrieve(self, query: str) -> list[dict]:
        return [{"chunk_id": cid} for cid in self.mapping.get(query, [])]


def test_evaluate_queryset_scores_each_query():
    queryset = [
        {"query": "q1", "relevant_chunk_ids": ["a"]},
        {"query": "q2", "relevant_chunk_ids": ["b", "c"]},
    ]
    retriever = FakeRetriever({"q1": ["a", "z"], "q2": ["b", "x"]})
    agg, per_query = evaluate_queryset(retriever, queryset)

    assert len(per_query) == 2
    assert agg.n_queries == 2
    assert agg.retrieval_rate == 1.0  # both queries retrieved a relevant id


def test_evaluate_queryset_partial_miss():
    queryset = [
        {"query": "q1", "relevant_chunk_ids": ["a"]},
        {"query": "q2", "relevant_chunk_ids": ["b"]},
    ]
    retriever = FakeRetriever({"q1": ["a"], "q2": ["nope"]})
    agg, _ = evaluate_queryset(retriever, queryset)
    assert agg.retrieval_rate == 0.5


def test_shipped_queryset_is_wellformed():
    """The hand-labeled query set must load and reference plausible chunk ids."""
    queries = load_queryset(_QUERYSET)
    assert 8 <= len(queries) <= 12
    for entry in queries:
        assert entry["query"].strip()
        assert entry["relevant_chunk_ids"]
        for cid in entry["relevant_chunk_ids"]:
            assert "::s" in cid  # matches chunk_id format source::sN[:clause]
