"""DELETE /documents/{source_id} — drop one document from the index.

Removes every chunk for that source, which also removes its dedup fingerprint
(the hash lives on the chunk metadata), so the same file can be ingested again
cleanly. Used by the Ingest page's "Replace existing document" action.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_db_path
from src.api.index_stats import index_totals
from src.api.schemas import DeleteDocumentResponse
from src.indexing.build import delete_source

router = APIRouter()


@router.delete("/documents/{source_id}", response_model=DeleteDocumentResponse)
def delete_document(source_id: str, db_path: str = Depends(get_db_path)) -> DeleteDocumentResponse:
    try:
        deleted = delete_source(source_id, db_path=db_path)
    except Exception as exc:  # noqa: BLE001 - index write failures are the server's problem
        raise HTTPException(
            status_code=500, detail=f"could not update the index: {type(exc).__name__}: {exc}"
        ) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail=f"No indexed document with source_id {source_id!r}")

    return DeleteDocumentResponse(
        source_id=source_id,
        deleted_chunk_count=deleted,
        totals=index_totals(db_path),
    )
