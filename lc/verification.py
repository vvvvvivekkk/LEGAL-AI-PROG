"""V1-V6 verification and the abstain / general-knowledge decision as Runnables.

LangChain has no citation-existence check, NLI entailment gate, atomic-claim
fidelity, self-consistency scoring, calibrated abstention or proof object, so
none of this is re-implemented: the pure functions in src/verification/ are
called as-is (same gates, weights 0.40/0.35/0.25, threshold 0.60) and wrapped
as RunnableLambdas so they compose into the LCEL pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.documents import Document
from langchain_core.runnables import Runnable, RunnableLambda

from lc.generation import ParsedAnswer, ParsedClaim
from lc.splitters import to_chunk_dict
from src.generation.general_knowledge import is_general_concept_question
from src.verification.chain import VerificationResult, verify_answer
from src.verification.nli import NLIModel
from src.verification.v5_vcs import VCSConfig


@dataclass
class VerifiableAnswer:
    """The attribute shape src/verification reads (same as src's Answer)."""

    query: str
    raw_text: str
    claims: list[ParsedClaim] = field(default_factory=list)
    context_chunk_ids: list[str] = field(default_factory=list)
    abstained: bool = False
    malformed_lines: list[str] = field(default_factory=list)


def doc_to_row(doc: Document) -> dict:
    """A retrieved chunk Document as the row dict src/verification consumes."""
    row = to_chunk_dict(doc)
    for key in ("rerank_score", "_relevance_score", "_distance", "_score", "expanded_neighbor"):
        if key in doc.metadata:
            row[key] = doc.metadata[key]
    return row


def to_answer(question: str, parsed: ParsedAnswer, context: list[Document]) -> VerifiableAnswer:
    return VerifiableAnswer(
        query=question,
        raw_text=parsed.raw_text,
        claims=list(parsed.claims),
        context_chunk_ids=[d.metadata["chunk_id"] for d in context],
        abstained=parsed.abstained,
        malformed_lines=list(parsed.malformed_lines),
    )


def verification_step(nli: NLIModel, config: VCSConfig | None = None) -> Runnable:
    """{question, context, parsed, resamples?} -> VerificationResult (VCS + proof)."""

    def _verify(state: dict) -> VerificationResult:
        answer = to_answer(state["question"], state["parsed"], state["context"])
        resamples = [
            to_answer(state["question"], r, state["context"]) for r in state.get("resamples") or []
        ]
        return verify_answer(
            answer,
            [doc_to_row(d) for d in state["context"]],
            nli,
            resamples=resamples or None,
            config=config,
        )

    return RunnableLambda(_verify, name="verify_v1_v6")


def wants_general_knowledge(state: dict) -> bool:
    """The documents declined AND the question is a general legal concept."""
    declined = state["parsed"].abstained or state["verification"].vcs_result.decision != "ANSWER"
    return (
        declined
        and state.get("allow_general_knowledge", True)
        and is_general_concept_question(state["question"])
    )
