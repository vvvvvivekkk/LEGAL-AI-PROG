"""FastAPI app for the Legal AI pipeline.

Run locally:
    uvicorn src.api.main:app --reload

The React UI (web/) talks to these endpoints only, never the pipeline modules
directly. CORS is opened for the local Vite dev server.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import embedding_map, evaluation, ingest, query, retrieve, stats

# Vite dev server default origins.
DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def create_app() -> FastAPI:
    app = FastAPI(title="Legal AI API", version="0.1.0")

    # Catch-all for exceptions a route didn't handle itself. Registered before
    # CORS so it sits *inside* it: the JSON 500 then still carries CORS headers.
    # Starlette's own error middleware is outermost, so without this the
    # browser would see a header-less 500 and report a bare "Failed to fetch".
    @app.middleware("http")
    async def unhandled_error_to_json(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:  # noqa: BLE001
            logging.getLogger("legal_ai.api").exception("unhandled error in %s", request.url.path)
            return JSONResponse(
                status_code=500,
                content={"detail": f"internal error: {type(exc).__name__}: {exc}"},
            )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(ingest.router, tags=["ingest"])
    app.include_router(retrieve.router, tags=["retrieve"])
    app.include_router(query.router, tags=["query"])
    app.include_router(evaluation.router, tags=["evaluation"])
    app.include_router(stats.router, tags=["stats"])
    app.include_router(embedding_map.router, tags=["embedding-map"])
    return app


app = create_app()
