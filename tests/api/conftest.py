"""API test fixtures: a fast fake embedder, fake reranker, and a TestClient
with pipeline dependencies overridden so tests run offline and quickly.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.api import deps
from src.api.main import app

_REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = _REPO_ROOT / "data" / "sample"


class FakeEmbedder:
    """Deterministic hashing embedder — same text always maps to the same
    32-d unit vector. No model download; fine for wiring/shape tests.
    """

    dim = 32

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)
        vecs = []
        for t in texts:
            digest = hashlib.sha256(t.encode("utf-8")).digest()  # 32 bytes
            arr = np.frombuffer(digest, dtype=np.uint8).astype(np.float32)
            norm = np.linalg.norm(arr) or 1.0
            vecs.append(arr / norm)
        return np.asarray(vecs, dtype=np.float32)

    @property
    def dimension(self) -> int:
        return self.dim


class FakeReranker:
    """Reverses candidate order and tags a rerank_score, deterministically."""

    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        out = []
        for i, row in enumerate(reversed(candidates)):
            row = dict(row)
            row["rerank_score"] = float(len(candidates) - i)
            out.append(row)
        return out


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "lancedb")
    app.dependency_overrides[deps.get_db_path] = lambda: db_path
    app.dependency_overrides[deps.get_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[deps.get_reranker_factory] = lambda: (lambda: FakeReranker())
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_txt_bytes() -> tuple[str, bytes]:
    path = SAMPLE_DIR / "urban_tenancy_act_2019.txt"
    return path.name, path.read_bytes()
