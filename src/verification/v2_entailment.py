"""V2 — Entailment / Support (NLI).

V1 confirms a cited chunk exists; V2 confirms it actually *supports* the claim.
Each (claim, cited chunk) pair is classified ENTAILS / CONTRADICTS / NEUTRAL by
an NLI model. A claim can cite several chunks, so we take the most favourable
outcome across its cited chunks:

  - if any cited chunk ENTAILS the claim  -> ENTAILS (record which chunk)
  - else if any CONTRADICTS               -> CONTRADICTS
  - else                                  -> NEUTRAL

Only ENTAILS is treated as supported downstream. Contradiction is worse than
neutral: it means the cited source actively refutes the claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.generation.parser import Claim
from src.verification.nli import NLIModel
from src.verification.types import Entailment, context_text_by_id


@dataclass
class ClaimEntailmentResult:
    claim_text: str
    verdict: Entailment
    best_chunk_id: str | None = None
    score: float = 0.0
    per_chunk: list[dict] = field(default_factory=list)

    @property
    def supported(self) -> bool:
        return self.verdict == Entailment.ENTAILS

    def to_dict(self) -> dict:
        return {
            "claim_text": self.claim_text,
            "verdict": self.verdict.value,
            "best_chunk_id": self.best_chunk_id,
            "score": self.score,
            "per_chunk": list(self.per_chunk),
        }


def _combine(per_chunk: list[dict]) -> tuple[Entailment, str | None, float]:
    entailing = [p for p in per_chunk if p["verdict"] == Entailment.ENTAILS]
    if entailing:
        best = max(entailing, key=lambda p: p["score"])
        return Entailment.ENTAILS, best["chunk_id"], best["score"]
    contradicting = [p for p in per_chunk if p["verdict"] == Entailment.CONTRADICTS]
    if contradicting:
        best = max(contradicting, key=lambda p: p["score"])
        return Entailment.CONTRADICTS, best["chunk_id"], best["score"]
    if per_chunk:
        best = max(per_chunk, key=lambda p: p["score"])
        return Entailment.NEUTRAL, best["chunk_id"], best["score"]
    return Entailment.NEUTRAL, None, 0.0


def check_entailment(
    claim: Claim,
    context_chunks: list[dict],
    nli: NLIModel,
) -> ClaimEntailmentResult:
    """Classify a claim against each of its cited chunks and combine."""
    texts = context_text_by_id(context_chunks)
    per_chunk: list[dict] = []
    for cid in claim.cited_chunk_ids:
        premise = texts.get(cid)
        if not premise:
            continue  # missing citation is V1's concern, not V2's
        label, score = nli.classify(premise, claim.text)
        per_chunk.append({"chunk_id": cid, "verdict": label, "score": score})

    verdict, best_id, score = _combine(per_chunk)
    return ClaimEntailmentResult(
        claim_text=claim.text,
        verdict=verdict,
        best_chunk_id=best_id,
        score=score,
        per_chunk=[{**p, "verdict": p["verdict"].value} for p in per_chunk],
    )


def check_entailment_all(
    claims: list[Claim],
    context_chunks: list[dict],
    nli: NLIModel,
) -> list[ClaimEntailmentResult]:
    return [check_entailment(c, context_chunks, nli) for c in claims]
