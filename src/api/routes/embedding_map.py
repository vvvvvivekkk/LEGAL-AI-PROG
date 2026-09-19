"""GET /embedding-map — 2D PCA projection of indexed chunk vectors.

Feeds the Evaluation page's embedding-space scatter: each indexed chunk becomes
an (x, y) point tagged with its source document so "embeddings" is something you
can see, not just a count.
"""

from __future__ import annotations

import json

import numpy as np
from fastapi import APIRouter, Depends

from src.api.deps import get_db_path
from src.api.projection import pca_2d
from src.api.schemas import EmbeddingMapResponse, EmbeddingPoint
from src.indexing.build import open_table, table_exists

router = APIRouter()


@router.get("/embedding-map", response_model=EmbeddingMapResponse)
def embedding_map(db_path: str = Depends(get_db_path)) -> EmbeddingMapResponse:
    if not table_exists(db_path):
        return EmbeddingMapResponse(method="pca", points=[], sources=[])
    df = open_table(db_path).to_pandas().reset_index(drop=True)
    if df.empty:
        return EmbeddingMapResponse(method="pca", points=[], sources=[])

    coords = pca_2d(np.vstack(df["vector"].to_numpy()))

    points: list[EmbeddingPoint] = []
    for i, record in enumerate(df.to_dict("records")):
        meta = json.loads(record["metadata"])
        points.append(
            EmbeddingPoint(
                x=float(coords[i, 0]),
                y=float(coords[i, 1]),
                chunk_id=record["chunk_id"],
                source_id=meta.get("source_id") or "",
                section_ref=meta.get("section_ref") or "",
            )
        )

    sources = sorted({p.source_id for p in points})
    return EmbeddingMapResponse(method="pca", points=points, sources=sources)
