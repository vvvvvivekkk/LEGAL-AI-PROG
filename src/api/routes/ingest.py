"""POST /ingest — upload a statute, run the real phase-1/2 pipeline, index it.

Wraps: ingestion (load/clean/parse) -> SAC chunking -> embedding -> LanceDB
append. Returns the newly-indexed chunks plus updated index totals. Does not
touch generation/verification.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.api.deps import get_db_path, get_embedder
from src.api.index_stats import index_totals
from src.api.schemas import IngestResponse
from src.api.serialization import new_chunk
from src.chunking.fallback import chunk_document_or_fallback
from src.indexing.build import append_chunks
from src.ingestion.pipeline import ingest_file_with_text

router = APIRouter()

_SUPPORTED = {".txt", ".pdf"}


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    file: UploadFile = File(...),
    db_path: str = Depends(get_db_path),
    embedder=Depends(get_embedder),
) -> IngestResponse:
    filename = file.filename or "upload"
    suffix = Path(filename).suffix.lower()
    if suffix not in _SUPPORTED:
        raise HTTPException(status_code=415, detail=f"Only {sorted(_SUPPORTED)} files are supported")

    contents = await file.read()
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / filename
        tmp_path.write_bytes(contents)
        try:
            document, cleaned = ingest_file_with_text(tmp_path)
        except NotImplementedError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - surface parse failures to the client
            raise HTTPException(status_code=400, detail=f"Could not parse file: {exc}") from exc

        chunk_records, used_fallback = chunk_document_or_fallback(document, cleaned)
        chunk_dicts = [c.to_dict() for c in chunk_records]

    if not chunk_dicts:
        # Even fallback found nothing — the file is effectively empty.
        raise HTTPException(
            status_code=422,
            detail="No chunks produced — the file appears to be empty.",
        )

    append_chunks(chunk_dicts, db_path=db_path, embedder=embedder)

    note = (
        "No legal structure detected — used fallback paragraph chunking."
        if used_fallback
        else None
    )

    return IngestResponse(
        source_id=document.source_id,
        filename=filename,
        new_chunk_count=len(chunk_dicts),
        new_chunks=[new_chunk(c) for c in chunk_dicts],
        totals=index_totals(db_path),
        used_fallback=used_fallback,
        note=note,
    )
