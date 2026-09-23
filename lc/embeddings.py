"""Embeddings: HuggingFaceEmbeddings over the same MiniLM model as src/.

What gets embedded is "contextual summary + chunk text" (the SAC point), as in
src/indexing/build.py. HuggingFaceEmbeddings swaps newlines for spaces before
encoding; MiniLM's tokenizer treats both as whitespace, so the vectors match.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from langchain_core.embeddings import Embeddings

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def default_embeddings() -> Embeddings:
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        encode_kwargs={"normalize_embeddings": True},
    )


class EmbedderAdapter(Embeddings):
    """Wraps any object with embed(texts) -> ndarray (src/'s interface, and the
    test fakes) as a LangChain Embeddings."""

    def __init__(self, embedder):
        self.embedder = embedder

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return np.asarray(self.embedder.embed(list(texts)), dtype=np.float32).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def as_embeddings(obj) -> Embeddings:
    return obj if isinstance(obj, Embeddings) else EmbedderAdapter(obj)


def embedding_input(summary: str, text: str) -> str:
    return f"{summary}\n{text}".strip()
