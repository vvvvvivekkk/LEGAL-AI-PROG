"""Tests for the general-knowledge fallback classifier and generator."""

from __future__ import annotations

import pytest

from src.generation.general_knowledge import (
    answer_from_general_knowledge,
    is_general_concept_question,
)


GENERAL = [
    "what is a non-disclosure agreement",
    "What is confidential information?",
    "Define an NDA",
    "What does 'mutual NDA' mean?",
    "Explain what an indemnity is",
    "what is the meaning of consideration in contract law",
]

DOCUMENT_SPECIFIC = [
    "What happens if the receiving party discloses confidential information to a third party?",
    "What is the term of this agreement?",
    "According to the document, what is confidential information?",
    "What is the governing law?",
    "Does the agreement allow disclosure to affiliates?",
    "How long must confidentiality be maintained?",
    "What is defined as confidential information in section 3?",
]


@pytest.mark.parametrize("query", GENERAL)
def test_general_concept_questions_are_detected(query):
    assert is_general_concept_question(query) is True


@pytest.mark.parametrize("query", DOCUMENT_SPECIFIC)
def test_document_questions_are_not_treated_as_general(query):
    """These must keep abstaining — the corpus is supposed to answer them."""
    assert is_general_concept_question(query) is False


def test_empty_query_is_not_general():
    assert is_general_concept_question("") is False
    assert is_general_concept_question("   ") is False


def test_answer_from_general_knowledge_uses_its_own_system_prompt():
    seen = {}

    class RecordingAdapter:
        def complete(self, system, user):
            seen["system"] = system
            seen["user"] = user
            return "  An NDA is a contract restricting disclosure.  "

    out = answer_from_general_knowledge("what is an NDA", RecordingAdapter())
    assert out == "An NDA is a contract restricting disclosure."
    assert "own knowledge" in seen["system"]
    assert "Do NOT cite chunk ids" in seen["system"]
    assert seen["user"] == "what is an NDA"
