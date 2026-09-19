import pytest

from src.chunking.sac import chunk_corpus
from src.indexing.build import build_index
from src.indexing.query import search_dense, search_fts, search_hybrid
from src.ingestion.pipeline import ingest_directory


@pytest.fixture(scope="module")
def sample_chunks():
    # Path resolved directly (not via the function-scoped sample_data_dir
    # fixture) so this can be module-scoped without a ScopeMismatch.
    documents = ingest_directory("data/sample")
    return [c.to_dict() for c in chunk_corpus(documents)]


@pytest.fixture
def indexed_table(tmp_path, sample_chunks, real_embedder):
    db_path = tmp_path / "lancedb"
    table = build_index(sample_chunks, db_path=db_path, embedder=real_embedder)
    return table


def _ids(results: list[dict]) -> list[str]:
    return [r["chunk_id"] for r in results]


def test_build_index_row_count_matches_chunks(indexed_table, sample_chunks):
    assert indexed_table.count_rows() == len(sample_chunks)


def test_keyword_only_query_found_by_fts_and_hybrid(indexed_table, real_embedder):
    # "seventy-two hours" is a distinctive exact phrase that appears in
    # exactly one chunk (the breach-notification clause) -- an easy target
    # for lexical/keyword search, and not an obviously distinctive phrase to
    # find purely by semantic paraphrase.
    target = "data_privacy_act_2024::s5:a"
    query = "seventy-two hours"

    fts_results = search_fts(indexed_table, query, k=5)
    assert target in _ids(fts_results)

    hybrid_results = search_hybrid(indexed_table, query, k=5, embedder=real_embedder)
    assert target in _ids(hybrid_results)


def test_semantic_paraphrase_query_found_by_dense_and_hybrid(indexed_table, real_embedder):
    # Target: "Authorization is valid for a period of three years and must
    # be renewed at least sixty days before expiry." Paraphrased with almost
    # no shared vocabulary -- only findable via semantic similarity, not
    # exact keyword overlap.
    target = "environmental_waste_act_2022::s5:a"
    query = "How soon before an environmental permit runs out does the license holder need to file to keep it active?"

    dense_results = search_dense(indexed_table, query, k=5, embedder=real_embedder)
    assert target in _ids(dense_results)

    hybrid_results = search_hybrid(indexed_table, query, k=5, embedder=real_embedder)
    assert target in _ids(hybrid_results)


def test_search_result_rows_carry_text_and_metadata(indexed_table, real_embedder):
    results = search_hybrid(indexed_table, "grievance officer", k=3, embedder=real_embedder)
    assert results
    first = results[0]
    assert "text" in first and "contextual_summary" in first
    assert isinstance(first["metadata"], dict)
    assert "source_id" in first["metadata"]
