"""Generation entry point: build prompt -> call adapter -> parse into an Answer.

`Answer` is the structured artifact phase-5 verification consumes: the raw
model text plus the parsed list of (claim, cited_chunk_ids). It also carries
the context chunk ids the answer was generated against, so V1 (citation
existence) can check citations against exactly what was retrieved.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.generation.base import LLMAdapter
from src.generation.parser import Claim, is_abstention, parse_claims
from src.generation.prompt import build_prompt


@dataclass
class Answer:
    query: str
    raw_text: str
    claims: list[Claim] = field(default_factory=list)
    context_chunk_ids: list[str] = field(default_factory=list)
    abstained: bool = False
    malformed_lines: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "raw_text": self.raw_text,
            "claims": [c.to_dict() for c in self.claims],
            "context_chunk_ids": list(self.context_chunk_ids),
            "abstained": self.abstained,
            "malformed_lines": list(self.malformed_lines),
        }


def parse_answer(query: str, raw_text: str, context_chunks: list[dict], strict: bool = False) -> Answer:
    """Turn a raw model response into a structured Answer."""
    context_ids = [c["chunk_id"] for c in context_chunks]
    if is_abstention(raw_text):
        return Answer(
            query=query,
            raw_text=raw_text,
            claims=[],
            context_chunk_ids=context_ids,
            abstained=True,
        )
    claims, malformed = parse_claims(raw_text, strict=strict)
    return Answer(
        query=query,
        raw_text=raw_text,
        claims=claims,
        context_chunk_ids=context_ids,
        abstained=False,
        malformed_lines=malformed,
    )


def generate(
    query: str,
    context_chunks: list[dict],
    adapter: LLMAdapter,
    strict: bool = False,
) -> Answer:
    """Generate a citation-forced answer for a query over retrieved context."""
    system, user = build_prompt(query, context_chunks)
    raw_text = adapter.complete(system, user)
    return parse_answer(query, raw_text, context_chunks, strict=strict)
