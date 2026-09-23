"""Chunk index on the langchain_community LanceDB vector store.

Its own directory (data/lancedb_lc/) so it never touches src/'s index.

Deviations from the stock integration, each forced by a limitation of it
(lancedb 0.38, langchain-community 0.4):
  * add_texts embeds exactly the string it stores, but SAC embeds "summary +
    chunk text" while storing (and BM25-indexing) the chunk text alone. So
    add_chunks embeds the SAC input itself and writes rows in the
    integration's own layout (vector / id / text / metadata).
  * The integration stores metadata as an Arrow struct inferred from the first
    batch; a later document with different keys or null types then fails to
    insert. The chunk's own metadata dict is therefore kept as a JSON string
    inside a flat, all-string metadata struct.
  * mode is "append": the default "overwrite" replaces the table on every add.
Deletes go through the integration's own delete(ids=...).
"""

from __future__ import annotations

import json
from functools import cached_property

from langchain_community.vectorstores import LanceDB
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from lc.embeddings import as_embeddings, embedding_input

TABLE_NAME = "chunks"


def _row_metadata(doc: Document, content_sha256: str) -> dict:
    meta = dict(doc.metadata["chunk_metadata"])
    meta["content_sha256"] = content_sha256
    return {
        "chunk_id": doc.metadata["chunk_id"],
        "contextual_summary": doc.metadata["contextual_summary"],
        "source_id": meta.get("source_id") or "",
        "content_sha256": content_sha256,
        "chunk_metadata_json": json.dumps(meta, ensure_ascii=False),
    }


def stored_to_document(text: str, metadata: dict) -> Document:
    """A row read back from the table as the chunk Document the pipeline uses."""
    return Document(
        page_content=text,
        metadata={
            "chunk_id": metadata["chunk_id"],
            "contextual_summary": metadata["contextual_summary"],
            "chunk_metadata": json.loads(metadata["chunk_metadata_json"]),
        },
    )


class ChunkStore:
    def __init__(self, db_path: str, embedder):
        self.db_path = db_path
        self.embeddings: Embeddings = as_embeddings(embedder)

    @cached_property
    def lance(self) -> LanceDB:
        return LanceDB(
            uri=self.db_path,
            embedding=self.embeddings,
            table_name=TABLE_NAME,
            mode="append",
        )

    def table(self):
        return self.lance.get_table()

    def exists(self) -> bool:
        return self.table() is not None

    def embed_chunks(self, docs: list[Document], content_sha256: str) -> list[dict]:
        """Rows in the integration's layout, embedding the SAC input (summary + text)."""
        if not docs:
            return []
        vectors = self.embeddings.embed_documents(
            [embedding_input(d.metadata["contextual_summary"], d.page_content) for d in docs]
        )
        return [
            {
                "vector": vector,
                "id": doc.metadata["chunk_id"],
                "text": doc.page_content,
                "metadata": _row_metadata(doc, content_sha256),
            }
            for doc, vector in zip(docs, vectors)
        ]

    def write_rows(self, rows: list[dict]) -> None:
        table = self.table()
        if table is None:
            self.lance._connection.create_table(TABLE_NAME, data=rows)
        elif rows:
            table.add(rows)

    def add_chunks(self, docs: list[Document], content_sha256: str) -> None:
        self.write_rows(self.embed_chunks(docs, content_sha256))

    def version(self) -> int:
        table = self.table()
        return -1 if table is None else table.version

    def all_rows(self):
        """Every stored row as a pandas DataFrame (empty if no table)."""
        import pandas as pd

        table = self.table()
        return pd.DataFrame() if table is None else table.to_pandas()

    def all_documents(self) -> list[Document]:
        df = self.all_rows()
        if df.empty:
            return []
        return [stored_to_document(t, m) for t, m in zip(df["text"], df["metadata"])]

    def find_duplicate(self, source_id: str, digest: str) -> tuple[str, str, int] | None:
        """(reason, source_id, chunk_count) of an indexed match, as src/indexing/dedup."""
        df = self.all_rows()
        if df.empty:
            return None
        meta = df["metadata"]
        by_hash = [m for m in meta if m.get("content_sha256") == digest]
        if by_hash:
            return "content", by_hash[0].get("source_id") or source_id, len(by_hash)
        by_source = [m for m in meta if m.get("source_id") == source_id]
        if by_source:
            return "source_id", source_id, len(by_source)
        return None

    def delete_source(self, source_id: str) -> int:
        df = self.all_rows()
        if df.empty:
            return 0
        ids = [cid for cid, m in zip(df["id"], df["metadata"]) if m.get("source_id") == source_id]
        for start in range(0, len(ids), 500):
            self.lance.delete(ids=ids[start : start + 500])
        return len(ids)

    def totals(self) -> tuple[int, int]:
        df = self.all_rows()
        if df.empty:
            return 0, 0
        return len(df), len({m.get("source_id") for m in df["metadata"]})
