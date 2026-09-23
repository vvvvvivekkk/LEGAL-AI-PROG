"""The LangChain loaders + splitters must produce exactly src/'s chunks.

Compared chunk by chunk -- id, text, contextual summary and the full metadata
dict -- on every file in data/sample/ and on ContractNLI agreements (one .txt,
one .pdf) from the raw corpus. data/corpus/ is gitignored, and the sample PDFs
are local too, so those cases skip when the files are absent rather than fail.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lc.loaders import load_document
from lc.splitters import split_with_fallback, to_chunk_dict
from src.chunking.fallback import chunk_document_or_fallback
from src.ingestion.pipeline import ingest_file_with_text

REPO = Path(__file__).resolve().parents[2]
SAMPLE = REPO / "data" / "sample"
CONTRACTNLI = REPO / "data" / "corpus" / "civil_law" / "contractnli" / "contract-nli" / "raw"

SAMPLE_FILES = sorted(SAMPLE.glob("*.txt")) + sorted(SAMPLE.glob("*.pdf"))
CONTRACTNLI_FILES = [
    CONTRACTNLI / "1013322_0000912057-00-023405_document_2.txt",
    CONTRACTNLI / "01_Bosch-Automotive-Service-Solutions-Mutual-Non-Disclosure-Agreement-7-12-17.pdf",
]


def _src_chunks(path: Path) -> tuple[list[dict], bool]:
    document, cleaned = ingest_file_with_text(path)
    records, used_fallback = chunk_document_or_fallback(document, cleaned)
    return [r.to_dict() for r in records], used_fallback


def _lc_chunks(path: Path) -> tuple[list[dict], bool]:
    docs, used_fallback = split_with_fallback(load_document(path))
    return [to_chunk_dict(d) for d in docs], used_fallback


def _assert_identical(path: Path) -> None:
    expected, expected_fallback = _src_chunks(path)
    actual, actual_fallback = _lc_chunks(path)
    assert expected, f"src produced no chunks for {path.name}"
    assert actual_fallback == expected_fallback
    assert len(actual) == len(expected)
    for want, got in zip(expected, actual):
        assert got["chunk_id"] == want["chunk_id"]
        assert got["text"] == want["text"], want["chunk_id"]
        assert got["contextual_summary"] == want["contextual_summary"], want["chunk_id"]
        assert got["metadata"] == want["metadata"], want["chunk_id"]


@pytest.mark.parametrize("path", SAMPLE_FILES, ids=lambda p: p.name)
def test_sample_chunks_identical(path):
    _assert_identical(path)


@pytest.mark.parametrize("path", CONTRACTNLI_FILES, ids=lambda p: p.name)
def test_contractnli_chunks_identical(path):
    if not path.exists():
        pytest.skip(f"{path.name} not present (data/corpus is gitignored)")
    _assert_identical(path)


def test_sample_statutes_take_the_sac_path():
    """Guards the test itself: the statutes must exercise SAC, not fallback."""
    for path in sorted(SAMPLE.glob("*.txt")):
        _, used_fallback = _lc_chunks(path)
        assert used_fallback is False, path.name
