"""V4 — Self-Consistency Cross-Check.

Hallucinated claims tend to be unstable: regenerate the answer a few times and
a fabricated detail often won't recur, while a well-grounded claim shows up
every time. V4 resamples generation N times and, for each claim in the primary
answer, measures how many resamples contain a matching claim. Claims below a
recurrence threshold are flagged unstable (SelfCheckGPT-style).

Matching is by token-set overlap on claim text — robust to small wording
changes without needing another model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.generation.base import LLMAdapter
from src.generation.generator import Answer, generate
from src.generation.parser import Claim
from src.verification.types import token_jaccard

DEFAULT_MATCH_THRESHOLD = 0.5
DEFAULT_STABILITY_THRESHOLD = 0.5


@dataclass
class ClaimConsistencyResult:
    claim_text: str
    consistency: float
    n_samples: int
    n_matches: int
    stable: bool

    def to_dict(self) -> dict:
        return {
            "claim_text": self.claim_text,
            "consistency": self.consistency,
            "n_samples": self.n_samples,
            "n_matches": self.n_matches,
            "stable": self.stable,
        }


def _sample_contains(claim: Claim, sample: Answer, match_threshold: float) -> bool:
    return any(
        token_jaccard(claim.text, other.text) >= match_threshold
        for other in sample.claims
    )


def self_consistency(
    primary: Answer,
    resamples: list[Answer],
    match_threshold: float = DEFAULT_MATCH_THRESHOLD,
    stability_threshold: float = DEFAULT_STABILITY_THRESHOLD,
) -> list[ClaimConsistencyResult]:
    """Score each primary claim by how many resamples reproduce it."""
    n = len(resamples)
    results: list[ClaimConsistencyResult] = []
    for claim in primary.claims:
        matches = sum(1 for s in resamples if _sample_contains(claim, s, match_threshold))
        consistency = matches / n if n else 0.0
        results.append(
            ClaimConsistencyResult(
                claim_text=claim.text,
                consistency=consistency,
                n_samples=n,
                n_matches=matches,
                stable=consistency >= stability_threshold,
            )
        )
    return results


def resample_answers(
    query: str,
    context_chunks: list[dict],
    adapter: LLMAdapter,
    n: int,
) -> list[Answer]:
    """Generate N answers for the same query/context (for a stochastic adapter)."""
    return [generate(query, context_chunks, adapter) for _ in range(n)]
