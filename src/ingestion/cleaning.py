"""Basic text cleaning for ingested legal documents.

Kept deliberately simple for phase 1: normalize line endings/whitespace
without touching the structural markers (CHAPTER/Section/Clause headings)
that src/ingestion/structure.py relies on.
"""

from __future__ import annotations

import re

_TRAILING_WHITESPACE_RE = re.compile(r"[ \t]+\n")
_MULTI_BLANK_LINES_RE = re.compile(r"\n{3,}")


def clean_text(raw_text: str) -> str:
    """Normalize whitespace in a raw document while preserving line structure.

    - Normalizes CRLF/CR to LF.
    - Strips trailing whitespace on each line.
    - Collapses 3+ consecutive blank lines down to a single blank line.
    - Strips leading/trailing blank lines from the whole document.
    """
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    text = _TRAILING_WHITESPACE_RE.sub("\n", text)
    text = _MULTI_BLANK_LINES_RE.sub("\n\n", text)
    return text.strip("\n")
