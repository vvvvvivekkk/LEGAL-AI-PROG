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
from src.verification.types import Entailment
from src.verification.v1_citation import ClaimCitationResult, check_citation_existence
from src.verification.v2_entailment import ClaimEntailmentResult, check_entailment_all
from src.verification.v3_atomic import ClaimFidelityResult, check_fidelity_all
from src.verification.v4_consistency import self_consistency
from src.verification.v5_vcs import VCSConfig, VCSResult, aggregate_vcs
from src.verification.v6_proof import ProofObject, build_proof


@dataclass
class VerificationResult:
    vcs_result: VCSResult
    proof: ProofObject | None

    def to_dict(self) -> dict:
        return {
            "vcs": self.vcs_result.to_dict(),
            "proof": self.proof.to_dict() if self.proof is not None else None,
        }


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
        proof = (
            build_proof(
                answer.query, answer.raw_text, context_chunks,
                v1=[], v2=[], v3=[], v4=None, vcs_result=vcs_result,
            )
            if config.enable_v6
            else None
        )
        return VerificationResult(vcs_result, proof)

    # A disabled layer is not run at all; downstream code sees a neutral
    # placeholder for it and V5 drops its term from the VCS normalisation.
    n_claims = len(answer.claims)
    v1 = (
        check_citation_existence(answer)
        if config.enable_v1
        else _skipped_citations(answer)
    )
    v2 = (
        check_entailment_all(answer.claims, context_chunks, nli)
        if config.enable_v2
        else _skipped_entailments(answer)
    )
    v3 = (
        check_fidelity_all(answer.claims, context_chunks, nli)
        if config.enable_v3
        else [ClaimFidelityResult(claim_text=c.text, atoms=[]) for c in answer.claims]
    )

    v4 = None
    consistencies: list[float | None]
    if resamples and config.enable_v4:
        v4 = self_consistency(answer, resamples)
        consistencies = [c.consistency for c in v4]
    else:
        consistencies = [None] * n_claims

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

    proof = (
        build_proof(
            answer.query, answer.raw_text, context_chunks,
            v1=v1, v2=v2, v3=v3, v4=v4, vcs_result=vcs_result,
        )
        if config.enable_v6
        else None
    )
    return VerificationResult(vcs_result, proof)


def _skipped_citations(answer: Answer) -> list[ClaimCitationResult]:
    """Placeholder V1 records for an ablation run with the V1 gate disabled.

    Every cited id is reported as existing, so nothing is gated on citations.
    """
    return [
        ClaimCitationResult(
            claim_text=c.text,
            cited_chunk_ids=list(c.cited_chunk_ids),
            existing_ids=list(c.cited_chunk_ids),
            missing_ids=[],
        )
        for c in answer.claims
    ]


def _skipped_entailments(answer: Answer) -> list[ClaimEntailmentResult]:
    """Placeholder V2 records for an ablation run with V2 disabled."""
    return [
        ClaimEntailmentResult(claim_text=c.text, verdict=Entailment.NEUTRAL)
        for c in answer.claims
    ]
