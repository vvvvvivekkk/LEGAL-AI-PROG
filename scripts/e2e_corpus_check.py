"""End-to-end ingestion + retrieval check against the real downloaded corpus.

Runs the same code path POST /ingest uses (load -> clean -> parse -> SAC or
fallback chunking -> embed -> LanceDB append) over files under data/corpus/,
then runs real civil-law queries through the same dense / FTS / hybrid helpers
GET /retrieve uses and prints the top hit of each side by side with its source
document, so relevance can be eyeballed rather than inferred from a count.

    python scripts/e2e_corpus_check.py --limit 2                 # quick: 2 files
    python scripts/e2e_corpus_check.py --files a.pdf b.txt       # explicit files
    python scripts/e2e_corpus_check.py                           # everything

Writes a Markdown report + results.json under experiments/<date>-e2e-corpus-check/
(the only place numbers may be quoted from). Uses its own LanceDB directory by
default so the app's dev index is untouched.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.chunking.fallback import chunk_document_or_fallback  # noqa: E402
from src.indexing.build import append_rows, chunks_to_rows, open_table  # noqa: E402
from src.indexing.query import search_dense, search_fts, search_hybrid  # noqa: E402
from src.ingestion.pipeline import ingest_file_with_text  # noqa: E402

DEFAULT_CORPUS = REPO_ROOT / "data" / "corpus"
DEFAULT_DB = REPO_ROOT / "data" / "lancedb_corpus_check"
SUPPORTED = {".txt", ".pdf"}

QUERIES = [
    "limitation period for filing a suit to recover property",
    "remedies available for breach of contract",
    "when is specific performance granted instead of damages",
    "registration requirements for a sale deed",
    "termination of the agreement for material breach and cure period",
    "indemnification obligations of the licensee",
    "governing law and jurisdiction for disputes",
    "confidential information disclosure obligations",
    "conditions precedent to closing the merger",
    "assignment of the contract without prior written consent",
]

_STOPWORDS = {
    "a", "an", "the", "of", "for", "to", "in", "on", "and", "or", "is", "are", "when",
    "instead", "available", "without", "with", "prior", "into", "by", "at", "be",
}


def content_terms(query: str) -> set[str]:
    """Query words that carry meaning (crude stem: strip a trailing 's')."""
    return {w.rstrip("s") for w in re.findall(r"[a-z]+", query.lower()) if w not in _STOPWORDS and len(w) > 2}


def overlap(query: str, text: str) -> set[str]:
    words = {w.rstrip("s") for w in re.findall(r"[a-z]+", (text or "").lower())}
    return content_terms(query) & words


def discover_files(corpus: Path) -> list[Path]:
    return sorted(p for p in corpus.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED)


def ingest_one(path: Path, db_path: Path, embedder) -> dict:
    """Mirror of the /ingest route, minus HTTP. Never raises; returns a record."""
    rec = {"file": str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path),
           "source_id": path.stem, "bytes": path.stat().st_size}
    t0 = time.perf_counter()
    try:
        document, cleaned = ingest_file_with_text(path)
        records, used_fallback = chunk_document_or_fallback(document, cleaned)
        chunk_dicts = [c.to_dict() for c in records]
        if not chunk_dicts:
            rec.update(status="zero_chunks", chunks=0, chunking=None)
            return rec
        rows = chunks_to_rows(chunk_dicts, embedder)
        append_rows(rows, db_path=db_path)
        rec.update(status="ok", chunks=len(chunk_dicts),
                   chunking="fallback" if used_fallback else "structured",
                   sections=len({c["metadata"].get("section_ref") for c in chunk_dicts}))
    except Exception as exc:  # noqa: BLE001 - one bad file must not stop the batch
        rec.update(status="error", chunks=0, chunking=None, error=f"{type(exc).__name__}: {exc}")
    finally:
        rec["seconds"] = round(time.perf_counter() - t0, 2)
    return rec


def hit_summary(row: dict | None, query: str) -> dict | None:
    if row is None:
        return None
    md = row.get("metadata") or {}
    score = next((row[k] for k in ("_relevance_score", "_distance", "_score") if k in row and row[k] is not None), None)
    text = (row.get("text") or "").strip()
    return {
        "source_id": md.get("source_id"),
        "section_ref": md.get("section_ref"),
        "chunk_id": row.get("chunk_id"),
        "score": round(float(score), 4) if score is not None else None,
        "overlap": sorted(overlap(query, text)),
        "snippet": re.sub(r"\s+", " ", text)[:220],
    }


def run_queries(db_path: Path, embedder, queries: list[str], k: int) -> list[dict]:
    table = open_table(db_path)
    out = []
    for q in queries:
        variants = {
            "dense": search_dense(table, q, k=k, embedder=embedder),
            "fts": search_fts(table, q, k=k),
            "hybrid": search_hybrid(table, q, k=k, embedder=embedder),
        }
        top = {name: hit_summary(rows[0] if rows else None, q) for name, rows in variants.items()}
        hybrid_top = top["hybrid"]
        flags = []
        if not variants["hybrid"]:
            flags.append("hybrid returned nothing")
        elif not hybrid_top["overlap"]:
            flags.append("hybrid top hit shares no content term with the query")
        if not variants["fts"]:
            flags.append("fts returned nothing")
        out.append({"query": q, "top": top, "counts": {n: len(r) for n, r in variants.items()}, "flags": flags,
                    "all": {n: [hit_summary(r, q) for r in rows] for n, rows in variants.items()}})
    return out


def _cell(hit: dict | None) -> str:
    if hit is None:
        return "(no result)"
    where = hit["source_id"] or "?"
    if hit["section_ref"]:
        where += f" · {hit['section_ref']}"
    return f"{where}\n  score {hit['score']}  overlap {hit['overlap'] or '—'}\n  “{hit['snippet']}”"


def print_report(ingested: list[dict], queries: list[dict]) -> None:
    print("\n=== Ingestion ===")
    for r in ingested:
        line = f"{r['status']:<11} {r['chunks']:>5} chunks  {r['chunking'] or '-':<10} {r['seconds']:>6.1f}s  {r['file']}"
        if r.get("error"):
            line += f"\n             {r['error']}"
        print(line)
    ok = [r for r in ingested if r["status"] == "ok"]
    print(f"\n{len(ok)}/{len(ingested)} files indexed, {sum(r['chunks'] for r in ok)} chunks "
          f"({sum(1 for r in ok if r['chunking']=='structured')} structured, "
          f"{sum(1 for r in ok if r['chunking']=='fallback')} fallback)")
    bad = [r for r in ingested if r["status"] != "ok"]
    if bad:
        print("FLAGGED FILES:")
        for r in bad:
            print(f"  - {r['file']}: {r['status']} {r.get('error','')}")

    print("\n=== Retrieval (top-1 per variant) ===")
    for q in queries:
        print(f"\nQ: {q['query']}")
        for name in ("dense", "fts", "hybrid"):
            print(f"  [{name:<6}] " + _cell(q["top"][name]).replace("\n", "\n           "))
        if q["flags"]:
            print("  FLAGS: " + "; ".join(q["flags"]))


def write_report(out_dir: Path, args: argparse.Namespace, ingested: list[dict], queries: list[dict]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ok = [r for r in ingested if r["status"] == "ok"]
    results = {
        "config": {"corpus": str(args.corpus), "db": str(args.db), "files": len(ingested), "k": args.k,
                   "embedder": type(args._embedder).__name__, "model": getattr(args._embedder, "model_name", None)},
        "totals": {"files": len(ingested), "indexed": len(ok), "chunks": sum(r["chunks"] for r in ok),
                   "structured": sum(1 for r in ok if r["chunking"] == "structured"),
                   "fallback": sum(1 for r in ok if r["chunking"] == "fallback"),
                   "failed": [r for r in ingested if r["status"] != "ok"]},
        "ingestion": ingested,
        "queries": queries,
    }
    (out_dir / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")

    md = [f"# E2E corpus check — {date.today().isoformat()}", "",
          f"Corpus `{args.corpus}`, index `{args.db}`, embedder `{results['config']['model']}`, k={args.k}.", "",
          "## Ingestion", "", "| status | chunks | chunking | secs | file |", "|---|---|---|---|---|"]
    md += [f"| {r['status']} | {r['chunks']} | {r['chunking'] or '-'} | {r['seconds']} | `{r['file']}`"
           f"{' — ' + r['error'] if r.get('error') else ''} |" for r in ingested]
    t = results["totals"]
    md += ["", f"**{t['indexed']}/{t['files']} files indexed, {t['chunks']} chunks "
               f"({t['structured']} structured, {t['fallback']} fallback), {len(t['failed'])} failed.**", "",
           "## Retrieval — top-1 per variant", ""]
    for q in queries:
        md += [f"### {q['query']}", "", "| variant | source | score | overlap | snippet |", "|---|---|---|---|---|"]
        for name in ("dense", "fts", "hybrid"):
            h = q["top"][name]
            if h is None:
                md.append(f"| {name} | (no result) | | | |")
            else:
                where = (h["source_id"] or "?") + (f" · {h['section_ref']}" if h["section_ref"] else "")
                md.append(f"| {name} | {where} | {h['score']} | {', '.join(h['overlap']) or '—'} | {h['snippet']} |")
        if q["flags"]:
            md.append(f"\n**Flags:** {'; '.join(q['flags'])}")
        md.append("")
    flagged = [q["query"] for q in queries if q["flags"]]
    md += ["## Summary", "",
           f"- Documents indexed: {t['indexed']} ({t['chunks']} chunks)",
           f"- Ingestion failures: {len(t['failed'])}" + (" — " + ", ".join(f['file'] for f in t['failed']) if t['failed'] else ""),
           f"- Queries flagged (empty or no term overlap in hybrid top hit): {len(flagged)}"
           + (" — " + "; ".join(flagged) if flagged else ""),
           "", "Relevance flags are a keyword heuristic to direct attention; the tables above are the actual check."]
    path = out_dir / "report.md"
    path.write_text("\n".join(md), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS, help="directory to search for .txt/.pdf")
    ap.add_argument("--files", nargs="*", type=Path, help="explicit files to ingest (overrides --corpus discovery)")
    ap.add_argument("--limit", type=int, default=None, help="only the first N discovered files")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB, help="LanceDB directory (created fresh unless --keep)")
    ap.add_argument("--keep", action="store_true", help="append to an existing index instead of resetting it")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--queries", nargs="*", default=None, help="override the built-in civil-law queries")
    ap.add_argument("--out", type=Path, default=None, help="report directory (default experiments/<date>-e2e-corpus-check)")
    args = ap.parse_args(argv)

    files = [p.resolve() for p in args.files] if args.files else discover_files(args.corpus)
    if args.limit:
        files = files[: args.limit]
    if not files:
        print(f"No .txt/.pdf files found under {args.corpus}", file=sys.stderr)
        return 2

    if args.db.exists() and not args.keep:
        shutil.rmtree(args.db)

    from src.embedding.sentence_transformer import SentenceTransformerEmbedder

    embedder = SentenceTransformerEmbedder()
    args._embedder = embedder

    print(f"Ingesting {len(files)} file(s) into {args.db} with {embedder.model_name}")
    ingested = []
    for i, path in enumerate(files, 1):
        rec = ingest_one(path, args.db, embedder)
        ingested.append(rec)
        print(f"  [{i}/{len(files)}] {rec['status']:<11} {rec['chunks']:>5} chunks  {rec['chunking'] or '-':<10} {path.name}")

    queries = []
    if any(r["status"] == "ok" for r in ingested):
        queries = run_queries(args.db, embedder, args.queries or QUERIES, args.k)

    print_report(ingested, queries)
    out_dir = args.out or (REPO_ROOT / "experiments" / f"{date.today().isoformat()}-e2e-corpus-check")
    path = write_report(out_dir, args, ingested, queries)
    print(f"\nReport: {path}")
    return 1 if any(r["status"] != "ok" for r in ingested) else 0


if __name__ == "__main__":
    raise SystemExit(main())
