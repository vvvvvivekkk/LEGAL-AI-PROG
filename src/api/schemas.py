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


class DeleteDocumentResponse(BaseModel):
    source_id: str
    deleted_chunk_count: int
    totals: IndexTotals


class RetrieveResponse(BaseModel):
    query: str
    k: int
    reranked: bool
    variants: dict[str, list[ChunkResult]]


class QueryRequest(BaseModel):
    query: str
    # Wider than the Search default: generation needs enough context to cover a
    # clause split across adjacent chunks, not just the single best-matching one.
    k: int = 12
    rerank: bool = True
    self_consistency: int = 0
    # When verification declines a *general concept* question, answer it from
    # the model's own knowledge instead, clearly labelled. Never applies to
    # questions about the indexed documents.
    allow_general_knowledge: bool = True


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


# How an answer was produced. "verified" and "abstained" are the document-grounded
# path; "general_knowledge" is the uncited fallback and carries no VCS.
ANSWER_MODES = ("verified", "abstained", "general_knowledge")


class QueryResponse(BaseModel):
    query: str
    answer_text: str
    abstained: bool
    decision: str
    vcs: float | None
    context_chunk_ids: list[str]
    proof: ProofModel
    answer_mode: str = "verified"
    # Set only when answer_mode == "general_knowledge": the document-grounded
    # attempt that was declined, kept so the UI can still show what was tried.
    grounded_answer_text: str | None = None


class ChatMessage(BaseModel):
    id: str | None = None
    role: str  # "user" | "assistant"
    text: str
    created_at: str | None = None
    # Present on assistant messages: the whole verification result as it was
    # shown, so reopening a conversation reproduces the proof, not just text.
    answer_mode: str | None = None
    decision: str | None = None
    vcs: float | None = None
    abstained: bool | None = None
    context_chunk_ids: list[str] | None = None
    proof: ProofModel | None = None


class ChatSummary(BaseModel):
    id: str
    title: str
    created_at: str | None = None
    updated_at: str | None = None
    message_count: int = 0


class Conversation(BaseModel):
    id: str
    title: str
    created_at: str | None = None
    updated_at: str | None = None
    messages: list[ChatMessage] = []


class ConversationList(BaseModel):
    conversations: list[ChatSummary] = []


class CreateConversationRequest(BaseModel):
    title: str | None = None


class EvaluationRun(BaseModel):
    name: str
    config: dict
    results: dict
    # Plain-language description and headline numbers (src/evaluation/results_store.py).
    kind: str = "other"
    about: str = ""
    highlights: list[dict] = []


class EvaluationResponse(BaseModel):
    runs: list[EvaluationRun]
    message: str | None = None
