"""Citation-forced prompt template.

The model is constrained two ways: (1) it may only use the provided context,
and (2) every factual claim must end with a citation to the chunk id(s) it
came from. The strict one-claim-per-line, citation-terminated format is what
makes phase-5 verification tractable — the parser can map each claim back to
its cited evidence deterministically.
"""

from __future__ import annotations

ABSTENTION_MARKER = "INSUFFICIENT_CONTEXT"

SYSTEM_PROMPT = f"""You are a legal question-answering assistant. You answer ONLY from the \
provided context passages, never from prior knowledge.

Rules you must follow exactly:
1. Use ONLY the information in the CONTEXT passages below. Do not add facts that \
are not stated there.
2. Write each factual claim on its own line.
3. End every claim line with a citation to the chunk id(s) it is supported by, in \
square brackets, e.g. [urban_tenancy_act_2019::s4:b]. If a claim draws on more than \
one passage, cite them all: [id_one][id_two].
4. Never write a factual sentence without a citation.
5. If the context does not contain enough information to answer, respond with a \
single line beginning exactly with "{ABSTENTION_MARKER}:" followed by a short reason, \
and nothing else.
"""


def format_context(context_chunks: list[dict]) -> str:
    """Render retrieved chunks into a citable CONTEXT block."""
    blocks = []
    for chunk in context_chunks:
        metadata = chunk.get("metadata") or {}
        ref = metadata.get("section_ref", "")
        act = metadata.get("act", "")
        header = f"[{chunk['chunk_id']}]"
        if ref or act:
            header += f" ({ref}{' — ' if ref and act else ''}{act})"
        summary = chunk.get("contextual_summary", "")
        text = chunk.get("text", "")
        body = f"{summary}\n{text}".strip() if summary else text
        blocks.append(f"{header}\n{body}")
    return "\n\n".join(blocks)


def build_user_prompt(query: str, context_chunks: list[dict]) -> str:
    context = format_context(context_chunks)
    return f"CONTEXT:\n{context}\n\nQUESTION:\n{query}\n\nANSWER (follow the citation rules exactly):"


def build_prompt(query: str, context_chunks: list[dict]) -> tuple[str, str]:
    """Return (system, user) prompt strings for the given query + context."""
    return SYSTEM_PROMPT, build_user_prompt(query, context_chunks)
