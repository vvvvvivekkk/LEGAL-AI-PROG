"""Retriever tests: config knobs + reranking behaviour.

The reranking-plumbing tests use a deterministic fake reranker and a fake
table, so they always run. A real-index test builds a LanceDB table with the
actual embedder and skips if the model can't be fetched.
"""

import pytest

from src.chunking.sac import chunk_corpus
from src.indexing.build import build_index
from src.ingestion.pipeline import ingest_directory
from src.retrieval.config import RetrievalConfig
from src.retrieval.retriever import Retriever


class RecordingReranker:
    """Reranker that records how many candidates it saw and reverses them."""

    def __init__(self):
        self.seen_counts: list[int] = []

    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        self.seen_counts.append(len(candidates))
        return list(reversed(candidates))


class FakeTable:
    """Minimal stand-in that returns a fixed candidate list, ignoring the query."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    # Retriever._fetch goes through src.indexing.query helpers, which call
    # table.search(...). We bypass that by patching _fetch in tests below,
    # so this table only needs to exist as an object.


def _rows(n: int) -> list[dict]:
    return [{"chunk_id": f"c{i}", "text": f"text {i}", "contextual_summary": ""} for i in range(n)]


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

def test_config_rejects_bad_mode():
    with pytest.raises(ValueError):
        RetrievalConfig(mode="magic")


def test_config_rejects_n_below_k():
    with pytest.raises(ValueError):
        RetrievalConfig(k=10, n=5)


# ---------------------------------------------------------------------------
# Rerank plumbing (fake reranker + monkeypatched _fetch)
# ---------------------------------------------------------------------------

def test_reranker_sees_n_candidates_and_truncates_to_k(monkeypatch):
    reranker = RecordingReranker()
    config = RetrievalConfig(mode="hybrid", use_reranker=True, k=3, n=10)
    retriever = Retriever(FakeTable([]), config=config, embedder=object(), reranker=reranker)

    monkeypatch.setattr(retriever, "_fetch", lambda q, limit: _rows(limit))
    out = retriever.retrieve("anything")

    assert reranker.seen_counts == [10]   # fetched N before reranking
    assert len(out) == 3                  # truncated to k
    # reversed order: reranker got c0..c9, reversed -> c9 first
    assert out[0]["chunk_id"] == "c9"


def test_no_reranker_fetches_k_directly(monkeypatch):
    config = RetrievalConfig(mode="dense", use_reranker=False, k=4, n=20)
    retriever = Retriever(FakeTable([]), config=config, embedder=object())

    captured = {}

    def fake_fetch(q, limit):
        captured["limit"] = limit
        return _rows(limit)

    monkeypatch.setattr(retriever, "_fetch", fake_fetch)
    out = retriever.retrieve("anything")

    assert captured["limit"] == 4  # fetched k, not n
    assert len(out) == 4
    assert out[0]["chunk_id"] == "c0"  # order preserved (no rerank)


def test_no_reranker_means_no_cross_encoder_built():
    config = RetrievalConfig(use_reranker=False)
    retriever = Retriever(FakeTable([]), config=config, embedder=object())
    assert retriever._reranker is None


# ---------------------------------------------------------------------------
# Real index integration (skips if embedder model unavailable)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def sample_table(tmp_path_factory, real_embedder):
    chunks = [c.to_dict() for c in chunk_corpus(ingest_directory("data/sample"))]
    db_path = tmp_path_factory.mktemp("lancedb_retrieval")
    return build_index(chunks, db_path=str(db_path), embedder=real_embedder)


def test_dense_retrieval_returns_k(sample_table, real_embedder):
    config = RetrievalConfig(mode="dense", use_reranker=False, k=5, n=20)
    retriever = Retriever(sample_table, config=config, embedder=real_embedder)
    out = retriever.retrieve("landlord security deposit refund")
    assert len(out) == 5
    assert all("chunk_id" in r for r in out)


def test_hybrid_retrieval_finds_deposit_clause(sample_table, real_embedder):
    config = RetrievalConfig(mode="hybrid", use_reranker=False, k=10, n=20)
    retriever = Retriever(sample_table, config=config, embedder=real_embedder)
    out = retriever.retrieve("how long to refund a tenant security deposit")
    ids = [r["chunk_id"] for r in out]
    assert any("urban_tenancy_act_2019::s4" in cid for cid in ids)


@pytest.fixture(scope="module")
def real_reranker():
    """The real cross-encoder; skips if the model can't be fetched."""
    from src.retrieval.rerank import CrossEncoderReranker

    reranker = CrossEncoderReranker()
    try:
        reranker.rerank("warmup", [{"chunk_id": "w", "text": "warmup", "contextual_summary": ""}])
    except Exception as exc:  # noqa: BLE001 - network/environment errors vary
        pytest.skip(f"cross-encoder reranker unavailable: {exc}")
    return reranker


def test_reranking_adds_scores_and_promotes_relevant(sample_table, real_embedder, real_reranker):
    config = RetrievalConfig(mode="hybrid", use_reranker=True, k=5, n=20)
    retriever = Retriever(sample_table, config=config, embedder=real_embedder, reranker=real_reranker)
    out = retriever.retrieve("how much security deposit can a landlord collect")

    assert len(out) == 5
    assert all("rerank_score" in r for r in out)
    # rerank scores must be in non-increasing order
    scores = [r["rerank_score"] for r in out]
    assert scores == sorted(scores, reverse=True)
    # the deposit-cap clause should surface in the reranked top-5
    ids = [r["chunk_id"] for r in out]
    assert any("urban_tenancy_act_2019::s4" in cid for cid in ids)
