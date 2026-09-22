"""Per-layer on/off switches used by the phase-6 verification ablation sweep.

Defaults are unchanged (every layer on) — these only exercise the disabled
paths, and assert each one has the effect the sweep claims it does.
"""

from src.generation.adapters.stub import StubAdapter
from src.generation.generator import generate
from src.verification.chain import verify_answer
from src.verification.types import Entailment
from src.verification.v5_vcs import ABSTAIN, ANSWER, VCSConfig


def _fabricated_citation_answer(context_chunks):
    canned = "The tenant may withhold rent forever [urban_tenancy_act_2019::s99:z]."
    return generate("q", context_chunks, StubAdapter(response=canned))


def test_v1_off_lifts_the_fabricated_citation_gate(context_chunks, make_nli):
    answer = _fabricated_citation_answer(context_chunks)
    gated = verify_answer(answer, context_chunks, make_nli([]))
    assert gated.vcs_result.per_claim[0].gate_failed == "citation"

    ungated = verify_answer(
        answer, context_chunks, make_nli([]), config=VCSConfig(enable_v1=False)
    )
    assert ungated.vcs_result.per_claim[0].gate_failed is None


def test_v2_off_drops_the_contradiction_gate_and_the_entailment_term(
    context_chunks, make_nli
):
    canned = "The deposit must be refunded within ninety days [urban_tenancy_act_2019::s4:b]."
    answer = generate("q", context_chunks, StubAdapter(response=canned))
    nli = make_nli([("thirty days", "ninety days", Entailment.CONTRADICTS, 0.9)])

    gated = verify_answer(answer, context_chunks, nli)
    assert gated.vcs_result.per_claim[0].gate_failed == "contradiction"

    ungated = verify_answer(
        answer, context_chunks, nli, config=VCSConfig(enable_v2=False)
    )
    assert ungated.vcs_result.per_claim[0].gate_failed is None
    # Only the fidelity term remains, so the claim score is the fidelity itself.
    claim = ungated.vcs_result.per_claim[0]
    assert claim.vcs == claim.fidelity


def test_v3_off_removes_fidelity_from_the_score(context_chunks, make_nli):
    canned = "The deposit must be refunded within thirty days [urban_tenancy_act_2019::s4:b]."
    answer = generate("q", context_chunks, StubAdapter(response=canned))
    nli = make_nli([("thirty days", "thirty days", Entailment.ENTAILS, 0.96)])

    result = verify_answer(answer, context_chunks, nli, config=VCSConfig(enable_v3=False))
    claim = result.vcs_result.per_claim[0]
    assert claim.fidelity == 0.0  # V3 not run
    assert claim.vcs == 1.0  # ...and not penalised for it


def test_v4_off_ignores_supplied_resamples(context_chunks, make_nli):
    canned = "The deposit must be refunded within thirty days [urban_tenancy_act_2019::s4:b]."
    answer = generate("q", context_chunks, StubAdapter(response=canned))
    other = generate("q", context_chunks, StubAdapter(response="Something else [urban_tenancy_act_2019::s4:a]."))
    nli = make_nli([("thirty days", "thirty days", Entailment.ENTAILS, 0.96)])

    with_v4 = verify_answer(answer, context_chunks, nli, resamples=[other])
    assert with_v4.vcs_result.per_claim[0].consistency == 0.0

    without_v4 = verify_answer(
        answer, context_chunks, nli, resamples=[other], config=VCSConfig(enable_v4=False)
    )
    assert without_v4.vcs_result.per_claim[0].consistency is None


def test_v5_off_always_answers_a_scored_response(context_chunks, make_nli):
    canned = "The deposit must be refunded within ninety days [urban_tenancy_act_2019::s4:b]."
    answer = generate("q", context_chunks, StubAdapter(response=canned))
    nli = make_nli([("thirty days", "ninety days", Entailment.CONTRADICTS, 0.9)])

    assert verify_answer(answer, context_chunks, nli).vcs_result.decision == ABSTAIN
    ungated = verify_answer(answer, context_chunks, nli, config=VCSConfig(enable_v5=False))
    assert ungated.vcs_result.decision == ANSWER
    assert ungated.vcs_result.vcs == 0.0  # the score is still reported


def test_v6_off_emits_no_proof_object(context_chunks, make_nli):
    canned = "The deposit must be refunded within thirty days [urban_tenancy_act_2019::s4:b]."
    answer = generate("q", context_chunks, StubAdapter(response=canned))
    nli = make_nli([("thirty days", "thirty days", Entailment.ENTAILS, 0.96)])

    result = verify_answer(answer, context_chunks, nli, config=VCSConfig(enable_v6=False))
    assert result.proof is None
    assert result.to_dict()["proof"] is None
