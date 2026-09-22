"""Neighbor-chunk expansion tests.

Covers the id-ordering primitives on both chunk id shapes (fallback "::p41",
SAC "::s4" / "::s4:b"), the ±window step, the document boundary, and the
Retriever wiring including the off-by-default behaviour.
"""

import pytest

from src.retrieval.config import RetrievalConfig
from src.retrieval.neighbors import (
    NEIGHBOR_OF_KEY,
    chunk_order_key,
    document_order,
    expand_with_neighbors,
    neighbor_ids,
    source_of,
)
from src.retrieval.retriever import Retriever

NDA = "064-19 Non Disclosure Agreement 2019"


def _row(chunk_id: str, text: str = "") -> dict:
    return {"chunk_id": chunk_id, "text": text or chunk_id, "contextual_summary": ""}


class FakeTable:
    """Stand-in table; the retriever's fetches are monkeypatched in these tests."""


# ---------------------------------------------------------------------------
# Chunk id parsing / document order
# ---------------------------------------------------------------------------

def test_source_of_handles_spaces_and_digits_in_source_id():
    assert source_of(f"{NDA}::p41") == NDA


def test_source_of_returns_none_for_unstructured_id():
    assert source_of("no-separator-here") is None


@pytest.mark.parametrize(
    "chunk_id,expected",
    [
        (f"{NDA}::p41", ("p", (41,), "")),
        ("urban_tenancy_act_2019::s4", ("s", (4,), "")),
        ("urban_tenancy_act_2019::s4:b", ("s", (4,), "b")),
        ("urban_tenancy_act_2019::s12.1:c", ("s", (12, 1), "c")),
    ],
)
def test_chunk_order_key_parses_both_id_schemes(chunk_id, expected):
    assert chunk_order_key(chunk_id) == expected


@pytest.mark.parametrize("chunk_id", ["bare_id", f"{NDA}::", "::p4", f"{NDA}::appendix"])
def test_chunk_order_key_is_none_for_unsupported_ids(chunk_id):
    assert chunk_order_key(chunk_id) is None


def test_document_order_sorts_numerically_not_lexically():
    ids = [f"{NDA}::p9", f"{NDA}::p41", f"{NDA}::p10", f"{NDA}::p42"]
    assert document_order(ids) == [
        f"{NDA}::p9",
        f"{NDA}::p10",
        f"{NDA}::p41",
        f"{NDA}::p42",
    ]


def test_document_order_places_sac_body_before_its_clauses():
    ids = ["act::s4:b", "act::s4", "act::s3:a", "act::s4:a"]
    assert document_order(ids) == ["act::s3:a", "act::s4", "act::s4:a", "act::s4:b"]


def test_document_order_drops_ids_with_no_parseable_position():
    ids = [f"{NDA}::p2", f"{NDA}::cover", f"{NDA}::p1"]
    assert document_order(ids) == [f"{NDA}::p1", f"{NDA}::p2"]


# ---------------------------------------------------------------------------
# ±window logic
# ---------------------------------------------------------------------------

def _nda_ids(count: int = 56) -> list[str]:
    return [f"{NDA}::p{i}" for i in range(1, count + 1)]


def test_window_one_takes_the_chunk_on_either_side():
    assert neighbor_ids(f"{NDA}::p41", _nda_ids(), window=1) == [f"{NDA}::p40", f"{NDA}::p42"]


def test_window_two_takes_two_on_either_side_in_document_order():
    assert neighbor_ids(f"{NDA}::p41", _nda_ids(), window=2) == [
        f"{NDA}::p39",
        f"{NDA}::p40",
        f"{NDA}::p42",
        f"{NDA}::p43",
    ]


def test_window_zero_takes_nothing():
    assert neighbor_ids(f"{NDA}::p41", _nda_ids(), window=0) == []


def test_window_is_clipped_at_the_start_and_end_of_the_document():
    ids = _nda_ids(3)
    assert neighbor_ids(f"{NDA}::p1", ids, window=1) == [f"{NDA}::p2"]
    assert neighbor_ids(f"{NDA}::p3", ids, window=1) == [f"{NDA}::p2"]


def test_window_steps_over_gaps_rather_than_guessing_missing_ordinals():
    """p42 is p41's neighbour even if p40 and p43 were never indexed."""
    ids = [f"{NDA}::p10", f"{NDA}::p41", f"{NDA}::p42"]
    assert neighbor_ids(f"{NDA}::p41", ids, window=1) == [f"{NDA}::p10", f"{NDA}::p42"]


