from src.chunking.sac import chunk_corpus, chunk_document
from src.ingestion.pipeline import ingest_directory, ingest_file


def test_chunking_known_structure_privacy_act(sample_data_dir):
    document = ingest_file(sample_data_dir / "data_privacy_act_2024.txt")
    chunks = chunk_document(document)

    # Section 3 has an intro body + 3 clauses -> 4 chunks.
    section_3_chunks = [c for c in chunks if c.metadata["section"] == "3"]
    assert len(section_3_chunks) == 4

    labels = {c.metadata["clause"] for c in section_3_chunks}
    assert labels == {None, "a", "b", "c"}

    # Section 9 has no clauses -> exactly 1 chunk, whole-section body text.
    section_9_chunks = [c for c in chunks if c.metadata["section"] == "9"]
    assert len(section_9_chunks) == 1
    assert section_9_chunks[0].metadata["clause"] is None
    assert section_9_chunks[0].text.startswith("This section requires every data fiduciary")


def test_chunk_ids_are_unique_and_stable(sample_data_dir):
    document = ingest_file(sample_data_dir / "data_privacy_act_2024.txt")
    chunks = chunk_document(document)

    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))

    clause_a_of_3 = next(c for c in chunks if c.metadata["section_ref"] == "Section 3(a)")
    assert clause_a_of_3.chunk_id == "data_privacy_act_2024::s3:a"


def test_metadata_extracted_correctly(sample_data_dir):
    document = ingest_file(sample_data_dir / "urban_tenancy_act_2019.txt")
    chunks = chunk_document(document)

    clause = next(c for c in chunks if c.metadata["section_ref"] == "Section 4(a)")
    assert clause.metadata["source_id"] == "urban_tenancy_act_2019"
    assert "URBAN TENANCY ACT" in clause.metadata["act"]
    assert clause.metadata["jurisdiction"] == "State of Larenthia"
    assert clause.metadata["date"] == "4 July 2019"
    assert clause.metadata["chapter"] == "Chapter II — RENT AGREEMENTS"
    assert clause.metadata["section_title"] == "Security deposit limits"
    assert clause.text.startswith("The security deposit shall not exceed two months")


def test_contextual_summary_reflects_parent_section(sample_data_dir):
    document = ingest_file(sample_data_dir / "environmental_waste_act_2022.txt")
    chunks = chunk_document(document)

    section_4_chunks = [c for c in chunks if c.metadata["section"] == "4"]
    assert len(section_4_chunks) >= 2

    # Every chunk under the same section shares one contextual summary, and
    # that summary carries the section heading + its own first sentence --
    # not the clause text itself.
    summaries = {c.contextual_summary for c in section_4_chunks}
    assert len(summaries) == 1
    summary = summaries.pop()
    assert "Section 4. Disposal of hazardous waste." in summary
    assert "This section governs how a waste generator must handle" in summary

    clause_chunk = next(c for c in section_4_chunks if c.metadata["clause"] == "a")
    assert clause_chunk.text != clause_chunk.contextual_summary
    assert "Hazardous waste must be handed over" in clause_chunk.text


def test_chunk_corpus_flattens_all_documents(sample_data_dir):
    documents = ingest_directory(sample_data_dir)
    chunks = chunk_corpus(documents)

    source_ids = {c.metadata["source_id"] for c in chunks}
    assert source_ids == {d.source_id for d in documents}
    assert len(chunks) > 20  # sanity: real hierarchy produced a real number of chunks


def test_chunk_record_to_dict_shape(sample_data_dir):
    document = ingest_file(sample_data_dir / "consumer_protection_act_2020.txt")
    chunk = chunk_document(document)[0]
    d = chunk.to_dict()
    assert set(d.keys()) == {"chunk_id", "text", "contextual_summary", "metadata"}
