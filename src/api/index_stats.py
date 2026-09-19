"""Compute index totals (chunk count, distinct document count) from LanceDB."""

from __future__ import annotations

import json

from src.api.schemas import IndexTotals
from src.indexing.build import open_table, table_exists


def index_totals(db_path: str) -> IndexTotals:
    if not table_exists(db_path):
        return IndexTotals(chunks=0, documents=0)
    df = open_table(db_path).to_pandas()
    if df.empty:
        return IndexTotals(chunks=0, documents=0)
    source_ids = df["metadata"].apply(lambda m: json.loads(m).get("source_id"))
    return IndexTotals(chunks=len(df), documents=int(source_ids.nunique()))
