"""Summary-Augmented Chunking (SAC).

Chunks are cut at structural boundaries (section body / clause), not fixed
size windows, and each chunk carries a contextual summary of its parent
section so retrieval doesn't lose the surrounding legal context. The summary
is a simple extractive one (section heading + first sentence of the section)
-- no LLM call, per phase 1 scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.ingestion.metadata import build_metadata
from src.ingestion.structure import Chapter, Clause, Document, Section


@dataclass
class ChunkRecord:
    chunk_id: str
    text: str
    contextual_summary: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "contextual_summary": self.contextual_summary,
            "metadata": dict(self.metadata),
        }


def contextual_summary_for_section(section: Section) -> str:
    """Extractive contextual summary: section heading + its own first sentence."""
    heading = f"Section {section.number}. {section.title}."
    first_sentence = section.first_sentence
    if first_sentence and first_sentence.rstrip(".") != section.title.rstrip("."):
        return f"{heading} {first_sentence}"
    return heading


def _chunk_id(source_id: str, section: Section, clause: Clause | None = None) -> str:
    base = f"{source_id}::s{section.number}"
    if clause is not None:
        return f"{base}:{clause.label}"
    return base


def chunk_section(document: Document, chapter: Chapter, section: Section) -> list[ChunkRecord]:
    """Emit chunk records for one section: a body chunk (if any) + one per clause."""
    chunks: list[ChunkRecord] = []
    summary = contextual_summary_for_section(section)

    if section.body_text:
        chunks.append(
            ChunkRecord(
                chunk_id=_chunk_id(document.source_id, section),
                text=section.body_text,
                contextual_summary=summary,
                metadata=build_metadata(document, chapter, section),
            )
        )

    for clause in section.clauses:
        chunks.append(
            ChunkRecord(
                chunk_id=_chunk_id(document.source_id, section, clause),
                text=clause.text,
                contextual_summary=summary,
                metadata=build_metadata(document, chapter, section, clause),
            )
        )

    return chunks


def chunk_document(document: Document) -> list[ChunkRecord]:
    """Emit chunk records for an entire parsed document, in document order."""
    chunks: list[ChunkRecord] = []
    for chapter in document.chapters:
        for section in chapter.sections:
            chunks.extend(chunk_section(document, chapter, section))
    return chunks


def chunk_corpus(documents: list[Document]) -> list[ChunkRecord]:
    """Emit chunk records for a list of parsed documents."""
    chunks: list[ChunkRecord] = []
    for document in documents:
        chunks.extend(chunk_document(document))
    return chunks
