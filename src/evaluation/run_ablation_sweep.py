"""Phase-6 retrieval/chunking ablation sweep: chunking x mode x reranker.

Full factorial over SAC vs fallback paragraph chunking, dense vs hybrid
retrieval, and reranker on/off (8 runs), on data/sample/. No LLM calls --
retrieval metrics only. Each index is built once and every config that uses it
reuses the same table, embedder and cross-encoder.

The query set labels relevance by SAC chunk id, so the fallback arm is scored
with the text-based matcher in retrieval_eval (same matcher applied to both
arms); SAC is additionally scored id-exact as a cross-check.

    python -m src.evaluation.run_ablation_sweep --out experiments/2026-09-23-ablations

Writes <out>/<config>/config.json + results.json per run.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import time
from dataclasses import asdict
from pathlib import Path

from src.chunking.fallback import fallback_chunks
from src.chunking.sac import chunk_corpus
from src.embedding.sentence_transformer import SentenceTransformerEmbedder
from src.evaluation.retrieval_eval import (
    evaluate_queryset,
    load_queryset,
    metrics_to_dict,
)
from src.indexing.build import build_index
from src.ingestion.pipeline import ingest_file_with_text
from src.retrieval.config import RetrievalConfig
from src.retrieval.rerank import CrossEncoderReranker
from src.retrieval.retriever import Retriever

_REPO_ROOT = Path(__file__).resolve().parents[2]
_QUERYSET = _REPO_ROOT / "data" / "eval" / "retrieval_queryset.json"
_SAMPLE = _REPO_ROOT / "data" / "sample"


def _corpus() -> list[tuple]:
    return [ingest_file_with_text(p) for p in sorted(_SAMPLE.glob("*.txt"))]


def _sac_chunks(corpus) -> list[dict]:
    return [c.to_dict() for c in chunk_corpus([doc for doc, _ in corpus])]


def _fallback_chunks(corpus) -> list[dict]:
    chunks: list[dict] = []
    for doc, cleaned in corpus:
        chunks.extend(c.to_dict() for c in fallback_chunks(cleaned, doc.source_id, doc.title))
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the phase-6 retrieval ablation sweep.")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--n", type=int, default=RetrievalConfig().n)
    parser.add_argument("--db-prefix", default="data/lancedb_ablate")
    parser.add_argument("--out", default=None, help="output dir (default experiments/<date>-ablations)")
    args = parser.parse_args()

    out_root = Path(args.out) if args.out else (
        _REPO_ROOT / "experiments" / f"{_dt.date.today().isoformat()}-ablations"
    )

    corpus = _corpus()
    embedder = SentenceTransformerEmbedder()
    reranker = CrossEncoderReranker(RetrievalConfig().reranker_model)
    queryset = load_queryset(_QUERYSET)

    sac_chunks = _sac_chunks(corpus)
    text_by_chunk_id = {c["chunk_id"]: c["text"] for c in sac_chunks}

    tables = {
        "sac": build_index(sac_chunks, db_path=f"{args.db_prefix}_sac", embedder=embedder),
        "fallback": build_index(
            _fallback_chunks(corpus), db_path=f"{args.db_prefix}_fallback", embedder=embedder
        ),
    }

    for chunking in ("sac", "fallback"):
        for mode in ("dense", "hybrid"):
            for rerank in (True, False):
                config = RetrievalConfig(mode=mode, use_reranker=rerank, k=args.k, n=args.n)
                retriever = Retriever(
                    tables[chunking],
                    config=config,
                    embedder=embedder,
                    reranker=reranker if rerank else None,
                )
                start = time.perf_counter()
                agg, per_query = evaluate_queryset(retriever, queryset, text_by_chunk_id)
                elapsed = time.perf_counter() - start

                payload = metrics_to_dict(agg, per_query)
                payload["match"] = "text"
                payload["mean_latency_s"] = elapsed / max(agg.n_queries, 1)
                if chunking == "sac":
                    id_agg, id_per_query = evaluate_queryset(retriever, queryset)
                    payload["id_exact_crosscheck"] = asdict(id_agg)

                name = f"{chunking}-{mode}-" + ("rerank" if rerank else "norerank")
                run_dir = out_root / name
                run_dir.mkdir(parents=True, exist_ok=True)
                cfg = asdict(config) | {"chunking": chunking, "corpus": "data/sample/*.txt"}
                (run_dir / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
                (run_dir / "results.json").write_text(
                    json.dumps(payload, indent=2), encoding="utf-8"
                )
                print(
                    f"{name}: P={agg.precision:.3f} R={agg.recall:.3f} F1={agg.f1:.3f} "
                    f"RR={agg.retrieval_rate:.3f} lat={payload['mean_latency_s']:.3f}s"
                )

    print(f"Sweep logged to {out_root}")


if __name__ == "__main__":
    main()
