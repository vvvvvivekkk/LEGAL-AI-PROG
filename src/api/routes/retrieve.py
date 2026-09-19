"""GET /retrieve — dense / FTS / hybrid (+ optional reranked) search, side by side.

Wraps the phase-2 query helpers and the phase-3 Retriever. Reranking is opt-in
via ?rerank=true because it loads the cross-encoder; the three base variants
always return.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_db_path, get_embedder, get_reranker_factory
from src.api.schemas import RetrieveResponse
from src.api.serialization import chunk_rows
from src.indexing.build import open_table, table_exists
from src.indexing.query import search_dense, search_fts, search_hybrid
from src.retrieval.config import RetrievalConfig
from src.retrieval.retriever import Retriever

router = APIRouter()


@router.get("/retrieve", response_model=RetrieveResponse)
def retrieve(
    q: str,
    k: int = 5,
    rerank: bool = False,
    db_path: str = Depends(get_db_path),
    embedder=Depends(get_embedder),
    reranker_factory=Depends(get_reranker_factory),
) -> RetrieveResponse:
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query 'q' must not be empty")
    if k < 1:
        raise HTTPException(status_code=400, detail="k must be >= 1")
    if not table_exists(db_path):
        raise HTTPException(status_code=409, detail="Index is empty — ingest a document first")

    table = open_table(db_path)
    variants = {
        "dense": chunk_rows(search_dense(table, q, k=k, embedder=embedder)),
        "fts": chunk_rows(search_fts(table, q, k=k)),
        "hybrid": chunk_rows(search_hybrid(table, q, k=k, embedder=embedder)),
    }

    if rerank:
        config = RetrievalConfig(mode="hybrid", use_reranker=True, k=k, n=max(4 * k, k))
        retriever = Retriever(table, config=config, embedder=embedder, reranker=reranker_factory())
        variants["hybrid_reranked"] = chunk_rows(retriever.retrieve(q))

    return RetrieveResponse(query=q, k=k, reranked=rerank, variants=variants)
