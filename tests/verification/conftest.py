"""Shared verification-test helpers: a controllable fake NLI and sample data."""

from __future__ import annotations

import pytest

from src.verification.types import Entailment


class FakeNLI:
    """Rule-driven NLI stub.

    `rules` is a list of (premise_substr, hypothesis_substr, label, score). The
    first rule whose substrings both appear (case-insensitive) wins. Falls back
    to NEUTRAL. Lets tests hand-craft ENTAILS / CONTRADICTS / NEUTRAL outcomes
    without a model download.
    """

    def __init__(self, rules: list[tuple[str, str, Entailment, float]] | None = None):
        self.rules = rules or []

    def classify(self, premise: str, hypothesis: str) -> tuple[Entailment, float]:
        p, h = premise.lower(), hypothesis.lower()
        for prem_sub, hyp_sub, label, score in self.rules:
            if prem_sub.lower() in p and hyp_sub.lower() in h:
                return label, score
        return Entailment.NEUTRAL, 0.5


@pytest.fixture
def make_nli():
    """Factory fixture: make_nli(rules) -> FakeNLI, usable without importing conftest."""
    def _make(rules=None):
        return FakeNLI(rules)

    return _make


@pytest.fixture
def context_chunks():
    return [
        {
            "chunk_id": "urban_tenancy_act_2019::s4:b",
            "text": "The landlord must refund the security deposit within thirty days of the tenant vacating.",
            "contextual_summary": "Section 4. Security deposit limits.",
            "metadata": {"section_ref": "Section 4(b)"},
        },
        {
            "chunk_id": "urban_tenancy_act_2019::s4:a",
            "text": "The security deposit shall not exceed two months' rent for residential premises.",
            "contextual_summary": "Section 4. Security deposit limits.",
            "metadata": {"section_ref": "Section 4(a)"},
        },
    ]
