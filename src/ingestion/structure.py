"""Structural parsing of the Act -> Chapter -> Section -> Clause hierarchy.

The sample synthetic statutes (data/sample/*.txt) all follow the same shape:

    THE FICTIONAL <NAME> ACT, <YEAR>
    Jurisdiction: <jurisdiction>
    Enacted: <date>

    CHAPTER <roman numeral> - <chapter name>

    Section <n>. <section title>.
    <optional intro/body text>
    (<n>) <numbered sub-clause text>          -- OR --
    Clause (<letter>): <lettered clause text>

This module turns that raw text into a `Document` tree. It's a hand-rolled
line-based parser (regex per line), not a general-purpose statute parser --
good enough for the synthetic corpus this phase is built and tested against.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_TITLE_RE = re.compile(r"^THE\s+.+\bACT\b.*$", re.IGNORECASE)
_JURISDICTION_RE = re.compile(r"^Jurisdiction:\s*(.+)$", re.IGNORECASE)
_ENACTED_RE = re.compile(r"^Enacted:\s*(.+)$", re.IGNORECASE)
_CHAPTER_RE = re.compile(r"^CHAPTER\s+([IVXLCDM]+)\s*[—\-]\s*(.+)$")
# Section numbers may carry a letter suffix, as in real Acts ("Section 498A.", "Section 13B.").
_SECTION_RE = re.compile(r"^Section\s+(\d+[A-Z]{0,2})\.\s*(.+?)\.?\s*$")
_NUMBERED_CLAUSE_RE = re.compile(r"^\((\d+)\)\s*(.+)$")
_LETTERED_CLAUSE_RE = re.compile(r"^Clause\s+\(([a-zA-Z])\):\s*(.+)$")


@dataclass
class Clause:
    label: str  # e.g. "1" or "a"
    text: str


@dataclass
class Section:
    number: str
    title: str
    body_lines: list[str] = field(default_factory=list)
    clauses: list[Clause] = field(default_factory=list)

    @property
    def body_text(self) -> str:
        return " ".join(self.body_lines).strip()

    @property
    def first_sentence(self) -> str:
        """First sentence of this section's own content (body, else first clause)."""
        source = self.body_text
        if not source and self.clauses:
            source = self.clauses[0].text
        if not source:
            return ""
        # Split on the first sentence-ending period.
        match = re.search(r"^(.*?[.!?])(\s|$)", source)
        return match.group(1).strip() if match else source.strip()


@dataclass
class Chapter:
    number: str
    name: str
    sections: list[Section] = field(default_factory=list)


@dataclass
class Document:
    source_id: str
    title: str
    jurisdiction: str | None = None
    enacted_date: str | None = None
    chapters: list[Chapter] = field(default_factory=list)


def parse_document(cleaned_text: str, source_id: str) -> Document:
    """Parse a cleaned statute text into its Act/Chapter/Section/Clause hierarchy."""
    lines = [line.strip() for line in cleaned_text.split("\n")]

    title = ""
    jurisdiction = None
    enacted_date = None
    chapters: list[Chapter] = []

    current_chapter: Chapter | None = None
    current_section: Section | None = None

    def flush_section() -> None:
        nonlocal current_section
        if current_section is not None and current_chapter is not None:
            current_chapter.sections.append(current_section)
        current_section = None

    for line in lines:
        if not line:
            continue

        if not title and _TITLE_RE.match(line):
            title = line
            continue

        m = _JURISDICTION_RE.match(line)
        if m:
            jurisdiction = m.group(1).strip()
            continue

        m = _ENACTED_RE.match(line)
        if m:
            enacted_date = m.group(1).strip()
            continue

        m = _CHAPTER_RE.match(line)
        if m:
            flush_section()
            current_chapter = Chapter(number=m.group(1), name=m.group(2).strip())
            chapters.append(current_chapter)
            continue

        m = _SECTION_RE.match(line)
        if m:
            flush_section()
            current_section = Section(number=m.group(1), title=m.group(2).strip())
            continue

        m = _LETTERED_CLAUSE_RE.match(line)
        if m and current_section is not None:
            current_section.clauses.append(Clause(label=m.group(1).lower(), text=m.group(2).strip()))
            continue

        m = _NUMBERED_CLAUSE_RE.match(line)
        if m and current_section is not None:
            current_section.clauses.append(Clause(label=m.group(1), text=m.group(2).strip()))
            continue

        # Otherwise: plain body/intro text belonging to the current section.
        if current_section is not None:
            current_section.body_lines.append(line)

    flush_section()

    if not title:
        title = source_id

    return Document(
        source_id=source_id,
        title=title,
        jurisdiction=jurisdiction,
        enacted_date=enacted_date,
        chapters=chapters,
    )
