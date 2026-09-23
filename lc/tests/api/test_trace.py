"""LangChain-only: the opt-in /query trace exposes every intermediate step.

Not a ported test -- src/'s /query has no trace. Without "trace" the response
must keep src/'s exact shape.
"""

from __future__ import annotations

from src.api.schemas import QueryResponse


def _ingest(client, sample):
    name, data = sample
    assert client.post("/ingest", files={"file": (name, data, "text/plain")}).status_code == 200


def test_default_response_has_src_shape(query_client, sample_txt_bytes):
    _ingest(query_client, sample_txt_bytes)
    body = query_client.post("/query", json={"query": "deposit refund", "k": 5}).json()
    assert set(body) == set(QueryResponse.model_fields)


def test_trace_carries_candidates_prompt_raw_output_and_verdicts(query_client, sample_txt_bytes):
    _ingest(query_client, sample_txt_bytes)
    body = query_client.post("/query", json={"query": "deposit refund", "k": 5, "trace": True}).json()
    trace = body["trace"]

    # retrieved candidates, each with its score and what kind of score it is
    assert len(trace["candidates"]) == len(body["context_chunk_ids"])
    assert [c["chunk_id"] for c in trace["candidates"]] == body["context_chunk_ids"]
    assert all(c["score"] is not None and c["score_kind"] for c in trace["candidates"])

    # the exact prompt: system + user, and the user turn carries the context ids
    roles = [m["role"] for m in trace["prompt"]]
    assert roles == ["system", "human"]
    assert trace["prompt"][0]["content"].startswith("You are a legal question-answering assistant.")
    assert all(f"[{cid}]" in trace["prompt"][1]["content"] for cid in body["context_chunk_ids"])

    # raw model output, and the per-claim verdicts in the proof
    assert trace["raw_output"] == body["answer_text"]
    assert trace["parsed_claims"]
    assert body["proof"]["claims"][0]["verdicts"]["v1_citation"]["passed"] is True
