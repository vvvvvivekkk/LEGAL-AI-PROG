"""Natural Language Inference backend for V2/V3.

`NLIModel` is the thin interface: given a premise (the cited chunk text) and a
hypothesis (the claim), return an Entailment label plus a confidence. The real
backend wraps a local roberta-large-mnli via transformers; tests inject a fake
NLI so the entailment *logic* is exercised deterministically without a model
download. Swapping in a legal-domain NLI model later means adding a backend,
not touching V2/V3.
"""

from __future__ import annotations

from typing import Protocol

from src.verification.types import Entailment

DEFAULT_NLI_MODEL = "roberta-large-mnli"

# roberta-large-mnli label order is [contradiction, neutral, entailment].
_MNLI_LABELS = {
    "CONTRADICTION": Entailment.CONTRADICTS,
    "NEUTRAL": Entailment.NEUTRAL,
    "ENTAILMENT": Entailment.ENTAILS,
}


class NLIModel(Protocol):
    def classify(self, premise: str, hypothesis: str) -> tuple[Entailment, float]:
        ...


_pipeline_cache: dict = {}


def _get_pipeline(model_name: str):
    if model_name not in _pipeline_cache:
        from transformers import pipeline

        _pipeline_cache[model_name] = pipeline(
            "text-classification",
            model=model_name,
            top_k=None,
        )
    return _pipeline_cache[model_name]


class RobertaMNLI:
    """NLI backend backed by a local HuggingFace MNLI model."""

    def __init__(self, model_name: str = DEFAULT_NLI_MODEL):
        self.model_name = model_name

    def classify(self, premise: str, hypothesis: str) -> tuple[Entailment, float]:
        clf = _get_pipeline(self.model_name)
        # NLI convention: text = premise, text_pair = hypothesis.
        scores = clf({"text": premise, "text_pair": hypothesis})
        # top_k=None returns a list of {label, score}; pick the argmax.
        best = max(scores, key=lambda d: d["score"])
        label = _MNLI_LABELS.get(best["label"].upper(), Entailment.NEUTRAL)
        return label, float(best["score"])
