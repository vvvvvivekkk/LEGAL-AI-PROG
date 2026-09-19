"""Metadata extraction for chunk records.

Builds the per-chunk metadata dict (source id, act/section reference,
jurisdiction, date) from the parsed Document/Chapter/Section/Clause tree in
src/ingestion/structure.py.
"""

from __future__ import annotations

from src.ingestion.structure import Chapter, Clause, Document, Section


def section_ref(section: Section, clause: Clause | None = None) -> str:
    """Human-readable reference, e.g. "Section 3" or "Section 3(a)"."""
    ref = f"Section {section.number}"
    if clause is not None:
        ref += f"({clause.label})"
    return ref


def build_metadata(
    document: Document,
    chapter: Chapter,
    section: Section,
    clause: Clause | None = None,
) -> dict:
    """Build the metadata dict attached to a chunk record."""
    return {
        "source_id": document.source_id,
        "act": document.title,
        "jurisdiction": document.jurisdiction,
        "date": document.enacted_date,
        "chapter": f"Chapter {chapter.number} — {chapter.name}",
        "section": section.number,
        "section_title": section.title,
        "clause": clause.label if clause is not None else None,
        "section_ref": section_ref(section, clause),
    }
