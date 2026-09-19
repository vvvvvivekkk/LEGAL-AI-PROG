"""Ingestion pipeline: load + clean + structurally parse a corpus directory."""

from __future__ import annotations

from pathlib import Path

from src.ingestion.cleaning import clean_text
from src.ingestion.loaders import load_document
from src.ingestion.structure import Document, parse_document


def ingest_file_with_text(path: str | Path) -> tuple[Document, str]:
    """Load (.txt or .pdf), clean, and parse; return the parsed Document and the
    cleaned text. The cleaned text is what fallback chunking needs when the
    document has no legal structure to parse.
    """
    path = Path(path)
    raw = load_document(path)
    cleaned = clean_text(raw)
    document = parse_document(cleaned, source_id=path.stem)
    return document, cleaned


def ingest_file(path: str | Path) -> Document:
    """Load (.txt or .pdf), clean, and structurally parse a single statute file."""
    document, _ = ingest_file_with_text(path)
    return document


def ingest_directory(directory: str | Path, pattern: str = "*.txt") -> list[Document]:
    """Ingest every matching file in a directory, sorted by filename.

    Defaults to *.txt (the sample corpus); pass pattern="*.pdf" or a broader
    glob to also pick up PDFs.
    """
    directory = Path(directory)
    paths = sorted(directory.glob(pattern))
    return [ingest_file(path) for path in paths]
