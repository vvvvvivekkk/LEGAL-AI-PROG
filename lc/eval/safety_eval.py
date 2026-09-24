"""Acceptance criterion 2: safety, LangChain vs plain Python.

Replays data/eval/ablation_cache.json (the cached answers the 2026-09-23
verification ablation used) through the full chain twice in this process:

  langchain  CitationOutputParser -> Documents -> verification_step Runnable
  python     src.generation.parse_answer -> src.verification.verify_answer

on the clean set and on the two known-bad probes (fabricated_citation,
mismatched_claim, from src.evaluation.verification_ablation.perturb_cache).
No LLM calls; same roberta-large-mnli for both arms.

    .venv-lc/Scripts/python -m lc.eval.safety_eval

Writes experiments/langchain_port/safety/{langchain,python}/results.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.documents import Document

from lc.generation import CitationOutputParser
from lc.verification import verification_step
from src.evaluation.verification_ablation import PERTURBATIONS, load_cache, perturb_cache
from src.verification.chain import verify_answer
from src.verification.nli import RobertaMNLI
from src.verification.v5_vcs import ANSWER

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / "data" / "eval" / "ablation_cache.json"
OUT = REPO / "experiments" / "langchain_port" / "safety"


def _as_doc(row: dict) -> Document:
    meta = {
        "chunk_id": row["chunk_id"],
        "contextual_summary": row.get("contextual_summary", ""),
        "chunk_metadata": row.get("metadata") or {},
    }
    for key in ("rerank_score", "_relevance_score"):
        if key in row:
            meta[key] = row[key]
    return Document(page_content=row["text"], metadata=meta)


def _langchain_verifier(nli):
    parser = CitationOutputParser()
    step = verification_step(nli)

    def run(item, use_resamples: bool):
        return step.invoke(
            {
                "question": item.query,
                "context": [_as_doc(r) for r in item.context_chunks],
                "parsed": parser.parse(item.raw_text),
                "resamples": [parser.parse(t) for t in item.resample_texts] if use_resamples else [],
            }
        )

    return run


def _python_verifier(nli):
    def run(item, use_resamples: bool):
        resamples = item.resamples() if use_resamples else None
        return verify_answer(item.answer(), item.context_chunks, nli, resamples=resamples or None)

    return run


def _clean(cache, verify) -> dict:
    per_query, scores = [], []
    for item in cache:
        if not item.available:
            continue
        vr = verify(item, use_resamples=True).vcs_result
        if vr.vcs is not None:
            scores.append(vr.vcs)
        per_query.append({"query": item.query, "decision": vr.decision, "vcs": vr.vcs,
                          "per_claim_vcs": [c.vcs for c in vr.per_claim]})
    return {
        "mean_vcs": sum(scores) / len(scores) if scores else None,
        "n_answer": sum(q["decision"] == ANSWER for q in per_query),
        "n_abstain": sum(q["decision"] != ANSWER for q in per_query),
        "per_query": per_query,
    }


def _probe(cache, verify, mode: str) -> dict:
    total = surfaced = 0
    for item in perturb_cache(cache, mode):
        if not item.available or not item.claims:
            continue
        vr = verify(item, use_resamples=False).vcs_result
        total += len(item.claims)
        if vr.decision == ANSWER:
            surfaced += len(item.claims)
    return {"bad_claims_total": total, "bad_claims_surfaced": surfaced}


def main() -> None:
    cache = load_cache(CACHE)
    nli = RobertaMNLI()
    results = {}
    for name, make in (("langchain", _langchain_verifier), ("python", _python_verifier)):
        verify = make(nli)
        payload = _clean(cache, verify)
        payload["probes"] = {mode: _probe(cache, verify, mode) for mode in PERTURBATIONS}
        payload["surfaced_total"] = sum(p["bad_claims_surfaced"] for p in payload["probes"].values())
        payload["bad_total"] = sum(p["bad_claims_total"] for p in payload["probes"].values())
        run_dir = OUT / name
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "config.json").write_text(
            json.dumps({"pipeline": name, "arm": "full_chain", "cache": "data/eval/ablation_cache.json",
                        "nli": "roberta-large-mnli", "probes": list(PERTURBATIONS)}, indent=2),
            encoding="utf-8",
        )
        (run_dir / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        results[name] = payload
        print(f"{name}: mean_vcs={payload['mean_vcs']:.4f} ANSWER={payload['n_answer']} "
              f"ABSTAIN={payload['n_abstain']} surfaced={payload['surfaced_total']}/{payload['bad_total']}")

    lc_q, py_q = results["langchain"]["per_query"], results["python"]["per_query"]
    same_decision = sum(a["decision"] == b["decision"] for a, b in zip(lc_q, py_q))
    same_vcs = sum(a["vcs"] == b["vcs"] for a, b in zip(lc_q, py_q))
    print(f"identical decision: {same_decision}/{len(lc_q)}, identical VCS: {same_vcs}/{len(lc_q)}")
    (OUT / "comparison.json").write_text(
        json.dumps({"identical_decision": same_decision, "identical_vcs": same_vcs,
                    "n_queries": len(lc_q)}, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
