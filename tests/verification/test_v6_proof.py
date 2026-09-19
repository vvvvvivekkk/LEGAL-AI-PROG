"""V6 tests: Proof Object assembly and JSON serialization."""

import json

from src.verification.types import Entailment
from src.verification.v1_citation import ClaimCitationResult
from src.verification.v2_entailment import ClaimEntailmentResult
from src.verification.v3_atomic import AtomResult, ClaimFidelityResult
from src.verification.v4_consistency import ClaimConsistencyResult
from src.verification.v5_vcs import aggregate_vcs
from src.verification.v6_proof import build_proof


def _layers():
    v1 = [ClaimCitationResult(
        claim_text="Deposit refunded within thirty days.",
        cited_chunk_ids=["urban_tenancy_act_2019::s4:b"],
        existing_ids=["urban_tenancy_act_2019::s4:b"],
        missing_ids=[],
    )]
    v2 = [ClaimEntailmentResult(
        claim_text="Deposit refunded within thirty days.",
        verdict=Entailment.ENTAILS,
        best_chunk_id="urban_tenancy_act_2019::s4:b",
        score=0.96,
    )]
    v3 = [ClaimFidelityResult(
        claim_text="Deposit refunded within thirty days.",
        atoms=[AtomResult("Deposit refunded within thirty days", Entailment.ENTAILS, 0.96)],
    )]
    v4 = [ClaimConsistencyResult(
        claim_text="Deposit refunded within thirty days.",
        consistency=1.0, n_samples=3, n_matches=3, stable=True,
    )]
    return v1, v2, v3, v4


def test_build_proof_has_span_and_verdicts(context_chunks):
    v1, v2, v3, v4 = _layers()
    vcs_result = aggregate_vcs(
        abstained=False,
        citation_flags=[True],
        entailments=[Entailment.ENTAILS],
        fidelities=[1.0],
        consistencies=[1.0],
    )
    proof = build_proof(
        "How long to refund a deposit?", "raw answer text", context_chunks,
        v1, v2, v3, v4, vcs_result,
    )
    assert len(proof.claims) == 1
    claim = proof.claims[0]
    # verbatim span comes straight from the cited chunk text
    assert claim.quoted_span == context_chunks[0]["text"]
    assert claim.supporting_chunk_ids == ["urban_tenancy_act_2019::s4:b"]
    assert claim.verdicts["v1_citation"]["passed"]
    assert claim.verdicts["v2_entailment"]["verdict"] == "ENTAILS"
    assert claim.verdicts["v4_consistency"]["stable"]
    assert claim.vcs_contribution == 1.0


def test_proof_is_json_serializable(context_chunks):
    v1, v2, v3, v4 = _layers()
    vcs_result = aggregate_vcs(
        abstained=False,
        citation_flags=[True], entailments=[Entailment.ENTAILS],
        fidelities=[1.0], consistencies=[1.0],
    )
    proof = build_proof("q", "raw", context_chunks, v1, v2, v3, v4, vcs_result)
    dumped = json.loads(proof.to_json())
    assert dumped["decision"] in ("ANSWER", "ABSTAIN")
    assert dumped["claims"][0]["quoted_span"]


def test_proof_without_v4(context_chunks):
    v1, v2, v3, _ = _layers()
    vcs_result = aggregate_vcs(
        abstained=False,
        citation_flags=[True], entailments=[Entailment.ENTAILS],
        fidelities=[1.0], consistencies=[None],
    )
    proof = build_proof("q", "raw", context_chunks, v1, v2, v3, None, vcs_result)
    assert proof.claims[0].verdicts["v4_consistency"] is None
