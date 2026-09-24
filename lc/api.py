"""FastAPI app for the LangChain port -- same endpoints and JSON shapes as src/api.

    uvicorn lc.api:app            (port 8000, the UI's default)

The React UI works against it unchanged (web/.env: VITE_API_BASE=http://localhost:8000).
Response models, JSON serialisation helpers, the chat store, PCA projection and
the /experiments reader are src/'s own: they are API plumbing, not pipeline,
and sharing them is what guarantees identical response shapes.

One addition, off by default: POST /query with "trace": true also returns a
"trace" object -- scored candidates, the exact prompt messages, the raw model
output and parsed claims. Without it the response is byte-for-byte src/'s shape.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

import numpy as np
from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from lc import deps
from lc.loaders import SUPPORTED_SUFFIXES, load_document, source_id_for
from lc.pipeline import GenerationError, build_query_chain
from lc.retrieval import (
    bm25_retriever,
    dense_retriever,
    hybrid_retriever,
    query_retriever,
)
from lc.splitters import split_with_fallback, to_chunk_dict
from lc.vectorstore import ChunkStore
from lc.verification import doc_to_row
from src.api.projection import pca_2d
from src.api.schemas import (
    ChatMessage,
    Conversation,
    ConversationList,
    CreateConversationRequest,
    DeleteDocumentResponse,
    EmbeddingMapResponse,
    EmbeddingPoint,
    EvaluationResponse,
    EvaluationRun,
    IndexTotals,
    IngestResponse,
    ProofModel,
    QueryRequest,
    QueryResponse,
    RetrieveResponse,
    SourceStat,
    StatsResponse,
)
from src.api.serialization import chunk_rows, new_chunk
from src.chat.store import ChatStore, is_valid_id
from src.config import load_env
from src.evaluation.results_store import load_runs
from src.generation.factory import missing_key_message, selected_provider
from src.indexing.dedup import content_hash

load_env()
log = logging.getLogger("legal_ai.lc_api")

# Floor on the /query candidate pool, as src/api/routes/query.py.
QUERY_POOL_N = 100

router = APIRouter()


class LCQueryRequest(QueryRequest):
    trace: bool = False


def _store(db_path: str = Depends(deps.get_db_path), embedder=Depends(deps.get_embedder)):
    return ChunkStore(db_path, embedder)


def _totals(store: ChunkStore) -> IndexTotals:
    chunks, documents = store.totals()
    return IndexTotals(chunks=chunks, documents=documents)


def _describe(exc: BaseException) -> str:
    text = str(exc).strip()
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


def _rows(docs) -> list[dict]:
    return chunk_rows([doc_to_row(d) for d in docs])


# ---------------------------------------------------------------------------
# Ingest / documents
# ---------------------------------------------------------------------------

@router.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...), store: ChunkStore = Depends(_store)) -> IngestResponse:
    filename = file.filename or "upload"
    if Path(filename).suffix.lower() not in SUPPORTED_SUFFIXES:
        raise HTTPException(
            status_code=415, detail=f"Only {sorted(SUPPORTED_SUFFIXES)} files are supported"
        )
    contents = await file.read()
    source_id = source_id_for(filename)
    digest = content_hash(contents)

    duplicate = store.find_duplicate(source_id, digest)
    if duplicate is not None:
        reason, dup_source, dup_count = duplicate
        why = (
            "identical content is already indexed"
            if reason == "content"
            else "a document with the same name is already indexed"
        )
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    f"Duplicate document: {why} as '{dup_source}' "
                    f"({dup_count} chunks). Nothing was added."
                ),
                "reason": reason,
                "duplicate_source_id": dup_source,
                "duplicate_chunk_count": dup_count,
            },
        )

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / filename
        tmp_path.write_bytes(contents)
        try:
            doc = load_document(tmp_path)
        except NotImplementedError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Could not parse file: {exc}") from exc
        chunks, used_fallback = split_with_fallback(doc)

    if not chunks:
        raise HTTPException(status_code=422, detail="No chunks produced — the file appears to be empty.")

    try:
        rows = store.embed_chunks(chunks, digest)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503, detail=f"embedding model unavailable: {_describe(exc)}"
        ) from exc
    try:
        store.write_rows(rows)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500, detail=f"could not write to the index: {_describe(exc)}"
        ) from exc

    chunk_dicts = [to_chunk_dict(c) for c in chunks]
    for chunk in chunk_dicts:
        chunk["metadata"]["content_sha256"] = digest
    return IngestResponse(
        source_id=source_id,
        filename=filename,
        new_chunk_count=len(chunk_dicts),
        new_chunks=[new_chunk(c) for c in chunk_dicts],
        totals=_totals(store),
        used_fallback=used_fallback,
        note="No legal structure detected — used fallback paragraph chunking." if used_fallback else None,
    )


@router.delete("/documents/{source_id}", response_model=DeleteDocumentResponse)
def delete_document(source_id: str, store: ChunkStore = Depends(_store)) -> DeleteDocumentResponse:
    try:
        deleted = store.delete_source(source_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500, detail=f"could not update the index: {_describe(exc)}"
        ) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No indexed document with source_id {source_id!r}")
    return DeleteDocumentResponse(source_id=source_id, deleted_chunk_count=deleted, totals=_totals(store))


# ---------------------------------------------------------------------------
# Retrieve / query
# ---------------------------------------------------------------------------

@router.get("/retrieve", response_model=RetrieveResponse)
def retrieve(
    q: str,
    k: int = 5,
    rerank: bool = False,
    store: ChunkStore = Depends(_store),
    reranker_factory=Depends(deps.get_reranker_factory),
) -> RetrieveResponse:
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query 'q' must not be empty")
    if k < 1:
        raise HTTPException(status_code=400, detail="k must be >= 1")
    if not store.exists():
        raise HTTPException(status_code=409, detail="Index is empty — ingest a document first")

    variants = {
        "dense": _rows(dense_retriever(store, k).invoke(q)),
        "fts": _rows(bm25_retriever(store, k).invoke(q)),
        "hybrid": _rows(hybrid_retriever(store, k).invoke(q)),
    }
    if rerank:
        retriever = query_retriever(store, k=k, n=max(4 * k, k), reranker=reranker_factory())
        variants["hybrid_reranked"] = _rows(retriever.invoke(q))
    return RetrieveResponse(query=q, k=k, reranked=rerank, variants=variants)


def _trace(state: dict) -> dict:
    parsed = state["parsed"]
    return {
        "candidates": _rows(state["context"]),
        "prompt": state["prompt"],
        "raw_output": parsed.raw_text,
        "parsed_claims": [
            {"text": c.text, "cited_chunk_ids": list(c.cited_chunk_ids)} for c in parsed.claims
        ],
        "malformed_lines": list(parsed.malformed_lines),
        "resample_outputs": [r.raw_text for r in state.get("resamples") or []],
    }


@router.post("/query", response_model=QueryResponse)
def query(
    req: LCQueryRequest,
    store: ChunkStore = Depends(_store),
    reranker_factory=Depends(deps.get_reranker_factory),
    adapter_factory=Depends(deps.get_adapter_factory),
    nli_factory=Depends(deps.get_nli_factory),
):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")
    if not store.exists():
        raise HTTPException(status_code=409, detail="Index is empty — ingest a document first")

    reranker = reranker_factory() if req.rerank else None
    retriever = query_retriever(store, k=req.k, n=max(8 * req.k, QUERY_POOL_N), reranker=reranker)
    try:
        llm = adapter_factory()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"LLM backend unavailable: {exc}") from exc
    try:
        nli = nli_factory()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"NLI backend unavailable: {exc}") from exc

    chain = build_query_chain(retriever, llm, nli)
    try:
        state = chain.invoke(
            {
                "question": req.query,
                "self_consistency": req.self_consistency,
                "allow_general_knowledge": req.allow_general_knowledge,
            }
        )
    except GenerationError as exc:
        raise HTTPException(status_code=503, detail=f"LLM backend failed: {exc}") from exc

    parsed, result = state["parsed"], state["verification"]
    context_ids = [d.metadata["chunk_id"] for d in state["context"]]
    proof = ProofModel(**result.proof.to_dict())
    decision = result.vcs_result.decision
    if state["general_text"]:
        response = QueryResponse(
            query=req.query,
            answer_text=state["general_text"],
            abstained=False,
            decision=decision,
            vcs=None,
            context_chunk_ids=context_ids,
            proof=proof,
            answer_mode="general_knowledge",
            grounded_answer_text=parsed.raw_text,
        )
    else:
        response = QueryResponse(
            query=req.query,
            answer_text=parsed.raw_text,
            abstained=parsed.abstained,
            decision=decision,
            vcs=result.vcs_result.vcs,
            context_chunk_ids=context_ids,
            proof=proof,
            answer_mode="verified" if decision == "ANSWER" else "abstained",
        )
    if req.trace:
        return JSONResponse(response.model_dump() | {"trace": _trace(state)})
    return response


# ---------------------------------------------------------------------------
# Stats / embedding map / evaluation
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=StatsResponse)
def stats(store: ChunkStore = Depends(_store)) -> StatsResponse:
    df = store.all_rows()
    if df.empty:
        return StatsResponse(chunks=0, documents=0, sources=[])
    counts: dict[str, int] = {}
    for meta in df["metadata"]:
        counts[meta["source_id"]] = counts.get(meta["source_id"], 0) + 1
    sources = [
        SourceStat(source_id=s, chunks=n)
        for s, n in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    ]
    return StatsResponse(chunks=len(df), documents=len(counts), sources=sources)


@router.get("/embedding-map", response_model=EmbeddingMapResponse)
def embedding_map(store: ChunkStore = Depends(_store)) -> EmbeddingMapResponse:
    df = store.all_rows().reset_index(drop=True) if store.exists() else None
    if df is None or df.empty:
        return EmbeddingMapResponse(method="pca", points=[], sources=[])
    coords = pca_2d(np.vstack(df["vector"].to_numpy()))
    points = []
    for i, meta in enumerate(df["metadata"]):
        chunk_meta = json.loads(meta["chunk_metadata_json"])
        points.append(
            EmbeddingPoint(
                x=float(coords[i, 0]),
                y=float(coords[i, 1]),
                chunk_id=meta["chunk_id"],
                source_id=meta.get("source_id") or "",
                section_ref=chunk_meta.get("section_ref") or "",
            )
        )
    return EmbeddingMapResponse(
        method="pca", points=points, sources=sorted({p.source_id for p in points})
    )


@router.get("/evaluation", response_model=EvaluationResponse)
def evaluation() -> EvaluationResponse:
    runs = load_runs()
    if not runs:
        return EvaluationResponse(runs=[], message="No evaluation runs yet.")
    return EvaluationResponse(
        runs=[EvaluationRun(name=r["name"], config=r["config"], results=r["results"]) for r in runs]
    )


# ---------------------------------------------------------------------------
# Chats (same store and behaviour as src/api/routes/chats.py)
# ---------------------------------------------------------------------------

def _require_id(conversation_id: str) -> None:
    if not is_valid_id(conversation_id):
        raise HTTPException(status_code=400, detail="Malformed conversation id")


@router.get("/chats", response_model=ConversationList)
def list_chats(store: ChatStore = Depends(deps.get_chat_store)) -> ConversationList:
    return ConversationList(conversations=store.list())


@router.post("/chats", response_model=Conversation)
def create_chat(
    req: CreateConversationRequest | None = None, store: ChatStore = Depends(deps.get_chat_store)
) -> Conversation:
    return Conversation(**store.create(title=req.title if req else None))


@router.get("/chats/{conversation_id}", response_model=Conversation)
def get_chat(conversation_id: str, store: ChatStore = Depends(deps.get_chat_store)) -> Conversation:
    _require_id(conversation_id)
    conversation = store.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"No conversation {conversation_id}")
    return Conversation(**conversation)


@router.post("/chats/{conversation_id}/messages", response_model=Conversation)
def append_message(
    conversation_id: str, message: ChatMessage, store: ChatStore = Depends(deps.get_chat_store)
) -> Conversation:
    _require_id(conversation_id)
    if message.role not in ("user", "assistant"):
        raise HTTPException(status_code=422, detail="role must be 'user' or 'assistant'")
    payload = {k: v for k, v in message.model_dump().items() if v is not None}
    updated = store.append(conversation_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"No conversation {conversation_id}")
    return Conversation(**updated)


@router.delete("/chats/{conversation_id}")
def delete_chat(conversation_id: str, store: ChatStore = Depends(deps.get_chat_store)) -> dict:
    _require_id(conversation_id)
    if not store.delete(conversation_id):
        raise HTTPException(status_code=404, detail=f"No conversation {conversation_id}")
    return {"deleted": conversation_id}


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def create_app() -> FastAPI:
    app = FastAPI(title="Legal AI API (LangChain port)", version="0.1.0")

    @app.middleware("http")
    async def unhandled_error_to_json(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:  # noqa: BLE001
            log.exception("unhandled error in %s", request.url.path)
            return JSONResponse(
                status_code=500, content={"detail": f"internal error: {type(exc).__name__}: {exc}"}
            )

    extra = os.environ.get("LEGAL_AI_CORS_ORIGINS", "")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS + [o.strip() for o in extra.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        problem = missing_key_message()
        return {
            "status": "ok",
            "llm": {"provider": selected_provider(), "configured": problem is None, "problem": problem},
        }

    app.include_router(router)
    return app


app = create_app()
