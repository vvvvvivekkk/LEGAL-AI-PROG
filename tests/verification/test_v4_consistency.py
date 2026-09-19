"""V4 tests: self-consistency across resampled answers."""

from src.generation.generator import Answer
from src.generation.parser import Claim
from src.verification.v4_consistency import self_consistency


def _answer(claim_texts):
    return Answer(
        query="q",
        raw_text="",
        claims=[Claim(t, ["c::s1"]) for t in claim_texts],
        context_chunk_ids=["c::s1"],
    )


def test_stable_claim_recurs_in_all_samples():
    primary = _answer(["The deposit is refunded within thirty days of vacating"])
    resamples = [
        _answer(["The deposit is refunded within thirty days of vacating"]),
        _answer(["A deposit is refunded within thirty days after the tenant vacating"]),
        _answer(["The deposit is refunded within thirty days of vacating the premises"]),
    ]
    results = self_consistency(primary, resamples)
    assert results[0].consistency == 1.0
    assert results[0].stable


def test_unstable_claim_flagged_when_absent_from_resamples():
    primary = _answer(["The landlord may seize the deposit permanently without cause"])
    resamples = [
        _answer(["The deposit is refunded within thirty days"]),
        _answer(["The deposit shall not exceed two months rent"]),
        _answer(["The tenant must receive ninety days eviction notice"]),
    ]
    results = self_consistency(primary, resamples)
    assert results[0].consistency == 0.0
    assert not results[0].stable


def test_partial_recurrence():
    primary = _answer(["The deposit is refunded within thirty days of vacating"])
    resamples = [
        _answer(["The deposit is refunded within thirty days of vacating"]),  # match
        _answer(["Something completely unrelated about waste disposal permits"]),  # no match
    ]
    results = self_consistency(primary, resamples)
    assert results[0].consistency == 0.5
    assert results[0].n_matches == 1
    assert results[0].n_samples == 2


def test_no_resamples_is_zero_consistency():
    primary = _answer(["A claim"])
    results = self_consistency(primary, [])
    assert results[0].consistency == 0.0
    assert not results[0].stable
