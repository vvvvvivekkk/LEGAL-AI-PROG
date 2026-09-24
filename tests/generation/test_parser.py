"""Parser tests: claim/citation extraction and malformed-line handling."""

import pytest

from src.generation.parser import (
    MalformedAnswerError,
    extract_citations,
    is_abstention,
    parse_claims,
    strip_citations,
)


def test_extract_single_citation():
    assert extract_citations("Rent is capped [urban_tenancy_act_2019::s4:a].") == [
        "urban_tenancy_act_2019::s4:a"
    ]


def test_extract_multi_bracket_citations():
    ids = extract_citations("Deposit rules apply [a::s1][b::s2:c].")
    assert ids == ["a::s1", "b::s2:c"]


def test_extract_comma_separated_citations():
    ids = extract_citations("Grounds for eviction [x::s5:a, x::s5:b, x::s5:c].")
    assert ids == ["x::s5:a", "x::s5:b", "x::s5:c"]


VIVINT = "VIVINT SOLAR, INC. - NON-COMPETITION AGREEMENT"


def test_extract_keeps_a_comma_inside_the_source_id():
    # Seen in the 2026-09-24 human e2e run: the source id comes from a file
    # name with a comma, and splitting on it broke every citation of that file.
    line = f"The amendment was entered into on August 16, 2017. [{VIVINT}::p1]"
    assert extract_citations(line) == [f"{VIVINT}::p1"]


def test_extract_comma_list_of_ids_that_contain_commas():
    ids = extract_citations(f"Both apply [{VIVINT}::p1, {VIVINT}::p3, other::s2].")
    assert ids == [f"{VIVINT}::p1", f"{VIVINT}::p3", "other::s2"]


def test_full_width_brackets_are_citations():
    # The exact answer Groq returned for S1 in the 2026-09-24 human e2e run:
    # every citation used 【】, so no claim was found and a correct answer abstained.
    raw = (
        "The agreement is valid for three years from the date it becomes effective"
        "【Confidentiality_Agreement_1::p18】.  \n"
        "It is tacitly extended by one year if it is not terminated three months before its"
        " expiration【Confidentiality_Agreement_1::p18】."
    )
    claims, malformed = parse_claims(raw)
    assert malformed == []
    assert [c.cited_chunk_ids for c in claims] == [["Confidentiality_Agreement_1::p18"]] * 2
    assert claims[0].text == "The agreement is valid for three years from the date it becomes effective."
    assert extract_citations("x ［a::s1］ [b::s2]") == ["a::s1", "b::s2"]


def test_extract_dedupes_repeated_ids():
    assert extract_citations("[a::s1][a::s1]") == ["a::s1"]


def test_empty_brackets_yield_no_ids():
    assert extract_citations("A claim with no real cite [].") == []


def test_strip_citations_leaves_clean_text():
    text = strip_citations("The deposit is refunded in thirty days [act::s4:b].")
    assert text == "The deposit is refunded in thirty days ."  # punctuation preserved


def test_parse_wellformed_multi_claim():
    raw = (
        "A landlord must refund the deposit within thirty days [urban::s4:b].\n"
        "The deposit may not exceed two months rent [urban::s4:a].\n"
    )
    claims, malformed = parse_claims(raw)
    assert malformed == []
    assert len(claims) == 2
    assert claims[0].cited_chunk_ids == ["urban::s4:b"]
    assert claims[1].cited_chunk_ids == ["urban::s4:a"]
    assert "thirty days" in claims[0].text


def test_parse_records_malformed_line_nonstrict():
    raw = (
        "A cited claim [act::s1].\n"
        "An uncited factual sentence with no bracket.\n"
    )
    claims, malformed = parse_claims(raw)
    assert len(claims) == 1
    assert malformed == ["An uncited factual sentence with no bracket."]


def test_parse_strict_raises_on_malformed():
    raw = "A sentence with no citation at all."
    with pytest.raises(MalformedAnswerError):
        parse_claims(raw, strict=True)


def test_abstention_detection():
    assert is_abstention("INSUFFICIENT_CONTEXT: the passages do not mention this.")
    assert not is_abstention("A normal answer [act::s1].")
