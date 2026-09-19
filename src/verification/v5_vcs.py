"""V5 — Verification Confidence Score (VCS) + abstention decision.

Aggregates the per-claim signals from V1-V4 into one interpretable score and
turns it into an answer/abstain decision.

Per-claim VCS
-------------
V1 (citation existence) and a V2 CONTRADICTS verdict are *hard gates*: either
one zeroes the claim, because a fabricated citation or a source that refutes
the claim cannot be rescued by fidelity or consistency.

Otherwise the claim score is a weighted mean of:
    entailment component  = 1.0 if V2 == ENTAILS else 0.0   (weight w_entail)
    fidelity              = V3 fraction of atoms entailed    (weight w_fidelity)
    consistency           = V4 recurrence across resamples   (weight w_consistency)

    claim_vcs = Σ(component · weight) / Σ(weight)

When V4 was not run (no resamples supplied), the consistency term is dropped
and its weight is excluded from the normalisation, so VCS stays in [0, 1]
rather than being penalised for a layer that didn't execute.

Answer VCS
----------
The mean of the per-claim scores. Decision:
    abstained by the model            -> ABSTAIN
    no verifiable claims              -> ABSTAIN
    VCS < threshold                   -> ABSTAIN
    otherwise                         -> ANSWER

Weights and threshold are provisional defaults; phase 6 calibrates the
threshold on held-out data (see docs/phases/phase-05-verification-proof.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.verification.types import Entailment

ANSWER = "ANSWER"
ABSTAIN = "ABSTAIN"


@dataclass
class VCSConfig:
    w_entail: float = 0.40
    w_fidelity: float = 0.35
    w_consistency: float = 0.25
    threshold: float = 0.60


@dataclass
class ClaimVCS:
    claim_text: str
    citation_ok: bool
    entailment: Entailment
    fidelity: float
    consistency: float | None
    vcs: float
    gate_failed: str | None = None

    def to_dict(self) -> dict:
        return {
            "claim_text": self.claim_text,
            "citation_ok": self.citation_ok,
            "entailment": self.entailment.value,
            "fidelity": self.fidelity,
            "consistency": self.consistency,
            "vcs": self.vcs,
            "gate_failed": self.gate_failed,
        }


@dataclass
class VCSResult:
    vcs: float | None
    decision: str
    threshold: float
    abstained: bool
    per_claim: list[ClaimVCS] = field(default_factory=list)
    weights: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "vcs": self.vcs,
            "decision": self.decision,
            "threshold": self.threshold,
            "abstained": self.abstained,
            "per_claim": [c.to_dict() for c in self.per_claim],
            "weights": dict(self.weights),
        }


def _claim_vcs(
    citation_ok: bool,
    entailment: Entailment,
    fidelity: float,
    consistency: float | None,
    config: VCSConfig,
) -> tuple[float, str | None]:
    if not citation_ok:
        return 0.0, "citation"
    if entailment == Entailment.CONTRADICTS:
        return 0.0, "contradiction"

    entail_component = 1.0 if entailment == Entailment.ENTAILS else 0.0
    components = [(entail_component, config.w_entail), (fidelity, config.w_fidelity)]
    if consistency is not None:
        components.append((consistency, config.w_consistency))

    total_weight = sum(w for _, w in components)
    if total_weight == 0:
        return 0.0, None
    score = sum(c * w for c, w in components) / total_weight
    return score, None


def aggregate_vcs(
    abstained: bool,
    citation_flags: list[bool],
    entailments: list[Entailment],
    fidelities: list[float],
    consistencies: list[float | None],
    config: VCSConfig | None = None,
) -> VCSResult:
    """Combine aligned per-claim V1-V4 signals into an answer-level VCSResult.

    All four signal lists must be the same length and ordered like the answer's
    claims. `consistencies` entries may be None (V4 not run).
    """
    config = config or VCSConfig()
    weights = {
        "w_entail": config.w_entail,
        "w_fidelity": config.w_fidelity,
        "w_consistency": config.w_consistency,
    }

    if abstained:
        return VCSResult(
            vcs=None, decision=ABSTAIN, threshold=config.threshold,
            abstained=True, per_claim=[], weights=weights,
        )

    per_claim: list[ClaimVCS] = []
    for text_idx, (cit, ent, fid, con) in enumerate(
        zip(citation_flags, entailments, fidelities, consistencies)
    ):
        score, gate = _claim_vcs(cit, ent, fid, con, config)
        per_claim.append(
            ClaimVCS(
                claim_text=f"claim_{text_idx}",
                citation_ok=cit,
                entailment=ent,
                fidelity=fid,
                consistency=con,
                vcs=score,
                gate_failed=gate,
            )
        )

    if not per_claim:
        return VCSResult(
            vcs=None, decision=ABSTAIN, threshold=config.threshold,
            abstained=False, per_claim=[], weights=weights,
        )

    vcs = sum(c.vcs for c in per_claim) / len(per_claim)
    decision = ANSWER if vcs >= config.threshold else ABSTAIN
    return VCSResult(
        vcs=vcs, decision=decision, threshold=config.threshold,
        abstained=False, per_claim=per_claim, weights=weights,
    )
