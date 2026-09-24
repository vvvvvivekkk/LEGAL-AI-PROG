"""Acceptance criterion 1: retrieval quality, LangChain vs plain Python.

Same corpus (data/sample/*.txt, SAC), same 10 labelled queries, same config
as experiments/2026-09-23-ablations/retrieval/sac-hybrid-rerank (hybrid,
rerank, k=5, n=50), same scorer (src.evaluation.retrieval_eval, text match
plus the id-exact cross-check). Both arms run in this process on the same
models, so the only difference is the pipeline.

    .venv-lc/Scripts/python -m lc.eval.retrieval_eval

Writes experiments/langchain_port/retrieval/{langchain,python}/results.json.
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import asdict
from pathlib import Path

from lc.embeddings import default_embeddings
from lc.loaders import load_document
from lc.retrieval import default_cross_encoder_compressor, query_retriever
from lc.splitters import SACTextSplitter, to_chunk_dict
from lc.vectorstore import ChunkStore
from lc.verification import doc_to_row
from src.chunking.sac import chunk_corpus
from src.evaluation.retrieval_eval import evaluate_queryset, load_queryset, metrics_to_dict
from src.indexing.build import build_index
from src.ingestion.pipeline import ingest_directory
from src.retrieval.config import RetrievalConfig
from src.retrieval.rerank import CrossEncoderReranker
from src.retrieval.retriever import Retriever

REPO = Path(__file__).resolve().parents[2]
SAMPLE = REPO / "data" / "sample"
QUERYSET = REPO / "data" / "eval" / "retrieval_queryset.json"
OUT = REPO / "experiments" / "langchain_port" / "retrieval"
K, N = 5, 50


class _Rows:
    """The .retrieve(query) -> rows interface evaluate_queryset expects."""

    def __init__(self, retriever):
        self.retriever = retriever

    def retrieve(self, query: str) -> list[dict]:
        return [doc_to_row(d) for d in self.retriever.invoke(query)]


def _langchain(db: Path):
    store = ChunkStore(str(db), default_embeddings())
    splitter = SACTextSplitter()
    for path in sorted(SAMPLE.glob("*.txt")):
        store.add_chunks(splitter.split_documents([load_document(path)]), content_sha256="eval")
    return _Rows(query_retriever(store, k=K, n=N, reranker=default_cross_encoder_compressor()))


def _python(db: Path):
    from src.embedding.sentence_transformer import SentenceTransformerEmbedder

    embedder = SentenceTransformerEmbedder()
    chunks = [c.to_dict() for c in chunk_corpus(ingest_directory(SAMPLE))]
    table = build_index(chunks, db_path=str(db), embedder=embedder)
    config = RetrievalConfig(mode="hybrid", use_reranker=True, k=K, n=N)
    return Retriever(table, config=config, embedder=embedder, reranker=CrossEncoderReranker())


def main() -> None:
    queryset = load_queryset(QUERYSET)
    text_by_id = {c.metadata["chunk_id"]: c.page_content for p in sorted(SAMPLE.glob("*.txt"))
                  for c in SACTextSplitter().split_documents([load_document(p)])}
    scratch = REPO / "data" / "lancedb_lc_eval"
    results = {}
    for name, build in (("langchain", _langchain), ("python", _python)):
        db = scratch / name
        shutil.rmtree(db, ignore_errors=True)
        retriever = build(db)
        retriever.retrieve(queryset[0]["query"])  # warm the models before timing
        start = time.perf_counter()
        agg, per_query = evaluate_queryset(retriever, queryset, text_by_id)
        elapsed = time.perf_counter() - start
        id_agg, _ = evaluate_queryset(retriever, queryset)
        payload = metrics_to_dict(agg, per_query)
        payload["match"] = "text"
        payload["id_exact_crosscheck"] = asdict(id_agg)
        payload["mean_latency_s"] = elapsed / max(agg.n_queries, 1)
        run_dir = OUT / name
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "config.json").write_text(
            json.dumps({"pipeline": name, "mode": "hybrid", "use_reranker": True, "k": K, "n": N,
                        "chunking": "sac", "corpus": "data/sample/*.txt"}, indent=2),
            encoding="utf-8",
        )
        (run_dir / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        results[name] = payload
        print(f"{name}: P={agg.precision:.4f} R={agg.recall:.4f} F1={agg.f1:.4f} "
              f"RR={agg.retrieval_rate:.2f} lat={payload['mean_latency_s']:.3f}s/query")

    lc_ids = [q["retrieved_ids"] for q in results["langchain"]["per_query"]]
    py_ids = [q["retrieved_ids"] for q in results["python"]["per_query"]]
    same_order = sum(a == b for a, b in zip(lc_ids, py_ids))
    same_set = sum(set(a) == set(b) for a, b in zip(lc_ids, py_ids))
    print(f"identical top-{K} (order): {same_order}/10, identical top-{K} (set): {same_set}/10")
    (OUT / "comparison.json").write_text(
        json.dumps({"identical_order": same_order, "identical_set": same_set,
                    "per_query": [{"query": q["query"], "langchain": a, "python": b}
                                  for q, a, b in zip(queryset, lc_ids, py_ids)]}, indent=2),
        encoding="utf-8",
    )
    shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    main()
