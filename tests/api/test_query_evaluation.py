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


# Regression: Ask abstained on this question over an NDA corpus that contained
# the answer, because /query fetched only max(4*k, k) = 20 candidates and the
# answering clause was at fused rank 39. Guard the pool depth, which is the
# deterministic part of that failure.
NDA_DISCLOSURE_QUESTION = (
    "What happens if the receiving party discloses confidential information to a third party?"
)


def test_query_fetches_a_deep_candidate_pool(client):
    from src.api import deps
    from src.api.main import app
    from src.api.routes.query import QUERY_POOL_N
    from src.api.schemas import QueryRequest
    from tests.api.conftest import CitingStubAdapter, FakeNLI

    # A corpus larger than the pool floor, so the floor is what limits the
    # fetch rather than the number of rows that exist.
    paragraphs = [
        f"{i}. The Receiving Party shall treat batch {i} of the disclosed materials "
        "as confidential and shall not make it available to any third party."
        for i in range(150)
    ]
    body = "\n\n".join(paragraphs).encode("utf-8")
    assert client.post("/ingest", files={"file": ("nda.txt", body, "text/plain")}).status_code == 200
    total_chunks = client.get("/stats").json()["chunks"]
    assert total_chunks > QUERY_POOL_N

    seen: list[int] = []

    class PoolRecordingReranker:
        def rerank(self, query, candidates):
            seen.append(len(candidates))
            return list(candidates)

    app.dependency_overrides[deps.get_reranker_factory] = lambda: (lambda: PoolRecordingReranker())
    app.dependency_overrides[deps.get_adapter_factory] = lambda: (lambda: CitingStubAdapter())
    app.dependency_overrides[deps.get_nli_factory] = lambda: (lambda: FakeNLI())

    default_k = QueryRequest(query="x").k
    resp = client.post("/query", json={"query": NDA_DISCLOSURE_QUESTION})
    assert resp.status_code == 200, resp.text

    assert seen, "the reranker was never called — /query is not reranking by default"
    # Deep enough that the cross-encoder, not the fused ranking, picks the top-k.
    assert seen[0] >= QUERY_POOL_N
    assert seen[0] >= 8 * default_k
    assert seen[0] > 4 * 5  # the old formula at the old default k — a pool of 20


# ---------------------------------------------------------------------------
# General-knowledge fallback
# ---------------------------------------------------------------------------

class AbstainingAdapter:
    """LLM that always declines — the document-grounded path produces nothing."""

    def __init__(self):
        self.prompts = []

    def complete(self, system, user):
        self.prompts.append((system, user))
        if "own knowledge" in system:
            return "A non-disclosure agreement is a contract restricting disclosure of information."
        return "INSUFFICIENT_CONTEXT: the passages do not define this."


def _adapter_client(client, adapter):
    from src.api import deps
    from src.api.main import app
    from tests.api.conftest import FakeNLI

    app.dependency_overrides[deps.get_adapter_factory] = lambda: (lambda: adapter)
    app.dependency_overrides[deps.get_nli_factory] = lambda: (lambda: FakeNLI())
    return client


def test_general_question_falls_back_to_general_knowledge(client, sample_txt_bytes):
    name, data = sample_txt_bytes
    client.post("/ingest", files={"file": (name, data, "text/plain")})
    adapter = AbstainingAdapter()
    c = _adapter_client(client, adapter)

    body = c.post("/query", json={"query": "What is a non-disclosure agreement?"}).json()

    assert body["answer_mode"] == "general_knowledge"
    assert body["vcs"] is None, "a general-knowledge answer must not carry a verification score"
    assert body["abstained"] is False
    assert "contract restricting disclosure" in body["answer_text"]
    # The declined document-grounded attempt is preserved, not thrown away.
    assert body["grounded_answer_text"].startswith("INSUFFICIENT_CONTEXT")
    # Two calls: the grounded attempt, then the general-knowledge one.
    assert any("own knowledge" in sys_p for sys_p, _ in adapter.prompts)


def test_document_question_still_abstains(client, sample_txt_bytes):
    """The remedies-clause case: the corpus should answer it, so abstain."""
    name, data = sample_txt_bytes
    client.post("/ingest", files={"file": (name, data, "text/plain")})
    adapter = AbstainingAdapter()
    c = _adapter_client(client, adapter)

    q = "What happens if the receiving party discloses confidential information to a third party?"
    body = c.post("/query", json={"query": q}).json()

    assert body["answer_mode"] == "abstained"
    assert body["abstained"] is True
    assert body["grounded_answer_text"] is None
    assert all("own knowledge" not in sys_p for sys_p, _ in adapter.prompts)


def test_general_fallback_can_be_disabled(client, sample_txt_bytes):
    name, data = sample_txt_bytes
    client.post("/ingest", files={"file": (name, data, "text/plain")})
    c = _adapter_client(client, AbstainingAdapter())

    body = c.post(
        "/query",
        json={"query": "What is a non-disclosure agreement?", "allow_general_knowledge": False},
    ).json()

    assert body["answer_mode"] == "abstained"
    assert body["abstained"] is True


def test_verified_answer_is_labelled_verified(client, sample_txt_bytes):
    from tests.api.conftest import CitingStubAdapter

    name, data = sample_txt_bytes
    client.post("/ingest", files={"file": (name, data, "text/plain")})
    c = _adapter_client(client, CitingStubAdapter())

    body = c.post("/query", json={"query": "What is the deposit refund period?"}).json()
    assert body["answer_mode"] == "verified"
    assert body["decision"] == "ANSWER"
    assert body["vcs"] is not None


def test_llm_provider_failure_returns_503_not_500(client, sample_txt_bytes):
    """An upstream quota/outage is not an internal error — report it cleanly."""
    from tests.api.conftest import FakeNLI
    from src.api import deps
    from src.api.main import app

    name, data = sample_txt_bytes
    client.post("/ingest", files={"file": (name, data, "text/plain")})

    class ExhaustedAdapter:
        def complete(self, system, user):
            raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")

    app.dependency_overrides[deps.get_adapter_factory] = lambda: (lambda: ExhaustedAdapter())
    app.dependency_overrides[deps.get_nli_factory] = lambda: (lambda: FakeNLI())

    resp = client.post("/query", json={"query": "deposit rules"})
    assert resp.status_code == 503
    assert "quota exceeded" in resp.json()["detail"]
