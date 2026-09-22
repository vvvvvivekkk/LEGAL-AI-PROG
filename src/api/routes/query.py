"""POST /query — full pipeline: retrieval → generation → verification.

Returns the generated answer plus its Proof Object (VCS, per-claim verdicts,
quoted spans). Generation and NLI models are resolved lazily via factories so a
missing API key or model surfaces as a clean 503 rather than a startup crash.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import (
    get_adapter_factory,
    get_db_path,
    get_embedder,
    get_nli_factory,
    get_reranker_factory,
)
from src.api.schemas import ProofModel, QueryRequest, QueryResponse
from src.generation.general_knowledge import (
    answer_from_general_knowledge,
    is_general_concept_question,
)
from src.generation.generator import generate
from src.indexing.build import open_table, table_exists
from src.retrieval.config import RetrievalConfig
from src.retrieval.retriever import Retriever
from src.verification.chain import verify_answer

router = APIRouter()

# Floor on the candidate pool for a generation query, regardless of k.
QUERY_POOL_N = 100


@router.post("/query", response_model=QueryResponse)
def query(
    req: QueryRequest,
    db_path: str = Depends(get_db_path),
    embedder=Depends(get_embedder),
    reranker_factory=Depends(get_reranker_factory),
    adapter_factory=Depends(get_adapter_factory),
    nli_factory=Depends(get_nli_factory),
) -> QueryResponse:
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")
    if not table_exists(db_path):
        raise HTTPException(status_code=409, detail="Index is empty — ingest a document first")

    # Retrieval
    table = open_table(db_path)
    # The pool is deliberately much deeper than k: a legal answer often lives in
    # a clause the fused ranking buries (see RetrievalConfig.DEFAULT_N), and the
    # reranker can only promote chunks that were fetched in the first place.
    config = RetrievalConfig(
        mode="hybrid", use_reranker=req.rerank, k=req.k, n=max(8 * req.k, QUERY_POOL_N)
    )
    reranker = reranker_factory() if req.rerank else None
    retriever = Retriever(table, config=config, embedder=embedder, reranker=reranker)
    context = retriever.retrieve(req.query)

    # Generation + verification models (lazy; report config errors as 503)
    try:
        adapter = adapter_factory()
    except Exception as exc:  # noqa: BLE001 - e.g. missing LLM_API_KEY
        raise HTTPException(status_code=503, detail=f"LLM backend unavailable: {exc}") from exc
    try:
        nli = nli_factory()
    except Exception as exc:  # noqa: BLE001 - NLI model load failure
        raise HTTPException(status_code=503, detail=f"NLI backend unavailable: {exc}") from exc

    answer = generate(req.query, context, adapter)

    resamples = None
    if req.self_consistency and not answer.abstained:
        resamples = [generate(req.query, context, adapter) for _ in range(req.self_consistency)]

    result = verify_answer(answer, context, nli, resamples=resamples)
    proof = result.proof

    # The documents could not support an answer. If the question was never about
    # the documents -- "what is an NDA?" -- answer it from general knowledge and
    # label it as such, rather than abstaining on a question the corpus was
    # never going to answer. Document-specific questions keep abstaining.
    declined = answer.abstained or result.vcs_result.decision != "ANSWER"
    if declined and req.allow_general_knowledge and is_general_concept_question(req.query):
        try:
            general_text = answer_from_general_knowledge(req.query, adapter)
        except Exception:  # noqa: BLE001 - fall back to the honest abstention
            general_text = ""
        if general_text:
            return QueryResponse(
                query=req.query,
                answer_text=general_text,
                abstained=False,
                decision=result.vcs_result.decision,
                vcs=None,  # nothing was verified against the documents
                context_chunk_ids=answer.context_chunk_ids,
                proof=ProofModel(**proof.to_dict()),
                answer_mode="general_knowledge",
                grounded_answer_text=answer.raw_text,
            )

    return QueryResponse(
        query=req.query,
        answer_text=answer.raw_text,
        abstained=answer.abstained,
        decision=result.vcs_result.decision,
        vcs=result.vcs_result.vcs,
        context_chunk_ids=answer.context_chunk_ids,
        proof=ProofModel(**proof.to_dict()),
        answer_mode="verified" if result.vcs_result.decision == "ANSWER" else "abstained",
    )
