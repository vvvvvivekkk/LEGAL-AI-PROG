"""End-to-end chain tests: a phase-4 generated answer through V1-V6."""

import json

from src.generation.adapters.stub import StubAdapter
from src.generation.generator import generate
from src.verification.chain import verify_answer
from src.verification.types import Entailment
from src.verification.v5_vcs import ABSTAIN, ANSWER


def test_chain_produces_vcs_and_proof_for_supported_answer(context_chunks, make_nli):
    canned = (
        "The deposit must be refunded within thirty days [urban_tenancy_act_2019::s4:b].\n"
        "The deposit may not exceed two months rent [urban_tenancy_act_2019::s4:a].\n"
    )
    answer = generate("Deposit rules?", context_chunks, StubAdapter(response=canned))
    nli = make_nli(
        [
            ("thirty days", "thirty days", Entailment.ENTAILS, 0.96),
            ("two months", "two months", Entailment.ENTAILS, 0.94),
        ]
    )
    result = verify_answer(answer, context_chunks, nli)

    assert result.vcs_result.vcs is not None
    assert result.vcs_result.decision == ANSWER
    assert len(result.proof.claims) == 2
    # proof carries verbatim spans and real claim text
    assert result.proof.claims[0].quoted_span == context_chunks[0]["text"]
    assert "thirty days" in result.proof.claims[0].claim_text
    # whole result serializes to JSON for the UI
    json.dumps(result.to_dict())


def test_chain_abstains_on_fabricated_citation(context_chunks, make_nli):
    # Cites a chunk id that was never retrieved -> V1 gate -> VCS 0 -> ABSTAIN.
    canned = "The tenant may withhold rent forever [urban_tenancy_act_2019::s99:z]."
    answer = generate("q", context_chunks, StubAdapter(response=canned))
    nli = make_nli([])
    result = verify_answer(answer, context_chunks, nli)

    assert result.vcs_result.vcs == 0.0
    assert result.vcs_result.decision == ABSTAIN
    assert result.proof.claims[0].verdicts["v1_citation"]["missing_ids"] == [
        "urban_tenancy_act_2019::s99:z"
    ]


def test_chain_handles_model_abstention(context_chunks, make_nli):
    answer = generate(
        "What is the capital of France?",
        context_chunks,
        StubAdapter(response="INSUFFICIENT_CONTEXT: not covered by these passages."),
    )
    result = verify_answer(answer, context_chunks, make_nli([]))
    assert result.vcs_result.abstained
    assert result.vcs_result.decision == ABSTAIN
    assert result.proof.claims == []


def test_chain_with_resamples_runs_v4(context_chunks, make_nli):
    canned = "The deposit must be refunded within thirty days [urban_tenancy_act_2019::s4:b]."
    adapter = StubAdapter(response=canned)
    answer = generate("q", context_chunks, adapter)
    resamples = [generate("q", context_chunks, adapter) for _ in range(3)]

    nli = make_nli([("thirty days", "thirty days", Entailment.ENTAILS, 0.96)])
    result = verify_answer(answer, context_chunks, nli, resamples=resamples)

    # V4 ran -> consistency present in the proof
    v4 = result.proof.claims[0].verdicts["v4_consistency"]
    assert v4 is not None
    assert v4["consistency"] == 1.0
    assert result.vcs_result.decision == ANSWER
