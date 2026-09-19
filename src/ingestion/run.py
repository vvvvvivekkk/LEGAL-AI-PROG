"""CLI entry point: ingest a directory of statute files and emit SAC chunks.

Usage:
    python -m src.ingestion.run --input data/sample --out data/processed
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.chunking.sac import chunk_corpus
from src.ingestion.pipeline import ingest_directory


def run(input_dir: str | Path, out_dir: str | Path) -> list[dict]:
    documents = ingest_directory(input_dir)
    chunks = [chunk.to_dict() for chunk in chunk_corpus(documents)]

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "chunks.json"
    out_path.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest + SAC-chunk a statute corpus.")
    parser.add_argument("--input", default="data/sample", help="Input directory of .txt statutes")
    parser.add_argument("--out", default="data/processed", help="Output directory for chunks.json")
    args = parser.parse_args()

    chunks = run(args.input, args.out)
    print(f"Wrote {len(chunks)} chunks from {args.input!r} to {Path(args.out) / 'chunks.json'}")


if __name__ == "__main__":
    main()
