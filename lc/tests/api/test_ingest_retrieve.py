"""Tests for POST /ingest and GET /retrieve (fake embedder, temp index)."""

from __future__ import annotations


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ingest_indexes_chunks_and_reports_totals(client, sample_txt_bytes):
    name, data = sample_txt_bytes
    resp = client.post("/ingest", files={"file": (name, data, "text/plain")})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["source_id"] == "urban_tenancy_act_2019"
    assert body["new_chunk_count"] > 0
    assert len(body["new_chunks"]) == body["new_chunk_count"]
    # new chunks carry text + metadata
    first = body["new_chunks"][0]
    assert first["chunk_id"].startswith("urban_tenancy_act_2019::")
    assert "section_ref" in first["metadata"]
    # totals reflect exactly this one document
    assert body["totals"]["chunks"] == body["new_chunk_count"]
    assert body["totals"]["documents"] == 1


def test_ingest_rejects_unsupported_extension(client):
    resp = client.post("/ingest", files={"file": ("notes.md", b"# hello", "text/markdown")})
    assert resp.status_code == 415


def test_ingest_unstructured_file_uses_fallback(client):
    body = b"Meeting notes.\n\nWe discussed the roadmap.\n\nAction items were assigned."
    resp = client.post("/ingest", files={"file": ("memo.txt", body, "text/plain")})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["used_fallback"] is True
    assert data["note"] and "fallback" in data["note"].lower()
    assert data["new_chunk_count"] == 3
    assert data["new_chunks"][0]["chunk_id"].startswith("memo::p")
    assert data["new_chunks"][0]["metadata"]["structure"] == "fallback"


