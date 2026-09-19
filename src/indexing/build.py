"""Build/append a LanceDB table of SAC chunks with a hybrid (vector + FTS) index.

LanceDB is embedded and file-based: the whole index lives under a local
directory (default data/lancedb/), no server process. Both a full rebuild
and an incremental append are supported -- append lets one newly-ingested
document's chunks be added without re-embedding the rest of the corpus.
"""

from __future__ import annotations

import json
from pathlib import Path

import lancedb
import numpy as np

from src.embedding.base import EmbeddingModel
from src.embedding.sentence_transformer import SentenceTransformerEmbedder

DEFAULT_DB_PATH = "data/lancedb"
TABLE_NAME = "chunks"


def _embedding_input(chunk: dict) -> str:
    """Text actually embedded: contextual summary + chunk text.

    This is the point of SAC -- the embedding encodes both the local chunk
    text *and* the context of the section it lives in.
    """
    return f"{chunk['contextual_summary']}\n{chunk['text']}".strip()


def chunks_to_rows(chunks: list[dict], embedder: EmbeddingModel | None = None) -> list[dict]:
    """Embed chunk records and turn them into LanceDB row dicts."""
    embedder = embedder or SentenceTransformerEmbedder()
    if not chunks:
        return []
    inputs = [_embedding_input(chunk) for chunk in chunks]
    vectors = np.asarray(embedder.embed(inputs))

    rows = []
    for chunk, vector in zip(chunks, vectors):
        rows.append(
            {
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "contextual_summary": chunk["contextual_summary"],
                "metadata": json.dumps(chunk["metadata"], ensure_ascii=False),
                "vector": vector.tolist(),
            }
        )
    return rows


def connect(db_path: str | Path = DEFAULT_DB_PATH) -> lancedb.DBConnection:
    return lancedb.connect(str(db_path))


def build_index(
    chunks: list[dict],
    db_path: str | Path = DEFAULT_DB_PATH,
    table_name: str = TABLE_NAME,
    embedder: EmbeddingModel | None = None,
) -> lancedb.table.Table:
    """Full (re)build: embeds every chunk and overwrites the table."""
    db = connect(db_path)
    rows = chunks_to_rows(chunks, embedder)
    table = db.create_table(table_name, data=rows, mode="overwrite")
    table.create_fts_index("text", replace=True)
    return table


def append_chunks(
    chunks: list[dict],
    db_path: str | Path = DEFAULT_DB_PATH,
    table_name: str = TABLE_NAME,
    embedder: EmbeddingModel | None = None,
) -> lancedb.table.Table:
    """Incrementally add chunks (e.g. from one newly-ingested document).

    Only the new chunks are embedded -- the rest of the table is untouched.
    Falls back to build_index if the table doesn't exist yet. The FTS index
    is rebuilt afterwards so newly-added rows are searchable by keyword too.
    """
    db = connect(db_path)
    rows = chunks_to_rows(chunks, embedder)

    if table_name in db.table_names():
        table = db.open_table(table_name)
        if rows:
            table.add(rows)
        table.create_fts_index("text", replace=True)
        return table

    table = db.create_table(table_name, data=rows, mode="overwrite")
    table.create_fts_index("text", replace=True)
    return table


def open_table(
    db_path: str | Path = DEFAULT_DB_PATH, table_name: str = TABLE_NAME
) -> lancedb.table.Table:
    db = connect(db_path)
    return db.open_table(table_name)


def table_exists(db_path: str | Path = DEFAULT_DB_PATH, table_name: str = TABLE_NAME) -> bool:
    return table_name in connect(db_path).table_names()


def _main() -> None:
    import argparse
    import json as _json

    parser = argparse.ArgumentParser(description="Build a LanceDB hybrid index from chunk records.")
    parser.add_argument("--chunks", default="data/processed", help="Directory containing chunks.json")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="LanceDB directory to build")
    args = parser.parse_args()

    chunks_path = Path(args.chunks) / "chunks.json"
    chunks = _json.loads(chunks_path.read_text(encoding="utf-8"))
    table = build_index(chunks, db_path=args.db)
    print(f"Indexed {len(chunks)} chunks from {chunks_path} into {args.db!r} (table rows: {table.count_rows()})")


if __name__ == "__main__":
    _main()
