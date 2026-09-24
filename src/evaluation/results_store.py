"""Read logged experiment runs from /experiments for the API's /evaluation view.

Each run is a directory under experiments/ containing config.json and/or
results.json (written by run_retrieval_eval.py). A sweep groups several runs in
one directory (experiments/<date>-ablations/retrieval/<config>/), so nested run
directories are found too and named by their path relative to experiments/.
This reader is deliberately tolerant: a missing experiments/ dir or a run
missing a file just yields fewer/empty fields rather than raising — the UI
shows "no runs yet".
"""

from __future__ import annotations

import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXPERIMENTS_DIR = _REPO_ROOT / "experiments"


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


# How deep below experiments/ a run directory may sit. One level is a plain
# run, two is a sweep grouping its arms, three is a sweep of sweeps.
MAX_RUN_DEPTH = 3


def load_runs(experiments_dir: str | Path = DEFAULT_EXPERIMENTS_DIR) -> list[dict]:
    """Return [{name, config, results}] for every run directory, name-sorted.

    A directory counts as a run when it holds a config.json or results.json.
    Sweeps nest their arms in subdirectories, so the search descends into a
    directory that is not itself a run, and keeps descending past one that is —
    a sweep may carry its own summary alongside per-arm subdirectories. Names
    are the path relative to experiments/, so nested runs stay distinguishable.
    """
    root = Path(experiments_dir)
    if not root.is_dir():
        return []

    runs: list[dict] = []

    def walk(directory: Path, depth: int) -> None:
        if depth > MAX_RUN_DEPTH:
            return
        for child in sorted(p for p in directory.iterdir() if p.is_dir()):
            config = _read_json(child / "config.json")
            results = _read_json(child / "results.json")
            if config or results:
                name = child.relative_to(root).as_posix()
                runs.append(
                    {
                        "name": name,
                        "config": config,
                        "results": results,
                        **describe_run(name, config, results),
                    }
                )
            walk(child, depth + 1)

    walk(root, 1)
    return runs


# ---------------------------------------------------------------------------
# Plain-language description of each run for the Evaluation page.
#
# Only retrieval runs have precision/recall/F1. Every other kind of run stores
# different numbers, so each is recognised by the shape of its results.json and
# reduced to a few headline figures, read from the file and never typed in by
# hand. The wording is kept in sync with experiments/README.md.

_ARM_LABELS = {
    "full_chain": "all six checks on",
    "minus_v1": "V1 (citation exists) switched off",
    "minus_v2": "V2 (NLI entailment) switched off",
    "minus_v3": "V3 (atomic fidelity) switched off",
    "minus_v4": "V4 (self-consistency) switched off",
    "minus_v5": "V5 (the score gate) switched off",
    "minus_v6": "V6 (proof object) switched off",
}


def _hl(label: str, value) -> dict:
    return {"label": label, "value": str(value)}


def _fmt(x, digits: int = 3) -> str:
    """Round half-up on the decimal value, so 0.7675 shows as 0.768 as in the paper
    (plain float formatting gives 0.767, because 0.7675 is stored as 0.76749...)."""
    if not isinstance(x, (int, float)):
        return "—"
    return str(Decimal(str(x)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))


def _probe_counts(probes: dict) -> tuple[int, int]:
    shown = sum(p.get("bad_claims_surfaced", 0) for p in probes.values() if isinstance(p, dict))
    total = sum(p.get("bad_claims_total", 0) for p in probes.values() if isinstance(p, dict))
    return shown, total


def describe_run(name: str, config: dict, results: dict) -> dict:
    """Return {"kind", "about", "highlights"} for one run. Never raises."""
    try:
        return _describe(name, config or {}, results or {})
    except Exception:  # noqa: BLE001 - a malformed file must not break the page
        return {"kind": "other", "about": "", "highlights": []}