def test_ingest_statute_does_not_use_fallback(client, sample_txt_bytes):
    name, data = sample_txt_bytes
    resp = client.post("/ingest", files={"file": (name, data, "text/plain")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["used_fallback"] is False
    assert body["note"] is None


def test_ingest_empty_file_returns_422(client):
    resp = client.post("/ingest", files={"file": ("empty.txt", b"   \n\n  ", "text/plain")})
    assert resp.status_code == 422


def test_retrieve_before_ingest_returns_409(client):
    resp = client.get("/retrieve", params={"q": "deposit refund"})
    assert resp.status_code == 409


def test_retrieve_returns_three_variants(client, sample_txt_bytes):
    name, data = sample_txt_bytes
    client.post("/ingest", files={"file": (name, data, "text/plain")})

    resp = client.get("/retrieve", params={"q": "security deposit refund", "k": 5})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reranked"] is False
    assert set(body["variants"].keys()) == {"dense", "fts", "hybrid"}
    for variant in body["variants"].values():
        assert isinstance(variant, list)
        assert len(variant) <= 5
    # rows are sanitized: no raw vector, metadata is an object
    for row in body["variants"]["dense"]:
        assert "vector" not in row
        assert isinstance(row["metadata"], dict)


def test_retrieve_with_rerank_adds_reranked_variant(client, sample_txt_bytes):
    name, data = sample_txt_bytes
    client.post("/ingest", files={"file": (name, data, "text/plain")})

    resp = client.get("/retrieve", params={"q": "security deposit", "k": 3, "rerank": "true"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reranked"] is True
    assert "hybrid_reranked" in body["variants"]
    reranked = body["variants"]["hybrid_reranked"]
    assert len(reranked) <= 3
    if reranked:
        assert reranked[0]["score_kind"] == "rerank_score"


def test_retrieve_empty_query_returns_400(client, sample_txt_bytes):
    name, data = sample_txt_bytes
    client.post("/ingest", files={"file": (name, data, "text/plain")})
    resp = client.get("/retrieve", params={"q": "   "})
    assert resp.status_code == 400


def test_ingest_embedding_failure_returns_503_with_reason(client_broken_embedder, sample_txt_bytes):
    name, data = sample_txt_bytes
    resp = client_broken_embedder.post("/ingest", files={"file": (name, data, "text/plain")})
    assert resp.status_code == 503
    detail = resp.json()["detail"]
    assert detail.startswith("embedding model unavailable:")
    assert "could not download" in detail
    # a failed ingest must not leave a half-written index behind
    assert client_broken_embedder.get("/retrieve", params={"q": "deposit"}).status_code == 409


def test_unhandled_route_error_is_json_with_cors_headers(client):
    """Any exception a route doesn't catch must still come back as JSON with
    CORS headers — otherwise the browser reports a bare "Failed to fetch"."""
    from lc.api import app as _app

    @_app.get("/_boom")
    def boom():
        raise RuntimeError("kaboom")

    try:
        resp = client.get("/_boom", headers={"Origin": "http://localhost:5173"})
    finally:
        _app.router.routes[:] = [r for r in _app.router.routes if getattr(r, "path", None) != "/_boom"]
    assert resp.status_code == 500
    assert resp.json()["detail"] == "internal error: RuntimeError: kaboom"
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_ingest_same_file_twice_is_rejected(client, sample_txt_bytes):
    name, data = sample_txt_bytes
    first = client.post("/ingest", files={"file": (name, data, "text/plain")})
    assert first.status_code == 200
    total = first.json()["totals"]["chunks"]

    second = client.post("/ingest", files={"file": (name, data, "text/plain")})
    assert second.status_code == 409
    assert "already indexed" in second.json()["detail"]["message"]
    assert client.get("/stats").json()["chunks"] == total


def test_ingest_same_content_under_new_name_is_rejected(client, sample_txt_bytes):
    name, data = sample_txt_bytes
    assert client.post("/ingest", files={"file": (name, data, "text/plain")}).status_code == 200
    resp = client.post("/ingest", files={"file": ("renamed_copy.txt", data, "text/plain")})
    assert resp.status_code == 409
    assert "identical content" in resp.json()["detail"]["message"]


def test_ingest_same_name_different_content_is_rejected(client, sample_txt_bytes):
    name, data = sample_txt_bytes
    assert client.post("/ingest", files={"file": (name, data, "text/plain")}).status_code == 200
    resp = client.post("/ingest", files={"file": (name, data + b"\n\nSection 99. Extra.", "text/plain")})
    assert resp.status_code == 409
    assert "same name" in resp.json()["detail"]["message"]


def test_delete_document_removes_chunks_and_allows_reingest(client, sample_txt_bytes):
    name, data = sample_txt_bytes
    first = client.post("/ingest", files={"file": (name, data, "text/plain")})
    assert first.status_code == 200
    source_id = first.json()["source_id"]
    chunk_count = first.json()["new_chunk_count"]

    # The document is searchable while it is indexed.
    before = client.get("/retrieve", params={"q": "security deposit refund", "k": 5})
    assert before.status_code == 200
    assert any(before.json()["variants"][v] for v in before.json()["variants"])

    deleted = client.delete(f"/documents/{source_id}")
    assert deleted.status_code == 200, deleted.text
    body = deleted.json()
    assert body["source_id"] == source_id
    assert body["deleted_chunk_count"] == chunk_count
    assert body["totals"]["chunks"] == 0
    assert body["totals"]["documents"] == 0

    # Its chunks are gone from the index and from search.
    assert client.get("/stats").json()["chunks"] == 0
    after = client.get("/retrieve", params={"q": "security deposit refund", "k": 5})
    assert after.status_code in (200, 409)
    if after.status_code == 200:
        for rows in after.json()["variants"].values():
            assert not [r for r in rows if r["chunk_id"].startswith(f"{source_id}::")]

    # And the same file can be ingested again without tripping the dedup check.
    again = client.post("/ingest", files={"file": (name, data, "text/plain")})
    assert again.status_code == 200, again.text
    assert again.json()["new_chunk_count"] == chunk_count


def test_delete_unknown_document_returns_404(client):
    assert client.delete("/documents/not_indexed").status_code == 404


def test_delete_only_removes_the_named_document(client, sample_txt_bytes):
    name, data = sample_txt_bytes
    client.post("/ingest", files={"file": (name, data, "text/plain")})
    memo = b"Meeting notes.\n\nWe discussed the roadmap.\n\nAction items were assigned."
    client.post("/ingest", files={"file": ("memo.txt", memo, "text/plain")})

    resp = client.delete("/documents/memo")
    assert resp.status_code == 200
    assert resp.json()["totals"]["documents"] == 1
    assert client.get("/stats").json()["sources"][0]["source_id"] == "urban_tenancy_act_2019"
