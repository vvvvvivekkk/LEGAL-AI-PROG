"""Retrieval on LangChain retrievers: dense + BM25 -> RRF -> cross-encoder.

    ContextualCompressionRetriever(
        base_retriever  = EnsembleRetriever([dense (LanceDB), BM25], RRF) -> top n,
        base_compressor = CrossEncoderReranker(BAAI/bge-reranker-base)    -> top k)

Why not the LanceDB integration's own hybrid search: with lancedb 0.38 its
query_type="hybrid" raises TypeError (it passes a (vector, text) tuple that
lancedb's query-type inference rejects) and query_type="fts" fails to unpack
its own results. EnsembleRetriever over a dense retriever and BM25Retriever is
the LangChain-native equivalent.

Custom code on top of the stock classes, all for parity with src/ or to keep
scores visible:
  * none of VectorStoreRetriever, BM25Retriever or EnsembleRetriever return a
    score, so thin subclasses put it in metadata (_distance / _score /
    _relevance_score -- the column names src/ reports);
  * EnsembleRetriever returns every fused document; it is truncated to n, as
    LanceDB's hybrid limit(n) does, so the reranker sees the same pool size;
  * c=59: lancedb's RRF is 1/(rank0 + 60), EnsembleRetriever's 1/(rank1 + c);
  * BM25Retriever's default tokenizer is str.split (case- and punctuation-
    sensitive); it is given lancedb's simple tokenizer behaviour instead
    (lowercase, split on non-alphanumerics);
  * the stock CrossEncoderReranker scores page_content only and drops the
    score; src/ scores "summary + text", so a subclass does that and keeps it.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from functools import lru_cache

from langchain_classic.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.retrievers import BM25Retriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun, Callbacks
from langchain_core.documents import BaseDocumentCompressor, Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

from lc.embeddings import embedding_input
from lc.vectorstore import ChunkStore, stored_to_document

RERANKER_MODEL = "BAAI/bge-reranker-base"
_TOKEN = re.compile(r"\w+")


def _copy(doc: Document, **extra) -> Document:
    return Document(page_content=doc.page_content, metadata={**doc.metadata, **extra})


def lance_tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


# ---------------------------------------------------------------------------
# Base retrievers
# ---------------------------------------------------------------------------

class DenseRetriever(BaseRetriever):
    """VectorStoreRetriever equivalent that keeps the L2 distance."""

    store: ChunkStore
    k: int = 5
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> list[Document]:
        hits = self.store.lance.similarity_search_with_score(query, k=self.k)
        return [
            _copy(stored_to_document(d.page_content, d.metadata), _distance=float(s))
            for d, s in hits
        ]


class ScoredBM25Retriever(BM25Retriever):
    """BM25Retriever that reports its BM25 score and, like lancedb FTS, returns
    only documents sharing at least one query term (score > 0). The stock one
    pads the top k with zero-score documents, which would then collect
    arbitrary RRF credit in the fusion."""

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun | None = None
    ) -> list[Document]:
        scores = self.vectorizer.get_scores(self.preprocess_func(query))
        order = sorted(range(len(self.docs)), key=lambda i: scores[i], reverse=True)[: self.k]
        return [_copy(self.docs[i], _score=float(scores[i])) for i in order if scores[i] > 0]


class FusedRetriever(EnsembleRetriever):
    """EnsembleRetriever (weighted RRF) that keeps the fused score and truncates
    to `limit`, like LanceDB's hybrid query."""

    limit: int = 5

    def weighted_reciprocal_rank(self, doc_lists: list[list[Document]]) -> list[Document]:
        scores: dict[str, float] = {}
        first: dict[str, Document] = {}
        for doc_list, weight in zip(doc_lists, self.weights):
            for rank, doc in enumerate(doc_list, start=1):
                key = doc.metadata[self.id_key]
                scores[key] = scores.get(key, 0.0) + weight / (rank + self.c)
                first.setdefault(key, doc)
        ranked = sorted(scores, key=lambda key: scores[key], reverse=True)[: self.limit]
        return [_copy(first[key], _relevance_score=scores[key]) for key in ranked]


