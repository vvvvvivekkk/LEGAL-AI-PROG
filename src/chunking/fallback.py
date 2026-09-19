"""Fallback chunking for documents with no detectable legal structure.

SAC (src/chunking/sac.py) cuts on Act/Chapter/Section/Clause boundaries. When a
document has none of that structure — a plain contract, a memo, arbitrary prose
— structural chunking yields nothing. Rather than dead-ending on "no chunks
produced", this module chunks by paragraph (splitting overly long paragraphs on
sentence boundaries) so any text still lands in the index. Chunks are marked
`structure="fallback"` in metadata so the UI can note that fallback was used.
"""

from __future__ import annotations

import re

from src.chunking.sac import ChunkRecord, chunk_document
from src.ingestion.structure import Document

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

DEFAULT_MAX_CHARS = 700
_MIN_CHARS = 1


def _hard_wrap(segment: str, max_chars: int) -> list[str]:
    """Last-resort split for a single sentence longer than max_chars."""
    return [segment[i : i + max_chars].strip() for i in range(0, len(segment), max_chars)]


def _pack(sentences: list[str], max_chars: int) -> list[str]:
    """Greedily pack sentences into windows no larger than max_chars."""
    windows: list[str] = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > max_chars:
            if current:
                windows.append(current)
                current = ""
            windows.extend(_hard_wrap(sentence, max_chars))
            continue
        if current and len(current) + 1 + len(sentence) > max_chars:
            windows.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        windows.append(current)
    return windows


def _segments(text: str, max_chars: int) -> list[str]:
    segments: list[str] = []
    for paragraph in _PARAGRAPH_SPLIT.split(text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= max_chars:
            segments.append(paragraph)
        else:
            segments.extend(_pack(_SENTENCE_SPLIT.split(paragraph), max_chars))
    return [s for s in segments if len(s.strip()) >= _MIN_CHARS]


def fallback_chunks(
    text: str,
    source_id: str,
    title: str | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list[ChunkRecord]:
    """Chunk arbitrary text by paragraph/sentence when no legal structure exists."""
    context = title or source_id
    chunks: list[ChunkRecord] = []
    for idx, segment in enumerate(_segments(text, max_chars), start=1):
        chunks.append(
            ChunkRecord(
                chunk_id=f"{source_id}::p{idx}",
                text=segment,
                contextual_summary=context,
                metadata={
                    "source_id": source_id,
                    "act": title or source_id,
                    "jurisdiction": None,
                    "date": None,
                    "chapter": None,
                    "section": None,
                    "section_title": None,
                    "clause": None,
                    "section_ref": f"Paragraph {idx}",
                    "structure": "fallback",
                },
            )
        )
    return chunks


def chunk_document_or_fallback(
    document: Document,
    cleaned_text: str,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> tuple[list[ChunkRecord], bool]:
    """Structural SAC chunks if the document has structure, else fallback chunks.

    Returns (chunks, used_fallback).
    """
    structural = chunk_document(document)
    if structural:
        return structural, False
    return fallback_chunks(cleaned_text, document.source_id, document.title, max_chars), True
