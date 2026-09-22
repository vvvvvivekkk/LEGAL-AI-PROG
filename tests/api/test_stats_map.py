"""Tests for GET /stats and GET /embedding-map, plus the PCA helper."""

from __future__ import annotations

import numpy as np

from src.api.projection import pca_2d


def test_pca_2d_shape_and_centering():
    rng = np.arange(30, dtype=float).reshape(10, 3)
    coords = pca_2d(rng)
    assert coords.shape == (10, 2)
    # projected coordinates are mean-centered
    assert np.allclose(coords.mean(axis=0), 0, atol=1e-8)


def test_pca_2d_empty():
    assert pca_2d(np.empty((0, 5))).shape == (0, 2)


def test_pca_2d_single_row_pads_to_two_cols():
    coords = pca_2d([[1.0, 2.0, 3.0]])
    assert coords.shape == (1, 2)


def test_stats_empty_index(client):
    resp = client.get("/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"chunks": 0, "documents": 0, "sources": []}


def test_stats_after_ingest(client, sample_txt_bytes):
    name, data = sample_txt_bytes
    client.post("/ingest", files={"file": (name, data, "text/plain")})
    body = client.get("/stats").json()
    assert body["documents"] == 1
    assert body["chunks"] > 0
    assert len(body["sources"]) == 1
    assert body["sources"][0]["source_id"] == "urban_tenancy_act_2019"
    assert body["sources"][0]["chunks"] == body["chunks"]


def test_embedding_map_empty_index(client):
    body = client.get("/embedding-map").json()
    assert body["method"] == "pca"
    assert body["points"] == []
    assert body["sources"] == []


def test_embedding_map_after_ingest(client, sample_txt_bytes):
    name, data = sample_txt_bytes
    ingest_body = client.post("/ingest", files={"file": (name, data, "text/plain")}).json()
    body = client.get("/embedding-map").json()

    assert body["method"] == "pca"
    assert len(body["points"]) == ingest_body["new_chunk_count"]
    assert body["sources"] == ["urban_tenancy_act_2019"]
    p = body["points"][0]
    assert isinstance(p["x"], float) and isinstance(p["y"], float)
    assert p["source_id"] == "urban_tenancy_act_2019"
    assert p["chunk_id"].startswith("urban_tenancy_act_2019::")


def test_db_path_can_be_overridden_by_env(monkeypatch):
    """scripts/batch_ask_check.py relies on this to use an isolated index."""
    import importlib

    from src.indexing.build import DEFAULT_DB_PATH

    monkeypatch.setenv("LEGAL_AI_DB_PATH", "data/lancedb_somewhere_else")
    deps = importlib.reload(importlib.import_module("src.api.deps"))
    try:
        assert deps.ApiState.db_path == "data/lancedb_somewhere_else"
    finally:
        monkeypatch.delenv("LEGAL_AI_DB_PATH", raising=False)
        deps = importlib.reload(importlib.import_module("src.api.deps"))
    assert deps.ApiState.db_path == DEFAULT_DB_PATH
