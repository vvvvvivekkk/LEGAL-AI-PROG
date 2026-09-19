"""Ingestion pipeline: load + clean + structurally parse a corpus directory."""

from __future__ import annotations

from pathlib import Path

from src.ingestion.cleaning import clean_text
from src.ingestion.loaders import load_txt
from src.ingestion.structure import Document, parse_document


def ingest_file(path: str | Path) -> Document:
    """Load, clean, and structurally parse a single .txt statute file."""
    path = Path(path)
    raw = load_txt(path)
    cleaned = clean_text(raw)
    return parse_document(cleaned, source_id=path.stem)


def ingest_directory(directory: str | Path, pattern: str = "*.txt") -> list[Document]:
    """Ingest every matching file in a directory, sorted by filename."""
    directory = Path(directory)
    paths = sorted(directory.glob(pattern))
    return [ingest_file(path) for path in paths]
