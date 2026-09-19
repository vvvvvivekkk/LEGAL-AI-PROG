"""Generator + adapter tests against the stub adapter (no API key needed)."""

import pytest

from src.generation.adapters.stub import StubAdapter
from src.generation.factory import get_adapter
from src.generation.generator import generate, parse_answer
from src.generation.prompt import ABSTENTION_MARKER, build_prompt

CONTEXT = [
    {
        "chunk_id": "urban_tenancy_act_2019::s4:b",
        "text": "The landlord must refund the security deposit within thirty days of the tenant vacating.",
        "contextual_summary": "Section 4. Security deposit limits.",
        "metadata": {"section_ref": "Section 4(b)", "act": "THE URBAN TENANCY ACT, 2019"},
    },
    {
        "chunk_id": "urban_tenancy_act_2019::s4:a",
        "text": "The security deposit shall not exceed two months' rent for residential premises.",
        "contextual_summary": "Section 4. Security deposit limits.",
        "metadata": {"section_ref": "Section 4(a)", "act": "THE URBAN TENANCY ACT, 2019"},
    },
]


def test_prompt_includes_context_ids_and_rules():
    system, user = build_prompt("How long to refund a deposit?", CONTEXT)
    assert "only" in system.lower()
    assert "urban_tenancy_act_2019::s4:b" in user
    assert "CONTEXT:" in user and "QUESTION:" in user


def test_generate_parses_stub_response_into_claims():
    canned = (
        "A landlord must refund the deposit within thirty days [urban_tenancy_act_2019::s4:b].\n"
        "The deposit may not exceed two months rent [urban_tenancy_act_2019::s4:a].\n"
    )
    adapter = StubAdapter(response=canned)
    answer = generate("How long to refund a deposit?", CONTEXT, adapter)

    assert not answer.abstained
    assert len(answer.claims) == 2
    assert answer.claims[0].cited_chunk_ids == ["urban_tenancy_act_2019::s4:b"]
    assert answer.context_chunk_ids == [
        "urban_tenancy_act_2019::s4:b",
        "urban_tenancy_act_2019::s4:a",
    ]


def test_generate_receives_built_prompt():
    """The adapter must be called with the citation-forced system prompt."""
    adapter = StubAdapter(response="A claim [urban_tenancy_act_2019::s4:a].")
    generate("q", CONTEXT, adapter)
    system, user = adapter.calls[0]
    assert "citation" in system.lower()
    assert "urban_tenancy_act_2019::s4:a" in user


def test_generate_handles_abstention():
    adapter = StubAdapter(response=f"{ABSTENTION_MARKER}: the context does not cover this.")
    answer = generate("What is the capital of France?", CONTEXT, adapter)
    assert answer.abstained
    assert answer.claims == []


def test_answer_is_json_serializable():
    import json

    adapter = StubAdapter(response="A claim [urban_tenancy_act_2019::s4:a].")
    answer = generate("q", CONTEXT, adapter)
    dumped = json.dumps(answer.to_dict())
    assert "urban_tenancy_act_2019::s4:a" in dumped


def test_parse_answer_directly():
    raw = "A landlord refunds within thirty days [urban_tenancy_act_2019::s4:b]."
    answer = parse_answer("q", raw, CONTEXT)
    assert len(answer.claims) == 1
    assert answer.claims[0].cited_chunk_ids == ["urban_tenancy_act_2019::s4:b"]


def test_factory_rejects_unknown_provider():
    with pytest.raises(ValueError):
        get_adapter(provider="not-a-provider", api_key="x")


def test_factory_claude_requires_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(ValueError):
        get_adapter(provider="claude")
