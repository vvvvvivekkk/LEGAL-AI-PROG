"""V3 — Atomic Claim Decomposition + Fidelity Scoring.

A single cited sentence can bundle several assertions ("the deposit is two
months' rent and must be refunded in thirty days"). V2 scores the sentence as
a whole; V3 breaks it into atomic sub-claims and verifies each one
independently against the same cited evidence, so a claim that is half-right
doesn't pass as fully supported. The per-claim fidelity score is the fraction
of atomic sub-claims the evidence entails.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.generation.parser import Claim
from src.verification.nli import NLIModel
from src.verification.types import Entailment
from src.verification.v2_entailment import check_entailment

# Split points for atomic decomposition: semicolons, " and "/" or " conjunctions,
# and sentence boundaries. Deliberately simple/extractive — no LLM — matching
# the phase-1 SAC philosophy; an LLM decomposer can slot in behind this later.
_SPLIT_RE = re.compile(r"\s*;\s*|\s+and\s+|\s+or\s+|\.\s+")


def decompose(text: str) -> list[str]:
    """Break a claim into atomic sub-claims. Always returns at least one part."""
    parts = [p.strip(" .") for p in _SPLIT_RE.split(text)]
    atoms = [p for p in parts if p]
    return atoms or [text.strip()]


@dataclass
class AtomResult:
    text: str
    verdict: Entailment
    score: float

    @property
    def entailed(self) -> bool:
        return self.verdict == Entailment.ENTAILS


@dataclass
class ClaimFidelityResult:
    claim_text: str
    atoms: list[AtomResult] = field(default_factory=list)

    @property
    def fidelity(self) -> float:
        if not self.atoms:
            return 0.0
        return sum(1 for a in self.atoms if a.entailed) / len(self.atoms)

    def to_dict(self) -> dict:
        return {
            "claim_text": self.claim_text,
            "fidelity": self.fidelity,
            "atoms": [
                {"text": a.text, "verdict": a.verdict.value, "score": a.score}
                for a in self.atoms
            ],
        }


def check_fidelity(
    claim: Claim,
    context_chunks: list[dict],
    nli: NLIModel,
) -> ClaimFidelityResult:
    """Decompose a claim and entailment-check each atom against its cited chunks."""
    atoms: list[AtomResult] = []
    for atom_text in decompose(claim.text):
        atom_claim = Claim(text=atom_text, cited_chunk_ids=list(claim.cited_chunk_ids))
        entail = check_entailment(atom_claim, context_chunks, nli)
        atoms.append(AtomResult(text=atom_text, verdict=entail.verdict, score=entail.score))
    return ClaimFidelityResult(claim_text=claim.text, atoms=atoms)


def check_fidelity_all(
    claims: list[Claim],
    context_chunks: list[dict],
    nli: NLIModel,
) -> list[ClaimFidelityResult]:
    return [check_fidelity(c, context_chunks, nli) for c in claims]