class _EmptyRetriever(BaseRetriever):
    def _get_relevant_documents(self, query: str, *, run_manager=None) -> list[Document]:
        return []


# BM25 is in-memory over every chunk; rebuilt only when the table version moves
# (an ingest or a delete), not per query.
_BM25_CACHE: dict[tuple[str, int], BaseRetriever] = {}


def bm25_retriever(store: ChunkStore, k: int) -> BaseRetriever:
    key = (store.db_path, store.version())
    if key not in _BM25_CACHE:
        docs = store.all_documents()
        _BM25_CACHE.clear()
        _BM25_CACHE[key] = (
            ScoredBM25Retriever.from_documents(docs, preprocess_func=lance_tokenize)
            if docs
            else _EmptyRetriever()
        )
    base = _BM25_CACHE[key]
    return base.model_copy(update={"k": k}) if isinstance(base, ScoredBM25Retriever) else base


def dense_retriever(store: ChunkStore, k: int) -> DenseRetriever:
    return DenseRetriever(store=store, k=k)


def hybrid_retriever(store: ChunkStore, k: int) -> FusedRetriever:
    """Dense + BM25, each fetching k, RRF-fused and truncated to k."""
    return FusedRetriever(
        retrievers=[dense_retriever(store, k), bm25_retriever(store, k)],
        weights=[0.5, 0.5],
        c=59,
        id_key="chunk_id",
        limit=k,
    )


# ---------------------------------------------------------------------------
# Reranking
# ---------------------------------------------------------------------------

class ScoredCrossEncoderReranker(CrossEncoderReranker):
    """Scores (query, summary + text) like src/, keeps the score as rerank_score."""

    def compress_documents(
        self, documents: Sequence[Document], query: str, callbacks: Callbacks | None = None
    ) -> Sequence[Document]:
        if not documents:
            return []
        pairs = [
            (query, embedding_input(d.metadata.get("contextual_summary", "") or "", d.page_content))
            for d in documents
        ]
        scores = [float(s) for s in self.model.score(pairs)]
        ranked = sorted(zip(documents, scores), key=lambda pair: pair[1], reverse=True)
        return [_copy(d, rerank_score=s) for d, s in ranked[: self.top_n]]


class RerankerAdapter(BaseDocumentCompressor):
    """Wraps an object with src/'s rerank(query, rows) interface (test fakes)."""

    reranker: object
    top_n: int = 5
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def compress_documents(
        self, documents: Sequence[Document], query: str, callbacks: Callbacks | None = None
    ) -> Sequence[Document]:
        from lc.verification import doc_to_row

        rows = [doc_to_row(d) | {"_doc": d} for d in documents]
        ranked = self.reranker.rerank(query, rows)
        return [
            _copy(r["_doc"], rerank_score=r.get("rerank_score")) for r in ranked[: self.top_n]
        ]


@lru_cache(maxsize=1)
def _cross_encoder():
    from langchain_community.cross_encoders import HuggingFaceCrossEncoder

    return HuggingFaceCrossEncoder(model_name=RERANKER_MODEL)


def default_cross_encoder_compressor() -> ScoredCrossEncoderReranker:
    return ScoredCrossEncoderReranker(model=_cross_encoder())


def as_compressor(reranker, top_n: int) -> BaseDocumentCompressor:
    if isinstance(reranker, CrossEncoderReranker):
        return reranker.model_copy(update={"top_n": top_n})
    if isinstance(reranker, BaseDocumentCompressor):
        return reranker
    return RerankerAdapter(reranker=reranker, top_n=top_n)


# ---------------------------------------------------------------------------
# The /query retriever
# ---------------------------------------------------------------------------

def query_retriever(store: ChunkStore, k: int, n: int, reranker=None) -> BaseRetriever:
    """With a reranker: pool of n fused candidates, cross-encoded down to k.
    Without: the fused top k directly (src/'s Retriever does the same)."""
    if reranker is None:
        return hybrid_retriever(store, k)
    return ContextualCompressionRetriever(
        base_compressor=as_compressor(reranker, top_n=k),
        base_retriever=hybrid_retriever(store, n),
    )
