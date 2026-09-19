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
