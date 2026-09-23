"""SAC and paragraph-fallback chunking as LangChain TextSplitters.

LangChain's built-in splitters cannot produce these chunks:
RecursiveCharacterTextSplitter merges adjacent short paragraphs up to
chunk_size (src/ keeps every paragraph separate), and no stock splitter cuts
on Act/Chapter/Section/Clause boundaries or attaches a chunk id and contextual
summary. So both are custom splitters. Each reads one loaded Document
(lc/loaders.py) and emits one Document per chunk:

    page_content                 the chunk text
    metadata["chunk_id"]         e.g. "urban_tenancy_act_2019::s4:b" / "nda::p12"
    metadata["contextual_summary"]
    metadata["chunk_metadata"]   the per-chunk metadata dict, exactly as src/

The legal-structure parser (src/ingestion/structure.py) and the metadata
builder are reused as-is: they are ingestion, not chunking, and duplicating a
regex parser would only add a way for the two versions to drift. The chunk
cutting itself is implemented here, and lc/tests/test_chunk_identity.py checks
it against src/chunking chunk by chunk.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from langchain_core.documents import Document
from langchain_text_splitters import TextSplitter

from src.ingestion.metadata import build_metadata
from src.ingestion.structure import Document as ParsedDocument
from src.ingestion.structure import Section, parse_document

DEFAULT_MAX_CHARS = 700

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _chunk_doc(chunk_id: str, text: str, summary: str, metadata: dict) -> Document:
    return Document(
        page_content=text,
        metadata={
            "chunk_id": chunk_id,
            "contextual_summary": summary,
            "chunk_metadata": metadata,
        },
    )


def to_chunk_dict(doc: Document) -> dict:
    """A chunk Document back in src/'s ChunkRecord.to_dict() shape."""
    return {
        "chunk_id": doc.metadata["chunk_id"],
        "text": doc.page_content,
        "contextual_summary": doc.metadata["contextual_summary"],
        "metadata": dict(doc.metadata["chunk_metadata"]),
    }


class _PerDocumentSplitter(TextSplitter):
    """Base for splitters whose output depends on the whole parsed document.

    TextSplitter.split_documents copies the parent metadata onto every piece,
    which cannot express per-chunk ids and summaries, so split_documents is
    overridden and split_text only serves the plain-string interface.
    """

    def __init__(self, **kwargs):
        # chunk_size is meaningless for structural cuts; TextSplitter still
        # validates it, so give it a value that never constrains anything.
        kwargs.setdefault("chunk_size", 10**9)
        kwargs.setdefault("chunk_overlap", 0)
        super().__init__(**kwargs)

    def chunk_parsed(self, parsed: ParsedDocument, cleaned: str) -> list[Document]:
        raise NotImplementedError

    def split_text(self, text: str) -> list[str]:
        parsed = parse_document(text, source_id="text")
        return [d.page_content for d in self.chunk_parsed(parsed, text)]

    def split_documents(self, documents: Iterable[Document]) -> list[Document]:
        out: list[Document] = []
        for doc in documents:
            source_id = doc.metadata["source_id"]
            parsed = parse_document(doc.page_content, source_id=source_id)
            out.extend(self.chunk_parsed(parsed, doc.page_content))
        return out

    def transform_documents(self, documents: Sequence[Document], **kwargs) -> list[Document]:
        return self.split_documents(documents)


class SACTextSplitter(_PerDocumentSplitter):
    """Summary-Augmented Chunking: one chunk per section body and per clause,
    each carrying "Section N. Title." plus the section's own first sentence."""

    @staticmethod
    def summary_for(section: Section) -> str:
        heading = f"Section {section.number}. {section.title}."
        first = section.first_sentence
        if first and first.rstrip(".") != section.title.rstrip("."):
            return f"{heading} {first}"
        return heading

    def chunk_parsed(self, parsed: ParsedDocument, cleaned: str) -> list[Document]:
        out: list[Document] = []
        for chapter in parsed.chapters:
            for section in chapter.sections:
                summary = self.summary_for(section)
                base = f"{parsed.source_id}::s{section.number}"
                if section.body_text:
                    out.append(
                        _chunk_doc(base, section.body_text, summary,
                                   build_metadata(parsed, chapter, section))
                    )
                for clause in section.clauses:
                    out.append(
                        _chunk_doc(f"{base}:{clause.label}", clause.text, summary,
                                   build_metadata(parsed, chapter, section, clause))
                    )
        return out


class ParagraphFallbackSplitter(_PerDocumentSplitter):
    """Paragraph chunks for documents with no legal structure; paragraphs over
    max_chars are packed greedily by sentence, a single over-long sentence is
    hard-wrapped. Marked structure="fallback" in metadata."""

    def __init__(self, max_chars: int = DEFAULT_MAX_CHARS, **kwargs):
        super().__init__(**kwargs)
        self.max_chars = max_chars

    def _pack(self, sentences: list[str]) -> list[str]:
        windows: list[str] = []
        current = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) > self.max_chars:
                if current:
                    windows.append(current)
                    current = ""
                windows.extend(
                    sentence[i : i + self.max_chars].strip()
                    for i in range(0, len(sentence), self.max_chars)
                )
                continue
            if current and len(current) + 1 + len(sentence) > self.max_chars:
                windows.append(current)
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            windows.append(current)
        return windows

    def segments(self, text: str) -> list[str]:
        out: list[str] = []
        for paragraph in _PARAGRAPH_SPLIT.split(text):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if len(paragraph) <= self.max_chars:
                out.append(paragraph)
            else:
                out.extend(self._pack(_SENTENCE_SPLIT.split(paragraph)))
        return [s for s in out if s.strip()]

    def chunk_parsed(self, parsed: ParsedDocument, cleaned: str) -> list[Document]:
        source_id, title = parsed.source_id, parsed.title
        out: list[Document] = []
        for idx, segment in enumerate(self.segments(cleaned), start=1):
            out.append(
                _chunk_doc(
                    f"{source_id}::p{idx}",
                    segment,
                    title or source_id,
                    {
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
        return out


def split_with_fallback(doc: Document) -> tuple[list[Document], bool]:
    """SAC chunks if the document has legal structure, else fallback chunks.

    Returns (chunks, used_fallback), like src.chunking.fallback.chunk_document_or_fallback.
    """
    structural = SACTextSplitter().split_documents([doc])
    if structural:
        return structural, False
    return ParagraphFallbackSplitter().split_documents([doc]), True
