"""FastAPI app for the Legal AI pipeline.

Run locally:
    uvicorn src.api.main:app --reload

The React UI (web/) talks to these endpoints only, never the pipeline modules
directly. CORS is opened for the local Vite dev server.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import (
    chats,
    documents,
    embedding_map,
    evaluation,
    ingest,
    query,
    retrieve,
    stats,
)
from src.config import load_env
from src.generation.factory import missing_key_message, selected_provider

# Pull LLM_PROVIDER / LLM_API_KEY / LLM_MODEL from the repo-root .env (if any)
# before any route resolves the LLM adapter.
load_env()

# Vite dev server default origins.
DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def allowed_origins() -> list[str]:
    """Dev origins, plus anything in LEGAL_AI_CORS_ORIGINS (comma-separated).

    scripts/batch_ask_check.py starts the UI on an ephemeral port, which would
    otherwise fail CORS preflight and make every /query look like a network
    error in the browser.
    """
    extra = os.environ.get("LEGAL_AI_CORS_ORIGINS", "")
    return DEV_ORIGINS + [o.strip() for o in extra.split(",") if o.strip()]


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
        allow_origins=allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def check_llm_config() -> None:
        """Say loudly, at startup, if the selected provider has no usable key.

        Otherwise a misnamed or absent key only shows up as a 503 on the first
        question somebody asks, which reads like a pipeline fault. .env is read
        once per process, so editing it needs a restart to take effect.
        """
        problem = missing_key_message()
        log = logging.getLogger("legal_ai.api")
        if problem:
            log.error("LLM backend is NOT configured: %s", problem)
            log.error("Ingest, retrieve and search will work; POST /query will return 503.")
        else:
            log.info("LLM backend: provider=%s, key found.", selected_provider())

    @app.get("/health")
    def health() -> dict:
        """Liveness plus whether the selected LLM provider is actually usable."""
        problem = missing_key_message()
        return {
            "status": "ok",
            "llm": {
                "provider": selected_provider(),
                "configured": problem is None,
                "problem": problem,
            },
        }

    app.include_router(ingest.router, tags=["ingest"])
    app.include_router(documents.router, tags=["documents"])
    app.include_router(retrieve.router, tags=["retrieve"])
    app.include_router(query.router, tags=["query"])
    app.include_router(evaluation.router, tags=["evaluation"])
    app.include_router(stats.router, tags=["stats"])
    app.include_router(chats.router, tags=["chats"])
    app.include_router(embedding_map.router, tags=["embedding-map"])
    return app


app = create_app()
