"""Default embedding backend: a small local sentence-transformers model.

`all-MiniLM-L6-v2` is used because it's small (~80MB), fast to download and
run locally, and good enough to develop/test the pipeline against. It is
*not* the model real experiments should report numbers with -- BGE-M3 or
GTE-Large (see docs/architecture.md §5) are the intended production
choices. This module is the seam for that swap: add a new entry to
MODEL_REGISTRY (or a new backend module implementing the same `embed`
interface from src/embedding/base.py) and point config at it. Neither is
wired up yet -- out of scope for phase 2.
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Swappable model registry. Only the dev-speed default is implemented today;
# the other keys document where BGE-M3 / GTE-Large would plug in later.
MODEL_REGISTRY = {
    "minilm": DEFAULT_MODEL_NAME,
    # "bge-m3": "BAAI/bge-m3",        # not wired up yet (phase 2+ later work)
    # "gte-large": "thenlper/gte-large",  # not wired up yet (phase 2+ later work)
}

_model_cache: dict[str, SentenceTransformer] = {}


def _get_model(model_name: str) -> SentenceTransformer:
    if model_name not in _model_cache:
        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]


class SentenceTransformerEmbedder:
    """Embedding backend backed by a local sentence-transformers model."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        self.model_name = model_name

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        model = _get_model(self.model_name)
        embeddings = model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(embeddings, dtype=np.float32)

    @property
    def dimension(self) -> int:
        return _get_model(self.model_name).get_sentence_embedding_dimension()


def embed(texts: list[str], model_name: str = DEFAULT_MODEL_NAME) -> np.ndarray:
    """Functional interface: embed(texts) -> np.ndarray, using the default backend."""
    return SentenceTransformerEmbedder(model_name).embed(texts)
