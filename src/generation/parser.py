"""Parse a citation-forced LLM response into structured claims.

The prompt (src/generation/prompt.py) constrains the model to one claim per
line, each terminated by one or more [chunk_id] citations. This parser turns
that text into (claim, cited_chunk_ids) records that phase-5 verification
consumes, and flags lines that violate the contract (a factual line with no
citation) as malformed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.generation.prompt import ABSTENTION_MARKER

# Models sometimes cite with full-width brackets (【id】, ［id］) instead of [id];
# both mean the same citation.
_CITATION_RE = re.compile(r"[\[［【]([^\[\]［］【】]*)[\]］】]")


class MalformedAnswerError(ValueError):
    """Raised in strict mode when a factual line carries no valid citation."""


@dataclass
class Claim:
    text: str
    cited_chunk_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"text": self.text, "cited_chunk_ids": list(self.cited_chunk_ids)}


def split_citation_group(group: str) -> list[str]:
    """Split one bracket's contents into chunk ids.

    Chunk ids always contain '::', but a source id may itself contain a comma
    (a file named "VIVINT SOLAR, INC. - AGREEMENT.txt"), so a comma only
    separates ids when the piece before it already holds a '::'. Pieces without
    one are joined back onto the id they belong to.
    """
    parts = group.split(",")
    if not any("::" in p for p in parts):
        return [p.strip() for p in parts if p.strip()]
    ids: list[str] = []
    pending: list[str] = []
    for part in parts:
        pending.append(part)
        if "::" in part:
            ids.append(",".join(pending).strip())
            pending = []
    ids.extend(p.strip() for p in pending if p.strip())
    return ids


def extract_citations(line: str) -> list[str]:
    """Pull chunk ids out of a line's [..] brackets.

    Supports both multi-bracket ([a][b]) and comma-separated ([a, b]) forms.
    Empty or whitespace-only brackets contribute no ids.
    """
    ids: list[str] = []
    for group in _CITATION_RE.findall(line):
        for cid in split_citation_group(group):
            if cid:
                ids.append(cid)
    # de-duplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for cid in ids:
        if cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def strip_citations(line: str) -> str:
    """Return the claim text with its [..] citations removed."""
    return _CITATION_RE.sub("", line).strip()


def is_abstention(raw_text: str) -> bool:
    return raw_text.strip().startswith(f"{ABSTENTION_MARKER}:")


def parse_claims(raw_text: str, strict: bool = False) -> tuple[list[Claim], list[str]]:
    """Parse response text into (claims, malformed_lines).

    A content line with at least one citation becomes a Claim. A content line
    with none is malformed. In strict mode the first malformed line raises
    MalformedAnswerError.
    """
    claims: list[Claim] = []
    malformed: list[str] = []

    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        ids = extract_citations(line)
        if ids:
            claims.append(Claim(text=strip_citations(line), cited_chunk_ids=ids))
        else:
            if strict:
                raise MalformedAnswerError(f"claim line without citation: {line!r}")
            malformed.append(line)

    return claims, malformed
