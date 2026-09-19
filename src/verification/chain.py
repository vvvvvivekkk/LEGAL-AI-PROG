"""Verification chain: run V1-V6 in order over a generated Answer.

Later layers consume earlier ones, so order matters:
  V1 citation existence -> V2 entailment -> V3 atomic fidelity
  -> V4 self-consistency (optional; needs resamples)
  -> V5 VCS aggregation + abstention decision
  -> V6 Proof Object

Returns (VCSResult, ProofObject). If resamples aren't supplied, V4 is skipped
and its weight is excluded from the VCS normalisation.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.generation.generator import Answer
from src.verification.nli import NLIModel
from src.verification.v1_citation import check_citation_existence
from src.verification.v2_entailment import check_entailment_all
from src.verification.v3_atomic import check_fidelity_all
from src.verification.v4_consistency import self_consistency
from src.verification.v5_vcs import VCSConfig, VCSResult, aggregate_vcs
from src.verification.v6_proof import ProofObject, build_proof


@dataclass
class VerificationResult:
    vcs_result: VCSResult
    proof: ProofObject

    def to_dict(self) -> dict:
        return {"vcs": self.vcs_result.to_dict(), "proof": self.proof.to_dict()}


def verify_answer(
    answer: Answer,
    context_chunks: list[dict],
    nli: NLIModel,
    resamples: list[Answer] | None = None,
    config: VCSConfig | None = None,
) -> VerificationResult:
    config = config or VCSConfig()

    # Model declined outright — nothing to verify, but still produce a decision.
    if answer.abstained:
        vcs_result = aggregate_vcs(
            abstained=True,
            citation_flags=[], entailments=[], fidelities=[], consistencies=[],
            config=config,
        )
        proof = build_proof(
            answer.query, answer.raw_text, context_chunks,
            v1=[], v2=[], v3=[], v4=None, vcs_result=vcs_result,
        )
        return VerificationResult(vcs_result, proof)

    v1 = check_citation_existence(answer)
    v2 = check_entailment_all(answer.claims, context_chunks, nli)
    v3 = check_fidelity_all(answer.claims, context_chunks, nli)

    v4 = None
    consistencies: list[float | None]
    if resamples:
        v4 = self_consistency(answer, resamples)
        consistencies = [c.consistency for c in v4]
    else:
        consistencies = [None] * len(answer.claims)

    vcs_result = aggregate_vcs(
        abstained=False,
        citation_flags=[c.passed for c in v1],
        entailments=[e.verdict for e in v2],
        fidelities=[f.fidelity for f in v3],
        consistencies=consistencies,
        config=config,
    )

    # Restore real claim texts on the per-claim VCS records (aggregate uses
    # positional placeholders since it only sees signal lists).
    for claim_vcs, claim in zip(vcs_result.per_claim, answer.claims):
        claim_vcs.claim_text = claim.text

    proof = build_proof(
        answer.query, answer.raw_text, context_chunks,
        v1=v1, v2=v2, v3=v3, v4=v4, vcs_result=vcs_result,
    )
    return VerificationResult(vcs_result, proof)
