"""V1 — Citation Existence (deterministic).

The cheapest, hardest gate: every chunk id a claim cites must actually exist
in the retrieved context. A citation to an id that was never retrieved is a
fabricated citation — the answer is asserting a source that isn't there. This
runs first because later layers (entailment, fidelity) are meaningless against
a source that doesn't exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.generation.generator import Answer


@dataclass
class ClaimCitationResult:
    claim_text: str
    cited_chunk_ids: list[str]
    existing_ids: list[str] = field(default_factory=list)
    missing_ids: list[str] = field(default_factory=list)

    @property
    def has_citation(self) -> bool:
        return bool(self.cited_chunk_ids)

    @property
    def passed(self) -> bool:
        """Passes only if it cites something and every cited id exists."""
        return self.has_citation and not self.missing_ids

    def to_dict(self) -> dict:
        return {
            "claim_text": self.claim_text,
            "cited_chunk_ids": list(self.cited_chunk_ids),
            "existing_ids": list(self.existing_ids),
            "missing_ids": list(self.missing_ids),
            "passed": self.passed,
        }


def check_citation_existence(answer: Answer) -> list[ClaimCitationResult]:
    """Check each claim's citations against the answer's retrieved context ids."""
    context_ids = set(answer.context_chunk_ids)
    results: list[ClaimCitationResult] = []
    for claim in answer.claims:
        existing = [cid for cid in claim.cited_chunk_ids if cid in context_ids]
        missing = [cid for cid in claim.cited_chunk_ids if cid not in context_ids]
        results.append(
            ClaimCitationResult(
                claim_text=claim.text,
                cited_chunk_ids=list(claim.cited_chunk_ids),
                existing_ids=existing,
                missing_ids=missing,
            )
        )
    return results
