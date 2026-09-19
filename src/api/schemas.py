"""Pydantic response/request models for the API."""

from __future__ import annotations

from pydantic import BaseModel


class ChunkResult(BaseModel):
    chunk_id: str | None = None
    text: str | None = None
    contextual_summary: str | None = None
    metadata: dict = {}
    score: float | None = None
    score_kind: str | None = None


class NewChunk(BaseModel):
    chunk_id: str
    text: str
    contextual_summary: str
    metadata: dict = {}


class IndexTotals(BaseModel):
    chunks: int
    documents: int


class SourceStat(BaseModel):
    source_id: str
    chunks: int


class StatsResponse(BaseModel):
    chunks: int
    documents: int
    sources: list[SourceStat] = []


class EmbeddingPoint(BaseModel):
    x: float
    y: float
    chunk_id: str
    source_id: str
    section_ref: str = ""


class EmbeddingMapResponse(BaseModel):
    method: str
    points: list[EmbeddingPoint] = []
    sources: list[str] = []


class IngestResponse(BaseModel):
    source_id: str
    filename: str
    new_chunk_count: int
    new_chunks: list[NewChunk]
    totals: IndexTotals
    used_fallback: bool = False
    note: str | None = None


class RetrieveResponse(BaseModel):
    query: str
    k: int
    reranked: bool
    variants: dict[str, list[ChunkResult]]


class QueryRequest(BaseModel):
    query: str
    k: int = 5
    rerank: bool = True
    self_consistency: int = 0


class ClaimProofModel(BaseModel):
    claim_text: str
    supporting_chunk_ids: list[str]
    quoted_span: str
    verdicts: dict
    vcs_contribution: float


class ProofModel(BaseModel):
    query: str
    answer_text: str
    vcs: float | None
    decision: str
    threshold: float
    abstained: bool
    claims: list[ClaimProofModel]


class QueryResponse(BaseModel):
    query: str
    answer_text: str
    abstained: bool
    decision: str
    vcs: float | None
    context_chunk_ids: list[str]
    proof: ProofModel


class EvaluationRun(BaseModel):
    name: str
    config: dict
    results: dict


class EvaluationResponse(BaseModel):
    runs: list[EvaluationRun]
    message: str | None = None
