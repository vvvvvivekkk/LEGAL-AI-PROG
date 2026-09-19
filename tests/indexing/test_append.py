from src.chunking.sac import chunk_document
from src.indexing.build import append_chunks, build_index
from src.indexing.query import search_hybrid
from src.ingestion.pipeline import ingest_file


def test_append_adds_second_document_without_losing_the_first(tmp_path, sample_data_dir, real_embedder):
    db_path = tmp_path / "lancedb"

    doc_a = ingest_file(sample_data_dir / "data_privacy_act_2024.txt")
    chunks_a = [c.to_dict() for c in chunk_document(doc_a)]

    doc_b = ingest_file(sample_data_dir / "urban_tenancy_act_2019.txt")
    chunks_b = [c.to_dict() for c in chunk_document(doc_b)]

    table = build_index(chunks_a, db_path=db_path, embedder=real_embedder)
    assert table.count_rows() == len(chunks_a)

    table = append_chunks(chunks_b, db_path=db_path, embedder=real_embedder)
    assert table.count_rows() == len(chunks_a) + len(chunks_b)

    # Nothing from doc A got duplicated or lost.
    all_ids = {row["chunk_id"] for row in table.to_pandas().to_dict(orient="records")}
    assert all_ids == {c["chunk_id"] for c in chunks_a} | {c["chunk_id"] for c in chunks_b}

    # Both documents are searchable via hybrid search after the append.
    results_a = search_hybrid(table, "grievance officer", k=5, embedder=real_embedder)
    assert any(r["metadata"]["source_id"] == "data_privacy_act_2024" for r in results_a)

    results_b = search_hybrid(table, "security deposit", k=5, embedder=real_embedder)
    assert any(r["metadata"]["source_id"] == "urban_tenancy_act_2019" for r in results_b)


def test_append_creates_table_if_missing(tmp_path, sample_data_dir, real_embedder):
    db_path = tmp_path / "lancedb"
    doc = ingest_file(sample_data_dir / "small_business_licensing_act_2021.txt")
    chunks = [c.to_dict() for c in chunk_document(doc)]

    table = append_chunks(chunks, db_path=db_path, embedder=real_embedder)
    assert table.count_rows() == len(chunks)
