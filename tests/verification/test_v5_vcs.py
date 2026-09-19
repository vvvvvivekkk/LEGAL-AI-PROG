"""V5 tests: VCS aggregation formula and abstention decision."""

from src.verification.types import Entailment
from src.verification.v5_vcs import ABSTAIN, ANSWER, VCSConfig, aggregate_vcs


def test_fully_supported_claim_scores_high_and_answers():
    result = aggregate_vcs(
        abstained=False,
        citation_flags=[True],
        entailments=[Entailment.ENTAILS],
        fidelities=[1.0],
        consistencies=[1.0],
    )
    assert result.vcs == 1.0
    assert result.decision == ANSWER


def test_fabricated_citation_gate_zeroes_claim():
    result = aggregate_vcs(
        abstained=False,
        citation_flags=[False],           # V1 gate fails
        entailments=[Entailment.ENTAILS],
        fidelities=[1.0],
        consistencies=[1.0],
    )
    assert result.vcs == 0.0
    assert result.per_claim[0].gate_failed == "citation"
    assert result.decision == ABSTAIN


def test_contradiction_gate_zeroes_claim():
    result = aggregate_vcs(
        abstained=False,
        citation_flags=[True],
        entailments=[Entailment.CONTRADICTS],
        fidelities=[1.0],
        consistencies=[1.0],
    )
    assert result.vcs == 0.0
    assert result.per_claim[0].gate_failed == "contradiction"


def test_consistency_omitted_renormalizes_weights():
    # No V4: entail(1.0)*0.40 + fidelity(1.0)*0.35 over weight 0.75 -> 1.0
    result = aggregate_vcs(
        abstained=False,
        citation_flags=[True],
        entailments=[Entailment.ENTAILS],
        fidelities=[1.0],
        consistencies=[None],
    )
    assert abs(result.vcs - 1.0) < 1e-9


def test_neutral_entailment_lowers_score_below_threshold():
    # entail component 0, fidelity 0.5, no consistency:
    # (0*0.40 + 0.5*0.35) / 0.75 = 0.233 -> below default 0.60 -> ABSTAIN
    result = aggregate_vcs(
        abstained=False,
        citation_flags=[True],
        entailments=[Entailment.NEUTRAL],
        fidelities=[0.5],
        consistencies=[None],
    )
    assert result.vcs < 0.6
    assert result.decision == ABSTAIN


def test_mean_across_claims():
    result = aggregate_vcs(
        abstained=False,
        citation_flags=[True, False],
        entailments=[Entailment.ENTAILS, Entailment.ENTAILS],
        fidelities=[1.0, 1.0],
        consistencies=[1.0, 1.0],
    )
    # claim0 = 1.0, claim1 gated to 0.0 -> mean 0.5
    assert result.vcs == 0.5


def test_abstained_answer_decision():
    result = aggregate_vcs(
        abstained=True,
        citation_flags=[], entailments=[], fidelities=[], consistencies=[],
    )
    assert result.decision == ABSTAIN
    assert result.vcs is None
    assert result.abstained


def test_no_claims_abstains():
    result = aggregate_vcs(
        abstained=False,
        citation_flags=[], entailments=[], fidelities=[], consistencies=[],
    )
    assert result.decision == ABSTAIN
    assert result.vcs is None


def test_custom_threshold_flips_decision():
    signals = dict(
        abstained=False,
        citation_flags=[True],
        entailments=[Entailment.ENTAILS],
        fidelities=[0.0],
        consistencies=[0.0],
    )
    # vcs = 1.0*0.40 = 0.40 over full weight 1.0 -> 0.40
    high = aggregate_vcs(**signals, config=VCSConfig(threshold=0.6))
    low = aggregate_vcs(**signals, config=VCSConfig(threshold=0.3))
    assert high.decision == ABSTAIN
    assert low.decision == ANSWER
