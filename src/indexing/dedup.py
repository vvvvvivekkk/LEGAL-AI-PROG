"""Duplicate-document detection for the index.

Two documents are considered the same if either their raw bytes hash to the
same SHA-256 (same file re-uploaded, possibly under a new name) or they share a
source_id (same filename stem, so their chunk_ids would collide). The hash is
stored on every chunk's metadata as ``content_sha256`` at ingest time.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from src.indexing.build import DEFAULT_DB_PATH, TABLE_NAME, open_table, table_exists


@dataclass(frozen=True)
class DuplicateMatch:
    reason: str  # "content" | "source_id"
    source_id: str
    chunk_count: int


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_duplicate(
    source_id: str,
    digest: str,
    db_path: str | Path = DEFAULT_DB_PATH,
    table_name: str = TABLE_NAME,
) -> DuplicateMatch | None:
    """Return the indexed document that matches by content hash or source_id, if any."""
    if not table_exists(db_path, table_name):
        return None
    df = open_table(db_path, table_name).to_pandas()
    if df.empty:
        return None
    meta = df["metadata"].apply(json.loads)

    by_hash = meta[meta.apply(lambda m: m.get("content_sha256") == digest)]
    if len(by_hash):
        return DuplicateMatch("content", by_hash.iloc[0].get("source_id", source_id), len(by_hash))

    by_source = meta[meta.apply(lambda m: m.get("source_id") == source_id)]
    if len(by_source):
        return DuplicateMatch("source_id", source_id, len(by_source))
    return None