def _describe(name: str, config: dict, results: dict) -> dict:
    leaf = name.rsplit("/", 1)[-1]

    if isinstance(results.get("aggregate"), dict) and "f1" in results["aggregate"]:
        chunking = {"sac": "SAC", "fallback": "paragraph fallback"}.get(config.get("chunking"))
        pipeline = {"python": "plain Python", "langchain": "LangChain"}.get(config.get("pipeline"))
        parts = [
            "Retrieval test on 10 labelled questions over the 5 synthetic statutes.",
            f"Chunking: {chunking}." if chunking else "",
            f"Pipeline: {pipeline}." if pipeline else "",
            "Scores whether the right clause is in the top k.",
        ]
        return {"kind": "retrieval", "about": " ".join(p for p in parts if p), "highlights": []}

    if "arm" in results and "mean_vcs" in results and "n_answer" in results:
        shown, total = _probe_counts(results.get("probes") or {})
        arm = results["arm"]
        return {
            "kind": "verification_arm",
            "about": (
                f"Verification ablation with {_ARM_LABELS.get(arm, arm)}: 10 cached answers "
                f"plus {total} deliberately corrupted claims."
            ),
            "highlights": [
                _hl("Mean VCS", _fmt(results.get("mean_vcs"))),
                _hl("Answered / refused", f"{results.get('n_answer')} / {results.get('n_abstain')}"),
                _hl("Bad claims shown", f"{shown} / {total}"),
            ],
        }

    if isinstance(results.get("arms"), dict) and isinstance(results.get("probes"), dict):
        probes = results["probes"]
        def shown_for(arm):
            return sum(p.get(arm, {}).get("bad_claims_surfaced", 0) for p in probes.values())
        total = sum(p.get("full_chain", {}).get("bad_claims_total", 0) for p in probes.values())
        return {
            "kind": "verification_sweep",
            "about": (
                "Summary of the verification ablation: each of the six checks switched off in "
                "turn, on clean answers and on corrupted claims. Per-arm results are listed below it."
            ),
            "highlights": [
                _hl("Arms", len(results["arms"])),
                _hl("Bad shown, full chain", f"{shown_for('full_chain')} / {total}"),
                _hl("Bad shown, without V5", f"{shown_for('minus_v5')} / {total}"),
            ],
        }

    summary = results.get("summary") if isinstance(results.get("summary"), dict) else {}

    if "labels_before_fixes" in summary:
        before = summary["labels_before_fixes"]
        n = sum(before.values())
        lat = summary.get("query_latency_s") or {}
        return {
            "kind": "end_to_end",
            "about": (
                "End-to-end test through the web app: 5 real documents, 15 questions whose "
                "answers were written down before the run, each answer judged by hand."
            ),
            "highlights": [
                _hl("Wrong but verified", f"{before.get('WRONG_VERIFIED', 0)} / {n}"),
                _hl("Correct and verified", f"{before.get('CORRECT_VERIFIED', 0)} / {n}"),
                _hl("False refusals", f"{before.get('FALSE_ABSTAIN', 0)} / {n}"),
                _hl("Mean time per question", f"{_fmt(lat.get('mean'), 1)} s"),
            ],
        }

    if isinstance(summary.get("python"), dict) and isinstance(summary.get("langchain"), dict):
        diff = summary.get("langchain_vs_python_mean")
        return {
            "kind": "latency",
            "about": (
                "Speed comparison: the same 10 questions asked twice to the plain-Python and the "
                "LangChain backend, alternating, reranking on."
            ),
            "highlights": [
                _hl("Python mean", f"{_fmt(summary['python'].get('mean_s'), 2)} s"),
                _hl("LangChain mean", f"{_fmt(summary['langchain'].get('mean_s'), 2)} s"),
                _hl("Difference", f"{diff * 100:+.1f}%" if isinstance(diff, (int, float)) else "—"),
            ],
        }

    if "surfaced_total" in results and "bad_total" in results:
        pipeline = config.get("pipeline", leaf)
        return {
            "kind": "safety",
            "about": (
                f"Safety replay on the {pipeline} pipeline: the cached answers and the corrupted "
                "claims from the verification ablation, passed through the full chain."
            ),
            "highlights": [
                _hl("Mean VCS", _fmt(results.get("mean_vcs"))),
                _hl("Answered / refused", f"{results.get('n_answer')} / {results.get('n_abstain')}"),
                _hl("Bad claims shown", f"{results['surfaced_total']} / {results['bad_total']}"),
            ],
        }

    if isinstance(results.get("results"), list) and isinstance(results.get("answers"), list):
        outcomes: dict[str, int] = {}
        for r in results["results"]:
            outcomes[r.get("outcome", "?")] = outcomes.get(r.get("outcome", "?"), 0) + 1
        return {
            "kind": "batch",
            "about": (
                "Early batch test on real ContractNLI agreements. This file holds the last of "
                "three runs; free-tier rate limits caused the backend errors (see report.md)."
            ),
            "highlights": [
                _hl("Verified", outcomes.get("verified", 0)),
                _hl("General knowledge", outcomes.get("general_knowledge", 0)),
                _hl("Backend errors", outcomes.get("backend_error", 0)),
            ],
        }

    if isinstance(results.get("totals"), dict) and isinstance(results.get("queries"), list):
        t = results["totals"]
        return {
            "kind": "corpus_check",
            "about": (
                "Early smoke test: index two real contracts and look at what dense, keyword and "
                "hybrid search return. No labelled answers, so there is nothing to score."
            ),
            "highlights": [
                _hl("Files indexed", t.get("indexed", "—")),
                _hl("Chunks", t.get("chunks", "—")),
                _hl("Queries tried", len(results["queries"])),
            ],
        }

    return {"kind": "other", "about": "", "highlights": []}