def test_unparseable_anchor_gets_no_neighbours():
    assert neighbor_ids(f"{NDA}::cover", _nda_ids(), window=1) == []


# ---------------------------------------------------------------------------
# expand_with_neighbors
# ---------------------------------------------------------------------------

def _siblings_for(docs: dict[str, list[str]]):
    return lambda source_id: [_row(cid) for cid in docs.get(source_id, [])]


def test_expansion_pulls_the_split_remedies_clause_in_document_order():
    docs = {NDA: _nda_ids()}
    out = expand_with_neighbors([_row(f"{NDA}::p41")], _siblings_for(docs), window=1)
    assert [r["chunk_id"] for r in out] == [
        f"{NDA}::p40",
        f"{NDA}::p41",
        f"{NDA}::p42",
    ]


def test_neighbours_are_tagged_with_their_anchor_and_carry_no_score():
    docs = {NDA: _nda_ids()}
    anchor = dict(_row(f"{NDA}::p41"), rerank_score=0.96)
    out = expand_with_neighbors([anchor], _siblings_for(docs), window=1)
    by_id = {r["chunk_id"]: r for r in out}
    assert by_id[f"{NDA}::p42"][NEIGHBOR_OF_KEY] == f"{NDA}::p41"
    assert "rerank_score" not in by_id[f"{NDA}::p42"]
    # the anchor itself is untouched
    assert by_id[f"{NDA}::p41"]["rerank_score"] == 0.96
    assert NEIGHBOR_OF_KEY not in by_id[f"{NDA}::p41"]


def test_expansion_never_crosses_a_document_boundary():
    docs = {"doc_a": ["doc_a::p1", "doc_a::p2"], "doc_b": ["doc_b::p1", "doc_b::p2"]}
    out = expand_with_neighbors([_row("doc_a::p2")], _siblings_for(docs), window=1)
    ids = [r["chunk_id"] for r in out]
    assert ids == ["doc_a::p1", "doc_a::p2"]
    assert not any(cid.startswith("doc_b") for cid in ids)


def test_expansion_keeps_ranked_order_of_anchors_and_never_drops_one():
    docs = {NDA: _nda_ids()}
    ranked = [_row(f"{NDA}::p23"), _row(f"{NDA}::p41")]
    out = expand_with_neighbors(ranked, _siblings_for(docs), window=1)
    ids = [r["chunk_id"] for r in out]
    assert ids == [
        f"{NDA}::p22",
        f"{NDA}::p23",
        f"{NDA}::p24",
        f"{NDA}::p40",
        f"{NDA}::p41",
        f"{NDA}::p42",
    ]
    assert ids.index(f"{NDA}::p23") < ids.index(f"{NDA}::p41")


def test_expansion_does_not_duplicate_overlapping_neighbours():
    docs = {NDA: _nda_ids()}
    ranked = [_row(f"{NDA}::p41"), _row(f"{NDA}::p42")]
    ids = [r["chunk_id"] for r in expand_with_neighbors(ranked, _siblings_for(docs), window=1)]
    assert ids == sorted(set(ids), key=ids.index)  # no repeats
    assert ids == [f"{NDA}::p40", f"{NDA}::p41", f"{NDA}::p42", f"{NDA}::p43"]


def test_rows_with_unparseable_ids_pass_through_untouched():
    out = expand_with_neighbors([_row("bare_id")], _siblings_for({}), window=1)
    assert [r["chunk_id"] for r in out] == ["bare_id"]


def test_expansion_queries_each_source_document_only_once():
    docs = {NDA: _nda_ids()}
    calls: list[str] = []

    def siblings_for(source_id):
        calls.append(source_id)
        return [_row(cid) for cid in docs.get(source_id, [])]

    ranked = [_row(f"{NDA}::p10"), _row(f"{NDA}::p41"), _row(f"{NDA}::p50")]
    expand_with_neighbors(ranked, siblings_for, window=1)
    assert calls == [NDA]


# ---------------------------------------------------------------------------
# Config + Retriever wiring
# ---------------------------------------------------------------------------

def test_expansion_is_off_by_default():
    assert RetrievalConfig().neighbor_window == 0


def test_config_rejects_a_negative_window():
    with pytest.raises(ValueError):
        RetrievalConfig(neighbor_window=-1)


