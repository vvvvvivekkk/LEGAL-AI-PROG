from pathlib import Path

from src.ingestion.loaders import load_document, load_pdf
from src.ingestion.pipeline import ingest_file

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures"
SAMPLE_PDF = FIXTURE_DIR / "sample_statute.pdf"


def test_load_pdf_extracts_text():
    text = load_pdf(SAMPLE_PDF)
    assert "THE FICTIONAL PUBLIC RECORDS ACT, 2018" in text
    assert "Section 2. Right to request public records." in text
    assert "Clause (a): A request must be made in writing" in text


def test_load_document_dispatches_pdf_by_extension():
    text = load_document(SAMPLE_PDF)
    assert "Public Records Act" in text


def test_load_pdf_missing_file_raises():
    try:
        load_pdf(FIXTURE_DIR / "does_not_exist.pdf")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected FileNotFoundError")


def test_ingest_file_parses_pdf_end_to_end():
    document = ingest_file(SAMPLE_PDF)

    assert document.source_id == "sample_statute"
    assert "PUBLIC RECORDS ACT" in document.title
    assert document.jurisdiction == "Republic of Veridia"
    assert document.enacted_date == "3 May 2018"
    assert [c.number for c in document.chapters] == ["I", "II"]

    section_2 = document.chapters[1].sections[0]
    assert section_2.number == "2"
    assert section_2.title == "Right to request public records"
    assert [c.label for c in section_2.clauses] == ["a", "b"]
