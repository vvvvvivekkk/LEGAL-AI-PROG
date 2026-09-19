"""V1 tests: citation existence, including a fabricated citation."""

from src.generation.generator import Answer
from src.generation.parser import Claim
from src.verification.v1_citation import check_citation_existence


def _answer(claims, context_ids):
    return Answer(
        query="q",
        raw_text="",
        claims=claims,
        context_chunk_ids=context_ids,
    )


def test_existing_citation_passes():
    answer = _answer(
        [Claim("A refund is due in thirty days.", ["urban::s4:b"])],
        ["urban::s4:b", "urban::s4:a"],
    )
    results = check_citation_existence(answer)
    assert results[0].passed
    assert results[0].missing_ids == []


def test_fabricated_citation_fails():
    # Cites a chunk id that was never retrieved -> fabricated citation.
    answer = _answer(
        [Claim("The tenant may withhold rent indefinitely.", ["urban::s99:z"])],
        ["urban::s4:b", "urban::s4:a"],
    )
    results = check_citation_existence(answer)
    assert not results[0].passed
    assert results[0].missing_ids == ["urban::s99:z"]
    assert results[0].existing_ids == []


def test_partial_citation_fails_if_any_missing():
    answer = _answer(
        [Claim("Mixed claim.", ["urban::s4:a", "urban::s404:x"])],
        ["urban::s4:a"],
    )
    results = check_citation_existence(answer)
    assert not results[0].passed
    assert results[0].existing_ids == ["urban::s4:a"]
    assert results[0].missing_ids == ["urban::s404:x"]


def test_uncited_claim_does_not_pass():
    answer = _answer([Claim("No citation here.", [])], ["urban::s4:a"])
    results = check_citation_existence(answer)
    assert not results[0].passed
    assert not results[0].has_citation