def _wired_retriever(monkeypatch, window, ranked_ids, doc_ids):
    config = RetrievalConfig(mode="hybrid", use_reranker=False, k=len(ranked_ids), n=50,
                             neighbor_window=window)
    retriever = Retriever(FakeTable(), config=config, embedder=object())
    monkeypatch.setattr(retriever, "_fetch", lambda q, limit: [_row(c) for c in ranked_ids][:limit])
    monkeypatch.setattr(
        retriever,
        "_fetch_siblings",
        lambda source_id: [_row(c) for c in doc_ids if c.startswith(f"{source_id}::")],
    )
    return retriever


def test_retriever_default_config_does_not_expand(monkeypatch):
    retriever = _wired_retriever(monkeypatch, 0, [f"{NDA}::p41"], _nda_ids())
    assert [r["chunk_id"] for r in retriever.retrieve("q")] == [f"{NDA}::p41"]


def test_retriever_expands_neighbours_when_window_is_set(monkeypatch):
    retriever = _wired_retriever(monkeypatch, 1, [f"{NDA}::p41"], _nda_ids())
    out = retriever.retrieve("q")
    assert [r["chunk_id"] for r in out] == [f"{NDA}::p40", f"{NDA}::p41", f"{NDA}::p42"]


def test_expansion_extends_the_context_rather_than_evicting_ranked_results(monkeypatch):
    """Turning expansion on must never remove a chunk the ranking selected."""
    ranked = [f"{NDA}::p23", f"{NDA}::p41"]
    plain = _wired_retriever(monkeypatch, 0, ranked, _nda_ids()).retrieve("q")
    expanded = _wired_retriever(monkeypatch, 1, ranked, _nda_ids()).retrieve("q")
    expanded_ids = {r["chunk_id"] for r in expanded}
    assert all(r["chunk_id"] in expanded_ids for r in plain)
    assert len(expanded) > len(plain)


def test_retriever_degrades_to_no_expansion_when_sibling_lookup_fails(monkeypatch):
    """A table that cannot serve a filtered scan must not fail the query."""
    config = RetrievalConfig(mode="hybrid", use_reranker=False, k=1, neighbor_window=1)
    retriever = Retriever(FakeTable(), config=config, embedder=object())
    monkeypatch.setattr(retriever, "_fetch", lambda q, limit: [_row(f"{NDA}::p41")])
    # FakeTable has no .search(), so _fetch_siblings hits its except branch.
    assert [r["chunk_id"] for r in retriever.retrieve("q")] == [f"{NDA}::p41"]


# ---------------------------------------------------------------------------
# Real index: the sibling lookup actually runs against LanceDB
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def sample_table(tmp_path_factory, real_embedder):
    from src.chunking.sac import chunk_corpus
    from src.indexing.build import build_index
    from src.ingestion.pipeline import ingest_directory

    chunks = [c.to_dict() for c in chunk_corpus(ingest_directory("data/sample"))]
    db_path = tmp_path_factory.mktemp("lancedb_neighbors")
    return build_index(chunks, db_path=str(db_path), embedder=real_embedder)


def test_sibling_lookup_returns_one_document_only(sample_table, real_embedder):
    config = RetrievalConfig(mode="dense", use_reranker=False, k=1, neighbor_window=1)
    retriever = Retriever(sample_table, config=config, embedder=real_embedder)
    siblings = retriever._fetch_siblings("urban_tenancy_act_2019")
    assert siblings, "expected the sample statute's chunks back from the index"
    assert all(s["chunk_id"].startswith("urban_tenancy_act_2019::") for s in siblings)


def test_real_index_expansion_adds_adjacent_sac_chunks(sample_table, real_embedder):
    query = "how much security deposit can a landlord collect"
    plain_cfg = RetrievalConfig(mode="hybrid", use_reranker=False, k=3, n=20)
    plain = Retriever(sample_table, config=plain_cfg, embedder=real_embedder).retrieve(query)

    wide_cfg = RetrievalConfig(mode="hybrid", use_reranker=False, k=3, n=20, neighbor_window=1)
    wide = Retriever(sample_table, config=wide_cfg, embedder=real_embedder).retrieve(query)

    plain_ids = [r["chunk_id"] for r in plain]
    wide_ids = [r["chunk_id"] for r in wide]
    assert set(plain_ids) <= set(wide_ids)   # nothing evicted
    assert len(wide_ids) > len(plain_ids)    # neighbours really were added
    assert len(wide_ids) == len(set(wide_ids))
    assert any(r.get(NEIGHBOR_OF_KEY) for r in wide)
    # every added chunk comes from a document that was already represented
    plain_sources = {source_of(c) for c in plain_ids}
    assert {source_of(c) for c in wide_ids} <= plain_sources
