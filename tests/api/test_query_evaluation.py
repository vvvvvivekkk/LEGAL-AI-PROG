"""Tests for POST /query and GET /evaluation with stubbed LLM + NLI.

The query_client / client_no_llm fixtures (in conftest) wire the stubbed
generation and verification backends.
"""

from __future__ import annotations


def _ingest(client, sample):
    name, data = sample
    resp = client.post("/ingest", files={"file": (name, data, "text/plain")})
    assert resp.status_code == 200, resp.text


def test_query_returns_answer_and_proof(query_client, sample_txt_bytes):
    _ingest(query_client, sample_txt_bytes)
    resp = query_client.post("/query", json={"query": "How is a security deposit handled?", "k": 5})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["answer_text"]
    assert body["abstained"] is False
    assert body["decision"] in ("ANSWER", "ABSTAIN")
    # proof carries claims, each with a supporting chunk + verbatim span
    assert body["proof"]["claims"]
    claim = body["proof"]["claims"][0]
    assert claim["supporting_chunk_ids"]
    assert claim["quoted_span"]
    assert claim["verdicts"]["v1_citation"]["passed"] is True


def test_query_with_stub_reaches_answer_decision(query_client, sample_txt_bytes):
    _ingest(query_client, sample_txt_bytes)
    resp = query_client.post("/query", json={"query": "deposit refund period", "k": 5})
    body = resp.json()
    # citing stub + always-entails NLI + existing citation => confident answer
    assert body["decision"] == "ANSWER"
    assert body["vcs"] is not None and body["vcs"] > 0.6


def test_query_self_consistency_runs_v4(query_client, sample_txt_bytes):
    _ingest(query_client, sample_txt_bytes)
    resp = query_client.post(
        "/query", json={"query": "deposit rules", "k": 3, "self_consistency": 2}
    )
    body = resp.json()
    v4 = body["proof"]["claims"][0]["verdicts"]["v4_consistency"]
    assert v4 is not None
    assert v4["consistency"] == 1.0  # deterministic stub -> identical resamples


def test_query_before_ingest_returns_409(query_client):
    resp = query_client.post("/query", json={"query": "anything"})
    assert resp.status_code == 409


def test_query_llm_unavailable_returns_503(client_no_llm, sample_txt_bytes):
    _ingest(client_no_llm, sample_txt_bytes)
    resp = client_no_llm.post("/query", json={"query": "deposit"})
    assert resp.status_code == 503


def test_evaluation_no_runs_message(client):
    resp = client.get("/evaluation")
    assert resp.status_code == 200
    body = resp.json()
    # experiments/ has no committed runs in the test environment
    assert isinstance(body["runs"], list)
    if not body["runs"]:
        assert body["message"]
