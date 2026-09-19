"""GET /stats — live index totals + per-source chunk counts (for the Home page)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends

from src.api.deps import get_db_path
from src.api.schemas import SourceStat, StatsResponse
from src.indexing.build import open_table, table_exists

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
def stats(db_path: str = Depends(get_db_path)) -> StatsResponse:
    if not table_exists(db_path):
        return StatsResponse(chunks=0, documents=0, sources=[])
    df = open_table(db_path).to_pandas()
    if df.empty:
        return StatsResponse(chunks=0, documents=0, sources=[])

    source_ids = df["metadata"].apply(lambda m: json.loads(m).get("source_id"))
    counts = source_ids.value_counts()
    sources = [SourceStat(source_id=str(sid), chunks=int(n)) for sid, n in counts.items()]
    return StatsResponse(chunks=len(df), documents=int(source_ids.nunique()), sources=sources)
