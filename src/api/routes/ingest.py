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
from src.indexing.build import append_rows, chunks_to_rows
from src.indexing.dedup import content_hash, find_duplicate
from src.ingestion.pipeline import ingest_file_with_text

router = APIRouter()

_SUPPORTED = {".txt", ".pdf"}


def _describe(exc: BaseException) -> str:
    """Short, human-readable reason for an exception (type name if no message)."""
    text = str(exc).strip()
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


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
    source_id = Path(filename).stem
    digest = content_hash(contents)

    # Refuse to index the same document twice: the chunk_ids would collide and
    # every retrieval would surface duplicate hits.
    duplicate = find_duplicate(source_id, digest, db_path=db_path)
    if duplicate is not None:
        why = (
            "identical content is already indexed"
            if duplicate.reason == "content"
            else "a document with the same name is already indexed"
        )
        raise HTTPException(
            status_code=409,
            detail=(
                f"Duplicate document: {why} as '{duplicate.source_id}' "
                f"({duplicate.chunk_count} chunks). Nothing was added."
            ),
        )

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
        for chunk in chunk_dicts:
            chunk["metadata"]["content_sha256"] = digest

    if not chunk_dicts:
        # Even fallback found nothing — the file is effectively empty.
        raise HTTPException(
            status_code=422,
            detail="No chunks produced — the file appears to be empty.",
        )

    # Embedding is the step most likely to fail at runtime (model not
    # downloaded, no network, out of memory). Report it as a clean 503 with the
    # real reason rather than letting the exception escape the route.
    try:
        rows = chunks_to_rows(chunk_dicts, embedder)
    except Exception as exc:  # noqa: BLE001 - any backend failure is "unavailable" to the client
        raise HTTPException(
            status_code=503,
            detail=f"embedding model unavailable: {_describe(exc)}",
        ) from exc

    try:
        append_rows(rows, db_path=db_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"could not write to the index: {_describe(exc)}",
        ) from exc

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
