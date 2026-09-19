"""V6 — Proof Object.

The auditable output artifact: for each claim, which chunk(s) support it, the
verbatim span quoted from the cited source, the verdict each layer returned,
and the claim's contribution to the VCS. Serializable to JSON for the UI's
proof viewer. V6 doesn't judge anything itself — it assembles V1-V5 into one
interpretable trace.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from src.verification.types import context_text_by_id, token_jaccard
from src.verification.v1_citation import ClaimCitationResult
from src.verification.v2_entailment import ClaimEntailmentResult
from src.verification.v3_atomic import ClaimFidelityResult
from src.verification.v4_consistency import ClaimConsistencyResult
from src.verification.v5_vcs import VCSResult


@dataclass
class ClaimProof:
    claim_text: str
    supporting_chunk_ids: list[str]
    quoted_span: str
    verdicts: dict
    vcs_contribution: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProofObject:
    query: str
    answer_text: str
    vcs: float | None
    decision: str
    threshold: float
    abstained: bool
    claims: list[ClaimProof] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "answer_text": self.answer_text,
            "vcs": self.vcs,
            "decision": self.decision,
            "threshold": self.threshold,
            "abstained": self.abstained,
            "claims": [c.to_dict() for c in self.claims],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def _quoted_span(claim_text: str, chunk_ids: list[str], texts: dict[str, str]) -> str:
    """Verbatim text of the cited chunk that best matches the claim."""
    candidates = [(cid, texts.get(cid, "")) for cid in chunk_ids if texts.get(cid)]
    if not candidates:
        return ""
    best_cid, best_text = max(candidates, key=lambda ct: token_jaccard(claim_text, ct[1]))
    return best_text


def build_proof(
    query: str,
    answer_text: str,
    context_chunks: list[dict],
    v1: list[ClaimCitationResult],
    v2: list[ClaimEntailmentResult],
    v3: list[ClaimFidelityResult],
    v4: list[ClaimConsistencyResult] | None,
    vcs_result: VCSResult,
) -> ProofObject:
    """Assemble the Proof Object from all layer outputs.

    v1..v4 lists are aligned with the answer's claims. v4 may be None (V4 not
    run). vcs_result.per_claim is aligned too (empty when abstained).
    """
    texts = context_text_by_id(context_chunks)

    if vcs_result.abstained or not v1:
        return ProofObject(
            query=query,
            answer_text=answer_text,
            vcs=vcs_result.vcs,
            decision=vcs_result.decision,
            threshold=vcs_result.threshold,
            abstained=vcs_result.abstained,
            claims=[],
        )

    n = len(v1)
    proofs: list[ClaimProof] = []
    for i in range(n):
        cit = v1[i]
        ent = v2[i]
        fid = v3[i]
        con = v4[i] if v4 is not None else None
        claim_vcs = vcs_result.per_claim[i].vcs if i < len(vcs_result.per_claim) else 0.0

        # Prefer the entailing chunk V2 picked; fall back to existing citations.
        support_ids = [ent.best_chunk_id] if ent.best_chunk_id else list(cit.existing_ids)
        support_ids = [s for s in support_ids if s]

        verdicts = {
            "v1_citation": {
                "passed": cit.passed,
                "missing_ids": list(cit.missing_ids),
            },
            "v2_entailment": {
                "verdict": ent.verdict.value,
                "score": ent.score,
                "best_chunk_id": ent.best_chunk_id,
            },
            "v3_fidelity": {
                "fidelity": fid.fidelity,
                "atoms": [
                    {"text": a.text, "verdict": a.verdict.value} for a in fid.atoms
                ],
            },
            "v4_consistency": (
                {"consistency": con.consistency, "stable": con.stable}
                if con is not None
                else None
            ),
        }

        proofs.append(
            ClaimProof(
                claim_text=cit.claim_text,
                supporting_chunk_ids=support_ids,
                quoted_span=_quoted_span(cit.claim_text, support_ids, texts),
                verdicts=verdicts,
                vcs_contribution=claim_vcs,
            )
        )

    return ProofObject(
        query=query,
        answer_text=answer_text,
        vcs=vcs_result.vcs,
        decision=vcs_result.decision,
        threshold=vcs_result.threshold,
        abstained=vcs_result.abstained,
        claims=proofs,
    )
