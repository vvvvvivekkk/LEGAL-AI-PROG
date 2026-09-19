"""Document loaders.

Only plain-text (.txt) statute files are supported for now — that's all the
sample corpus contains. PDF/HTML loaders are stubbed so the module shape
matches the target architecture without pretending to support formats we
haven't implemented or tested against yet.
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def load_txt(path: str | Path, encoding: str = "utf-8") -> str:
    """Load a plain-text document and return its raw contents."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"No such file: {path}")
    return path.read_text(encoding=encoding)


def load_pdf(path: str | Path) -> str:
    """Load a PDF document and extract its text, page by page, via pypdf."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"No such file: {path}")
    reader = PdfReader(str(path))
    pages_text = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages_text)


def load_html(path: str | Path) -> str:
    """Load an HTML document. Not implemented yet — no HTML support in phase 1."""
    raise NotImplementedError(
        "HTML ingestion is not implemented yet. Only .txt loaders exist so far "
        "(see docs/phases/phase-01-ingestion-chunking.md)."
    )


_LOADERS = {
    ".txt": load_txt,
    ".pdf": load_pdf,
    ".htm": load_html,
    ".html": load_html,
}


def load_document(path: str | Path) -> str:
    """Dispatch to the right loader based on file extension."""
    path = Path(path)
    suffix = path.suffix.lower()
    try:
        loader = _LOADERS[suffix]
    except KeyError as exc:
        raise ValueError(f"No loader registered for file extension {suffix!r}") from exc
    return loader(path)
