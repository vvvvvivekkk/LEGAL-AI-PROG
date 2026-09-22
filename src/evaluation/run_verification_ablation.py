"""Runner: V1-V6 verification ablation sweep, logged to /experiments.

Two steps, because LLM calls are the scarce resource and verification is free:

    # 1. one real generation per eval query (+ V4 resamples for a subset)
    python -m src.evaluation.run_verification_ablation generate \
        --db data/lancedb_ablation --cache data/eval/ablation_cache.json \
        --resample-queries 5 --n-resamples 2

    # 2. replay the chain per ablation arm — no LLM calls
    python -m src.evaluation.run_verification_ablation ablate \
        --cache data/eval/ablation_cache.json

Step 2 writes experiments/<date>-ablations/config.json + results.json plus one
<arm>/config.json + <arm>/results.json per arm, so the phase-7 Evaluation page
picks each arm up as its own run. Per repo rules, only numbers from these
logged runs may be quoted anywhere.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
from pathlib import Path

from src.chunking.sac import chunk_corpus
from src.evaluation.verification_ablation import (
    ARMS,
    PERTURBATIONS,
    build_cache,
    load_cache,
    run_probe,
    run_sweep,
    save_cache,
)
from src.indexing.build import build_index
from src.ingestion.pipeline import ingest_directory
from src.retrieval.config import RetrievalConfig
from src.retrieval.retriever import Retriever

_REPO_ROOT = Path(__file__).resolve().parents[2]
_QUERYSET = _REPO_ROOT / "data" / "eval" / "retrieval_queryset.json"

# Matches the /query route: a deep candidate pool, reranked down to k.
QUERY_POOL_N = 100
DEFAULT_K = 5


def _load_queryset() -> list[dict]:
    return json.loads(_QUERYSET.read_text(encoding="utf-8"))["queries"]


def _build_retriever(db_path: str, k: int, rerank: bool) -> Retriever:
    chunks = [c.to_dict() for c in chunk_corpus(ingest_directory(_REPO_ROOT / "data" / "sample"))]
    table = build_index(chunks, db_path=db_path)
    config = RetrievalConfig(mode="hybrid", use_reranker=rerank, k=k, n=max(8 * k, QUERY_POOL_N))
    reranker = None
    if rerank:
        from src.retrieval.rerank import CrossEncoderReranker

        reranker = CrossEncoderReranker()
    return Retriever(table, config=config, reranker=reranker)


def _cmd_generate(args: argparse.Namespace) -> None:
    from src.generation.factory import get_adapter

    queries = [q["query"] for q in _load_queryset()]
    retriever = _build_retriever(args.db, args.k, args.rerank)
    adapter = get_adapter()
    cache = build_cache(
        queries,
        retriever,
        adapter,
        resample_queries=queries[: args.resample_queries],
        n_resamples=args.n_resamples,
        pause_s=args.pause,
    )
    save_cache(cache, args.cache)
    failed = [c.query for c in cache if not c.available]
    print(f"Cached {len(cache) - len(failed)}/{len(cache)} generations to {args.cache}")
    for q in failed:
        print(f"  UNAVAILABLE: {q}")


def _cmd_ablate(args: argparse.Namespace) -> None:
    from src.verification.nli import RobertaMNLI

    cache = load_cache(args.cache)
    gold = {q["query"]: q["relevant_chunk_ids"] for q in _load_queryset()}
    nli = RobertaMNLI()
    results = run_sweep(cache, nli, gold=gold)

    # Known-bad probes: the same arms over deterministically corrupted copies
    # of the cached answers, where every claim is bad by construction.
    probes = {mode: run_probe(cache, nli, mode) for mode in PERTURBATIONS}

    out_dir = _REPO_ROOT / "experiments" / (args.name or f"{_dt.date.today().isoformat()}-ablations")
    out_dir.mkdir(parents=True, exist_ok=True)
    for arm, res in results.items():
        arm_dir = out_dir / arm
        arm_dir.mkdir(exist_ok=True)
        (arm_dir / "config.json").write_text(
            json.dumps({"arm": arm, **res["config"]}, indent=2), encoding="utf-8"
        )
        payload = dict(res)
        payload["probes"] = {mode: probes[mode][arm] for mode in probes}
        (arm_dir / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    (out_dir / "config.json").write_text(
        json.dumps(
            {"sweep": "verification-v1-v6", "arms": list(ARMS), "probes": list(PERTURBATIONS)},
            indent=2,
        ),
        encoding="utf-8",
    )
    (out_dir / "results.json").write_text(
        json.dumps(
            {
                "arms": {
                    arm: {k: v for k, v in res.items() if k != "per_query"}
                    for arm, res in results.items()
                },
                "probes": probes,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Sweep logged to {out_dir}")
    for arm, res in results.items():
        mv = res["mean_vcs"]
        print(
            f"{arm:<12} mean_vcs={mv if mv is None else round(mv, 3)!s:<7} "
            f"ANSWER={res['n_answer']} ABSTAIN={res['n_abstain']} "
            f"bad={res['bad_claims_surfaced']} weak={res['weak_claims_surfaced']} "
            f"abst_acc={res['abstention_accuracy']}"
        )
    for mode, per_arm in probes.items():
        print(f"\nprobe: {mode}")
        for arm, res in per_arm.items():
            print(
                f"  {arm:<12} surfaced={res['bad_claims_surfaced']}/{res['bad_claims_total']} "
                f"catch_rate={res['catch_rate']}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="V1-V6 verification ablation sweep.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    gen = sub.add_parser("generate", help="run retrieval + one LLM generation per query")
    gen.add_argument("--db", default="data/lancedb_ablation")
    gen.add_argument("--cache", default="data/eval/ablation_cache.json")
    gen.add_argument("--k", type=int, default=DEFAULT_K)
    gen.add_argument("--rerank", dest="rerank", action="store_true", default=True)
    gen.add_argument("--no-rerank", dest="rerank", action="store_false")
    gen.add_argument("--resample-queries", type=int, default=0, help="how many queries get V4 resamples")
    gen.add_argument("--n-resamples", type=int, default=2)
    gen.add_argument("--pause", type=float, default=2.0, help="seconds between LLM calls")
    gen.set_defaults(func=_cmd_generate)

    abl = sub.add_parser("ablate", help="replay the chain per arm over the cache (no LLM calls)")
    abl.add_argument("--cache", default="data/eval/ablation_cache.json")
    abl.add_argument("--name", default=None, help="experiments/<name> directory")
    abl.set_defaults(func=_cmd_ablate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
