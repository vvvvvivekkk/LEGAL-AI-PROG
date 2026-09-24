"""General-knowledge fallback for conceptual questions.

The pipeline's whole point is that document-grounded answers are verified, so
abstention is the right outcome when a question about the indexed documents
cannot be supported by them. But a question like "what is an NDA?" is not
asking about the documents at all -- abstaining on it is unhelpful, and the
answer was never going to carry citations in the first place.

So: when verification declines AND the question is asking for a general legal
concept rather than something specific to the corpus, the answer is
regenerated from the model's own knowledge and labelled as such. It is never
merged with the verified path -- the API returns a distinct answer_mode and
no VCS, and the UI badges it separately.
"""

from __future__ import annotations

import re

from src.generation.base import LLMAdapter

GENERAL_KNOWLEDGE_SYSTEM = """You are a legal information assistant answering a \
general conceptual question from your own knowledge.

Rules:
1. Answer the general legal concept plainly, in at most four sentences.
2. Do NOT cite chunk ids or pretend to quote any document -- you have no document \
context for this answer.
3. Do not claim anything about the user's own documents or agreements.
4. If the question is not actually a general legal concept question, say so briefly.
"""

# "What is X" / "define X" style openers.
_DEFINITIONAL = re.compile(
    r"^\s*(what(?:'s| is| are)\b|what do(?:es)?\b.*\bmean\b|define\b|definition of\b"
    r"|explain\b|tell me about\b|meaning of\b)",
    re.IGNORECASE,
)

# Markers that the question is about *these* documents, not a general concept.
# If any of these appear, the question belongs on the verified path and an
# abstention is the correct, honest answer.
_DOCUMENT_SPECIFIC = re.compile(
    r"\b(this|these|my|our|the) (agreement|contract|document|nda|clause|section|file|policy)\b"
    r"|\bin (the|this) (agreement|contract|document|file)\b"
    # "...under the Urban Tenancy Act?" names a specific instrument.
    r"|\bunder (the|this)\b"
    r"|\baccording to\b|\bwhat happens if\b|\bwhich (document|agreement|file)\b"
    r"|\bsection \d|\bclause \d|\bdoes the (agreement|contract|document)\b"
    r"|\bhow long\b|\bwhat is the (term|duration|notice period|governing law|jurisdiction)\b",
    re.IGNORECASE,
)


def is_general_concept_question(query: str) -> bool:
    """True when the query asks for a general legal concept, not corpus content.

    Deliberately conservative: a query only qualifies if it opens like a
    definition request AND carries no marker tying it to the indexed documents.
    Anything ambiguous stays on the verified path, where abstaining is correct.
    """
    text = (query or "").strip()
    if not text:
        return False
    if _DOCUMENT_SPECIFIC.search(text):
        return False
    return bool(_DEFINITIONAL.search(text))


def answer_from_general_knowledge(query: str, adapter: LLMAdapter) -> str:
    """Answer a conceptual question from the model's own knowledge (uncited)."""
    return adapter.complete(GENERAL_KNOWLEDGE_SYSTEM, query).strip()
