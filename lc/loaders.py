"""Document loading on LangChain loaders.

TextLoader (and, for PDFs, PagePDFLoader below) produce the raw text; the result is cleaned with the
same function src/ uses and returned as one LangChain Document per file, with
the same source_id rule as src/ingestion/pipeline.py (filename stem, stripped).

PDFs do NOT go through PyPDFLoader: its parser strip()s every page's text,
with no option to turn that off, while src/ joins pages unstripped. Whitespace
at a page edge decides where a paragraph break falls, so on a real 402-page PDF
the stripped text chunks into 1678 paragraphs instead of 1836. PagePDFLoader
below is a BaseLoader over the same pypdf call as src/, without the strip.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

from src.ingestion.cleaning import clean_text

SUPPORTED_SUFFIXES = {".txt", ".pdf"}


class PagePDFLoader(BaseLoader):
    """One Document per PDF page, text exactly as pypdf extracts it."""

    def __init__(self, file_path: str | Path):
        self.file_path = str(file_path)

    def lazy_load(self) -> Iterator[Document]:
        from pypdf import PdfReader

        for number, page in enumerate(PdfReader(self.file_path).pages):
            yield Document(
                page_content=page.extract_text() or "",
                metadata={"source": self.file_path, "page": number},
            )


def source_id_for(path: str | Path) -> str:
    # Stripped for the same reason as src/: a stray space in a filename ends up
    # inside every chunk_id, and the model cannot reproduce it when citing.
    return Path(path).stem.strip()


def load_raw_text(path: str | Path) -> str:
    """Raw extracted text of one .txt or .pdf file, via a LangChain loader."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"No such file: {path}")
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return TextLoader(str(path), encoding="utf-8").load()[0].page_content
    if suffix == ".pdf":
        pages = PagePDFLoader(path).load()
        return "\n".join(page.page_content for page in pages)
    if suffix in (".htm", ".html"):
        raise NotImplementedError(
            "HTML ingestion is not implemented yet. Only .txt and .pdf loaders exist."
        )
    raise ValueError(f"No loader registered for file extension {suffix!r}")


def load_document(path: str | Path) -> Document:
    """Load + clean one file into a single Document carrying its source_id."""
    path = Path(path)
    cleaned = clean_text(load_raw_text(path))
    return Document(
        page_content=cleaned,
        metadata={"source_id": source_id_for(path), "source": str(path)},
    )
