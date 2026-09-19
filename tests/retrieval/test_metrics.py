"""Pure metric tests for retrieval evaluation (no model / network needed)."""

from src.evaluation.retrieval_eval import (
    aggregate,
    precision_recall_f1,
    score_query,
)


def test_perfect_retrieval():
    p, r, f1 = precision_recall_f1(["a", "b"], ["a", "b"])
    assert p == 1.0
    assert r == 1.0
    assert f1 == 1.0


def test_no_relevant_retrieved():
    p, r, f1 = precision_recall_f1(["x", "y"], ["a", "b"])
    assert p == 0.0
    assert r == 0.0
    assert f1 == 0.0


def test_partial_precision_recall():
    # retrieved 4, 1 relevant hit; relevant set size 2
    p, r, f1 = precision_recall_f1(["a", "x", "y", "z"], ["a", "b"])
    assert p == 0.25
    assert r == 0.5
    assert abs(f1 - (2 * 0.25 * 0.5) / (0.25 + 0.5)) < 1e-9


def test_empty_retrieval_is_zero():
    p, r, f1 = precision_recall_f1([], ["a"])
    assert (p, r, f1) == (0.0, 0.0, 0.0)


def test_score_query_hit_flag():
    m_hit = score_query("q", ["a", "z"], ["a"])
    assert m_hit.hit is True
    m_miss = score_query("q", ["y", "z"], ["a"])
    assert m_miss.hit is False


def test_aggregate_averages_and_retrieval_rate():
    q1 = score_query("q1", ["a"], ["a"])          # perfect hit
    q2 = score_query("q2", ["x"], ["b"])          # miss
    agg = aggregate([q1, q2])
    assert agg.n_queries == 2
    assert agg.precision == 0.5   # (1.0 + 0.0) / 2
    assert agg.retrieval_rate == 0.5  # one of two queries hit


def test_aggregate_empty():
    agg = aggregate([])
    assert agg.n_queries == 0
    assert agg.retrieval_rate == 0.0
