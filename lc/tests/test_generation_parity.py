"""The LCEL prompt and output parser must match src/generation exactly."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from langchain_core.documents import Document

from lc.generation import ANSWER_PROMPT, CitationOutputParser, prompt_inputs
from src.generation.generator import parse_answer
from src.generation.prompt import build_prompt

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / "data" / "eval" / "ablation_cache.json"


def _cached() -> list[dict]:
    return json.loads(CACHE.read_text(encoding="utf-8"))


def _as_doc(row: dict) -> Document:
    return Document(
        page_content=row["text"],
        metadata={
            "chunk_id": row["chunk_id"],
            "contextual_summary": row.get("contextual_summary", ""),
            "chunk_metadata": row.get("metadata") or {},
        },
    )


@pytest.mark.parametrize("item", _cached(), ids=lambda i: i["query"][:40])
def test_rendered_prompt_is_byte_identical(item):
    system, user = build_prompt(item["query"], item["context_chunks"])
    messages = ANSWER_PROMPT.invoke(
        prompt_inputs({"question": item["query"], "context": [_as_doc(r) for r in item["context_chunks"]]})
    ).to_messages()
    assert [m.type for m in messages] == ["system", "human"]
    assert messages[0].content == system
    assert messages[1].content == user


EDGE_CASES = [
    "INSUFFICIENT_CONTEXT: nothing here.",
    "  INSUFFICIENT_CONTEXT: leading space.",
    "A claim. [a::s1]\nAnother. [a::s2][b::p3]\n\nNo citation here.",
    "Comma form. [a::s1, b::s2]\nDuplicate ids. [a::s1][a::s1]",
    "Comma in a source id. [VIVINT SOLAR, INC. - AGREEMENT::p1, x::s2]",
    "Full-width brackets【a::p18】.\nMixed ［b::s1］ and [c::s2].",
    "Empty brackets [] and [ ] only.",
    "Text with {braces} and a citation. [x::p1]",
    "",
]


@pytest.mark.parametrize(
    "raw",
    [i["raw_text"] for i in _cached()] + [t for i in _cached() for t in i["resample_texts"]] + EDGE_CASES,
)
def test_parser_matches_src(raw):
    want = parse_answer("q", raw, [])
    got = CitationOutputParser().parse(raw)
    assert got.abstained == want.abstained
    assert [(c.text, c.cited_chunk_ids) for c in got.claims] == [
        (c.text, c.cited_chunk_ids) for c in want.claims
    ]
    assert got.malformed_lines == want.malformed_lines
