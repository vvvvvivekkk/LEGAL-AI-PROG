"""GET /evaluation — return logged experiment runs from /experiments.

Returns "no runs yet" until phase 6 produces runs (or run_retrieval_eval.py is
executed manually).
"""

from __future__ import annotations

from fastapi import APIRouter

from src.api.schemas import EvaluationResponse, EvaluationRun
from src.evaluation.results_store import load_runs

router = APIRouter()


@router.get("/evaluation", response_model=EvaluationResponse)
def evaluation() -> EvaluationResponse:
    runs = load_runs()
    if not runs:
        return EvaluationResponse(runs=[], message="No evaluation runs yet.")
    return EvaluationResponse(
        runs=[EvaluationRun(name=r["name"], config=r["config"], results=r["results"]) for r in runs],
    )
