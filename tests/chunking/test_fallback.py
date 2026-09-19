"""Tests for fallback (paragraph/sentence) chunking."""

from src.chunking.fallback import (
    chunk_document_or_fallback,
    fallback_chunks,
)
from src.ingestion.pipeline import ingest_file_with_text


def test_fallback_splits_paragraphs():
    text = "First paragraph about a topic.\n\nSecond paragraph about another topic.\n\nThird one."
    chunks = fallback_chunks(text, source_id="memo")
    assert len(chunks) == 3
    assert chunks[0].chunk_id == "memo::p1"
    assert chunks[0].metadata["structure"] == "fallback"
    assert chunks[0].metadata["section_ref"] == "Paragraph 1"
    assert "First paragraph" in chunks[0].text


def test_fallback_packs_long_paragraph_by_sentences():
    sentence = "This is a fairly long sentence that carries some content. "
    long_para = sentence * 40  # ~2280 chars, one paragraph
    chunks = fallback_chunks(long_para, source_id="doc", max_chars=300)
    assert len(chunks) > 1
    assert all(len(c.text) <= 320 for c in chunks)  # allow small packing slack


def test_fallback_hard_wraps_oversized_sentence():
    blob = "x" * 1000  # no sentence/paragraph breaks at all
    chunks = fallback_chunks(blob, source_id="doc", max_chars=200)
    assert len(chunks) == 5
    assert all(len(c.text) <= 200 for c in chunks)


def test_fallback_ignores_blank_paragraphs():
    text = "Real content here.\n\n\n\n   \n\nMore content."
    chunks = fallback_chunks(text, source_id="doc")
    assert len(chunks) == 2


def test_fallback_chunk_ids_unique_and_serializable():
    text = "Para one.\n\nPara two.\n\nPara three."
    chunks = fallback_chunks(text, source_id="doc")
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    d = chunks[0].to_dict()
    assert set(d.keys()) == {"chunk_id", "text", "contextual_summary", "metadata"}


def test_orchestrator_uses_structural_for_statute(tmp_path):
    statute = tmp_path / "mini_act.txt"
    statute.write_text(
        "THE FICTIONAL SAMPLE ACT, 2020\n"
        "Jurisdiction: Testland\n\n"
        "CHAPTER I - PRELIMINARY\n\n"
        "Section 1. Short title.\n"
        "This Act may be called the Sample Act.\n",
        encoding="utf-8",
    )
    document, cleaned = ingest_file_with_text(statute)
    chunks, used_fallback = chunk_document_or_fallback(document, cleaned)
    assert not used_fallback
    assert chunks
    assert all(c.metadata.get("structure") != "fallback" for c in chunks)


def test_orchestrator_falls_back_for_unstructured(tmp_path):
    memo = tmp_path / "memo.txt"
    memo.write_text(
        "Meeting notes from Tuesday.\n\n"
        "We discussed the roadmap and agreed on next steps.\n\n"
        "Action items were assigned to the team.\n",
        encoding="utf-8",
    )
    document, cleaned = ingest_file_with_text(memo)
    chunks, used_fallback = chunk_document_or_fallback(document, cleaned)
    assert used_fallback
    assert len(chunks) == 3
    assert all(c.metadata["structure"] == "fallback" for c in chunks)
