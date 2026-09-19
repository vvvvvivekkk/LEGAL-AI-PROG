"""Runner: build the sample index, evaluate retrieval, log a run to /experiments.

Not part of the automated test suite (it needs the embedding + reranker models,
which require network on first use). Run manually:

    python -m src.evaluation.run_retrieval_eval --mode hybrid --rerank
    python -m src.evaluation.run_retrieval_eval --mode dense --no-rerank --k 5 --n 20

Writes experiments/<date>-retrieval-<mode>[-rerank]/config.json + results.json.
Per repo rules, only numbers from these logged runs may be quoted anywhere.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
from dataclasses import asdict
from pathlib import Path

from src.chunking.sac import chunk_corpus
from src.evaluation.retrieval_eval import (
    evaluate_queryset,
    load_queryset,
    metrics_to_dict,
)
from src.indexing.build import build_index
from src.ingestion.pipeline import ingest_directory
from src.retrieval.config import RetrievalConfig
from src.retrieval.retriever import Retriever

_REPO_ROOT = Path(__file__).resolve().parents[2]
_QUERYSET = _REPO_ROOT / "data" / "eval" / "retrieval_queryset.json"


def _run_name(config: RetrievalConfig) -> str:
    today = _dt.date.today().isoformat()
    suffix = f"{config.mode}" + ("-rerank" if config.use_reranker else "-norerank")
    return f"{today}-retrieval-{suffix}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run retrieval-only evaluation and log it.")
    parser.add_argument("--mode", choices=["dense", "fts", "hybrid"], default="hybrid")
    parser.add_argument("--rerank", dest="rerank", action="store_true", default=True)
    parser.add_argument("--no-rerank", dest="rerank", action="store_false")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--db", default="data/lancedb_eval")
    args = parser.parse_args()

    config = RetrievalConfig(mode=args.mode, use_reranker=args.rerank, k=args.k, n=args.n)

    chunks = [c.to_dict() for c in chunk_corpus(ingest_directory(_REPO_ROOT / "data" / "sample"))]
    table = build_index(chunks, db_path=args.db)

    retriever = Retriever(table, config=config)
    queryset = load_queryset(_QUERYSET)
    agg, per_query = evaluate_queryset(retriever, queryset)

    out_dir = _REPO_ROOT / "experiments" / _run_name(config)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config.json").write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
    (out_dir / "results.json").write_text(
        json.dumps(metrics_to_dict(agg, per_query), indent=2), encoding="utf-8"
    )

    print(f"Run logged to {out_dir}")
    print(
        f"P={agg.precision:.3f} R={agg.recall:.3f} F1={agg.f1:.3f} "
        f"RR={agg.retrieval_rate:.3f} over {agg.n_queries} queries"
    )


if __name__ == "__main__":
    main()
