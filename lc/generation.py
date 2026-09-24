"""Citation-forced generation as an LCEL chain.

    ChatPromptTemplate (src/'s exact system prompt) | chat model | StrOutputParser
    | CitationOutputParser

The chat model is picked from the same env vars as src/generation/factory.py
(LLM_PROVIDER, LLM_MODEL and the provider keys) and built from the matching
LangChain integration. A plain object with complete(system, user) -- the
test stubs, or any src/ adapter -- is accepted too and wrapped as a Runnable,
so tests keep injecting the stubs they use today.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import BaseOutputParser, StrOutputParser
from langchain_core.prompt_values import PromptValue
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda

from src.config import env
from src.generation.general_knowledge import GENERAL_KNOWLEDGE_SYSTEM
from src.generation.prompt import ABSTENTION_MARKER, SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

# The system prompt is src/'s constant, imported rather than copied so the two
# can never drift. Both prompts go in as variables, not template text: SAC
# chunk text is arbitrary document content and may contain literal braces.
ANSWER_PROMPT = ChatPromptTemplate.from_messages([("system", "{system}"), ("human", "{user}")])
GENERAL_PROMPT = ChatPromptTemplate.from_messages([("system", "{system}"), ("human", "{question}")])

USER_TEMPLATE = (
    "CONTEXT:\n{context}\n\nQUESTION:\n{question}\n\nANSWER (follow the citation rules exactly):"
)


def format_context(docs: list[Document]) -> str:
    """Render retrieved chunk Documents into the citable CONTEXT block."""
    blocks = []
    for doc in docs:
        meta = doc.metadata.get("chunk_metadata") or {}
        ref = meta.get("section_ref", "")
        act = meta.get("act", "")
        header = f"[{doc.metadata['chunk_id']}]"
        if ref or act:
            header += f" ({ref}{' — ' if ref and act else ''}{act})"
        summary = doc.metadata.get("contextual_summary", "")
        body = f"{summary}\n{doc.page_content}".strip() if summary else doc.page_content
        blocks.append(f"{header}\n{body}")
    return "\n\n".join(blocks)


def prompt_inputs(inputs: dict) -> dict:
    """{question, context: [Document]} -> the variables ANSWER_PROMPT takes."""
    return {
        "system": SYSTEM_PROMPT,
        "user": USER_TEMPLATE.format(
            context=format_context(inputs["context"]), question=inputs["question"]
        ),
    }


def general_inputs(inputs: dict) -> dict:
    return {"system": GENERAL_KNOWLEDGE_SYSTEM, "question": inputs["question"]}


# ---------------------------------------------------------------------------
# Output parser
# ---------------------------------------------------------------------------

_CITATION_RE = re.compile(r"\[([^\[\]]*)\]")


@dataclass
class ParsedClaim:
    text: str
    cited_chunk_ids: list[str] = field(default_factory=list)


@dataclass
class ParsedAnswer:
    raw_text: str
    abstained: bool
    claims: list[ParsedClaim] = field(default_factory=list)
    malformed_lines: list[str] = field(default_factory=list)


class CitationOutputParser(BaseOutputParser[ParsedAnswer]):
    """One claim per line, each ending in [chunk_id] citations; a response
    opening with INSUFFICIENT_CONTEXT: is an abstention. Mirrors
    src/generation/parser.py + generator.parse_answer."""

    @staticmethod
    def citations(line: str) -> list[str]:
        ids: list[str] = []
        for group in _CITATION_RE.findall(line):
            for part in group.split(","):
                cid = part.strip()
                if cid and cid not in ids:
                    ids.append(cid)
        return ids

    def parse(self, text: str) -> ParsedAnswer:
        if text.strip().startswith(f"{ABSTENTION_MARKER}:"):
            return ParsedAnswer(raw_text=text, abstained=True)
        claims: list[ParsedClaim] = []
        malformed: list[str] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            ids = self.citations(line)
            if ids:
                claims.append(ParsedClaim(_CITATION_RE.sub("", line).strip(), ids))
            else:
                malformed.append(line)
        return ParsedAnswer(raw_text=text, abstained=False, claims=claims, malformed_lines=malformed)

    @property
    def _type(self) -> str:
        return "citation_answer"


# ---------------------------------------------------------------------------
# Chat model selection
# ---------------------------------------------------------------------------

PROVIDERS = ("claude", "openai", "gemini", "groq")

# Same models and output budgets as the src/ adapters. temperature is left at
# the provider's own default, as src/ does, rather than LangChain's.
DEFAULTS = {
    "claude": ("claude-sonnet-4-6", 1024),
    "openai": ("gpt-4o", 1024),
    "gemini": ("gemini-2.5-flash", 4096),
    "groq": ("openai/gpt-oss-120b", 4096),
}


def chat_model_from_env(provider: str | None = None) -> BaseLanguageModel:
    provider = (provider or env("LLM_PROVIDER") or "claude").lower()
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown LLM_PROVIDER {provider!r}; expected one of {PROVIDERS}")
    default_model, max_tokens = DEFAULTS[provider]
    model = env("LLM_MODEL") or default_model

    if provider == "claude":
        from langchain_anthropic import ChatAnthropic

        key = env("LLM_API_KEY")
        if not key:
            raise ValueError("ChatAnthropic requires an API key (LLM_API_KEY)")
        return ChatAnthropic(model=model, max_tokens=max_tokens, api_key=key)
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        key = env("LLM_API_KEY")
        if not key:
            raise ValueError("ChatOpenAI requires an API key (LLM_API_KEY)")
        return ChatOpenAI(model=model, max_tokens=max_tokens, api_key=key)
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        key = env("GEMINI_API_KEY")
        if not key:
            raise ValueError("ChatGoogleGenerativeAI requires an API key (GEMINI_API_KEY)")
        llm = ChatGoogleGenerativeAI(
            model=model, max_output_tokens=max_tokens, google_api_key=key, max_retries=0
        )
        # The free tier 503s under load; src/ retries 6x with exponential
        # backoff (base 2s, cap 30s) plus jitter. with_retry is the closest
        # LangChain equivalent (it retries on any exception, not only 503).
        return llm.with_retry(stop_after_attempt=6, wait_exponential_jitter=True)
    from langchain_groq import ChatGroq

    key = env("GROQ_API_KEY") or env("LLM_API_KEY")
    if not key:
        raise ValueError("ChatGroq requires an API key: set GROQ_API_KEY (or LLM_API_KEY)")
    # src/ sends no temperature, so Groq applies its API default (1.0). ChatGroq
    # cannot leave it unset (non-optional float, own default 0.7), so pass 1.0.
    return ChatGroq(model=model, max_tokens=max_tokens, api_key=key, temperature=1.0)


def as_chat_runnable(llm) -> Runnable:
    """A LangChain chat model as-is; a complete(system, user) object wrapped.

    The wrapper receives the rendered ChatPromptValue and hands its system and
    human message text to complete(), so a stub sees byte-for-byte the prompt a
    real model would.
    """
    if isinstance(llm, Runnable):
        return llm

    def _call(prompt: PromptValue) -> str:
        messages = prompt.to_messages()
        system = "\n".join(m.content for m in messages if m.type == "system")
        user = "\n".join(m.content for m in messages if m.type == "human")
        return llm.complete(system, user)

    return RunnableLambda(_call, name=type(llm).__name__)


def answer_chain(llm) -> Runnable:
    """{question, context} -> ParsedAnswer:  prompt | llm | str | citation parser."""
    return (
        RunnableLambda(prompt_inputs, name="prompt_inputs")
        | ANSWER_PROMPT
        | as_chat_runnable(llm)
        | StrOutputParser()
        | CitationOutputParser()
    )


def general_knowledge_chain(llm) -> Runnable:
    """{question} -> uncited general-knowledge answer text."""
    return (
        RunnableLambda(general_inputs, name="general_inputs")
        | GENERAL_PROMPT
        | as_chat_runnable(llm)
        | StrOutputParser()
        | RunnableLambda(lambda s: s.strip(), name="strip")
    )
