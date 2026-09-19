"""V2 tests: entailment/support with a controllable fake NLI."""

from src.generation.parser import Claim
from src.verification.types import Entailment
from src.verification.v2_entailment import check_entailment


def test_supporting_passage_entails(context_chunks, make_nli):
    nli = make_nli([("refund the security deposit within thirty days", "thirty days", Entailment.ENTAILS, 0.97)])
    claim = Claim("The deposit must be refunded within thirty days.", ["urban_tenancy_act_2019::s4:b"])
    result = check_entailment(claim, context_chunks, nli)
    assert result.verdict == Entailment.ENTAILS
    assert result.supported
    assert result.best_chunk_id == "urban_tenancy_act_2019::s4:b"
    assert result.score == 0.97


def test_contradicting_passage_flagged(context_chunks, make_nli):
    # Hand-crafted contradiction: the claim says ninety days, the source says thirty.
    nli = make_nli([("thirty days", "ninety days", Entailment.CONTRADICTS, 0.91)])
    claim = Claim("The deposit must be refunded within ninety days.", ["urban_tenancy_act_2019::s4:b"])
    result = check_entailment(claim, context_chunks, nli)
    assert result.verdict == Entailment.CONTRADICTS
    assert not result.supported


def test_neutral_when_no_rule_matches(context_chunks, make_nli):
    nli = make_nli([])  # everything falls back to NEUTRAL
    claim = Claim("Something unrelated.", ["urban_tenancy_act_2019::s4:a"])
    result = check_entailment(claim, context_chunks, nli)
    assert result.verdict == Entailment.NEUTRAL
    assert not result.supported


def test_entails_wins_over_contradicts_across_multiple_chunks(context_chunks, make_nli):
    # One cited chunk contradicts, another entails -> ENTAILS wins.
    nli = make_nli(
        [
            ("two months", "two months", Entailment.CONTRADICTS, 0.6),
            ("thirty days", "thirty days", Entailment.ENTAILS, 0.95),
        ]
    )
    claim = Claim(
        "Deposit is two months and refunded in thirty days.",
        ["urban_tenancy_act_2019::s4:a", "urban_tenancy_act_2019::s4:b"],
    )
    result = check_entailment(claim, context_chunks, nli)
    assert result.verdict == Entailment.ENTAILS
    assert result.best_chunk_id == "urban_tenancy_act_2019::s4:b"


def test_missing_citation_text_skipped(context_chunks, make_nli):
    # A cited id not in context contributes nothing here (that's V1's job).
    nli = make_nli([("thirty days", "thirty days", Entailment.ENTAILS, 0.9)])
    claim = Claim(
        "Refunded in thirty days.",
        ["urban_tenancy_act_2019::s4:b", "not::in:context"],
    )
    result = check_entailment(claim, context_chunks, nli)
    assert result.verdict == Entailment.ENTAILS
    assert len(result.per_chunk) == 1  # only the resolvable cited chunk was scored
