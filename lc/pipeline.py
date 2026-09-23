"""The /query pipeline as one LCEL chain.

    question
      -> retrieve      (ContextualCompressionRetriever: fused pool -> cross-encoder -> k)
      -> generate      (prompt | llm | str | citation parser)
      -> resample      (optional, V4 self-consistency)
      -> verify        (V1-V6 Runnable)
      -> fallback      (RunnableBranch: general-knowledge answer, or pass through)

Every step is a RunnablePassthrough.assign, so the state that comes out keeps
each intermediate: the scored candidates, the exact prompt messages, the raw
model text, the parsed claims and the verification result. That state is what
the API's optional trace returns.
"""

from __future__ import annotations

from operator import itemgetter

from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import (
    Runnable,
    RunnableBranch,
    RunnableLambda,
    RunnablePassthrough,
)

from lc.generation import (
    ANSWER_PROMPT,
    answer_chain,
    general_knowledge_chain,
    prompt_inputs,
)
from lc.verification import verification_step, wants_general_knowledge
from src.verification.nli import NLIModel


class GenerationError(RuntimeError):
    """The LLM provider failed (rate limit, quota, outage); the API maps it to 503."""


def _guard(runnable: Runnable, name: str) -> Runnable:
    def _call(state: dict, config=None):
        try:
            return runnable.invoke(state, config)
        except Exception as exc:  # noqa: BLE001
            raise GenerationError(f"{type(exc).__name__}: {exc}") from exc

    return RunnableLambda(_call, name=name)


def _prompt_messages(state: dict) -> list[dict]:
    value = ANSWER_PROMPT.invoke(prompt_inputs(state))
    return [{"role": m.type, "content": m.content} for m in value.to_messages()]


def build_query_chain(retriever: BaseRetriever, llm, nli: NLIModel) -> Runnable:
    """Input: {question, self_consistency, allow_general_knowledge}."""
    answer = answer_chain(llm)

    def _resamples(state: dict, config=None) -> list:
        n = state.get("self_consistency") or 0
        if not n or state["parsed"].abstained:
            return []
        # Sequential, like src/: resamples share the provider's rate limit.
        return answer.batch([state] * n, config={"max_concurrency": 1})

    def _general(state: dict, config=None) -> str:
        try:
            return general_knowledge_chain(llm).invoke(state, config)
        except Exception:  # noqa: BLE001 - fall back to the honest abstention
            return ""

    return (
        RunnablePassthrough.assign(context=itemgetter("question") | retriever)
        | RunnablePassthrough.assign(prompt=RunnableLambda(_prompt_messages, name="prompt"))
        | RunnablePassthrough.assign(parsed=_guard(answer, "generate"))
        | RunnablePassthrough.assign(resamples=_guard(RunnableLambda(_resamples), "resample"))
        | RunnablePassthrough.assign(verification=verification_step(nli))
        | RunnableBranch(
            (
                wants_general_knowledge,
                RunnablePassthrough.assign(general_text=RunnableLambda(_general, name="general")),
            ),
            RunnablePassthrough.assign(general_text=lambda _: None),
        )
    )
