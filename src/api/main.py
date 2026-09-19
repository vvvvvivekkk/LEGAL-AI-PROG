"""FastAPI app for the Legal-RAG pipeline.

Run locally:
    uvicorn src.api.main:app --reload

The React UI (web/) talks to these endpoints only, never the pipeline modules
directly. CORS is opened for the local Vite dev server.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import ingest, retrieve

# Vite dev server default origins.
DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def create_app() -> FastAPI:
    app = FastAPI(title="Legal-RAG API", version="0.1.0")

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
    return app


app = create_app()
