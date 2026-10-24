"""One-process deployment: the API under /api and the built web app at /.

For hosting on a single URL (Hugging Face Spaces: see deploy/huggingface/). The
API is mounted under /api so its routes never collide with the web app's page
URLs (/ingest, /evaluation, ...). Local development keeps using
`uvicorn lc.api:app` with the Vite dev server.

On start, if the index is empty, the criminal-law demo pack (data/demo_crime) is
loaded in the background through the API's own /ingest route, and the reranker
and NLI models are loaded once, so a fresh container can answer straight away.
Set LEGAL_AI_SEED=0 to skip this.

    uvicorn lc.hosted:app --host 0.0.0.0 --port 7860
"""

from __future__ import annotations

import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from lc.api import app as api_app

ROOT = Path(__file__).resolve().parent.parent
WEB_DIST = Path(os.environ.get("LEGAL_AI_WEB_DIST") or ROOT / "web" / "dist").resolve()
SEED_DIR = Path(os.environ.get("LEGAL_AI_SEED_DIR") or ROOT / "data" / "demo_crime")

log = logging.getLogger("legal_ai.hosted")
if not log.handlers:  # uvicorn configures only its own loggers; show these lines in the host's log
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s:     %(message)s"))
    log.addHandler(_handler)
    log.setLevel(logging.INFO)


def seed_index() -> None:
    """Ingest every .txt in SEED_DIR when the index is empty, then warm the models."""
    from fastapi.testclient import TestClient

    client = TestClient(api_app)
    try:
        if client.get("/stats").json().get("documents"):
            log.info("index already holds documents; not seeding")
        else:
            files = sorted(SEED_DIR.glob("*.txt"))
            for path in files:
                with path.open("rb") as fh:
                    r = client.post("/ingest", files={"file": (path.name, fh, "text/plain")})
                if r.status_code not in (200, 409):
                    log.warning("seeding %s failed: HTTP %s %s", path.name, r.status_code, r.text[:300])
            stats = client.get("/stats").json()
            log.info("seeded %s files: %s documents, %s chunks", len(files), stats.get("documents"), stats.get("chunks"))

        client.get("/retrieve", params={"q": "punishment for theft", "k": 5, "rerank": "true"})
        from src.verification.nli import RobertaMNLI

        RobertaMNLI().classify("Theft is punishable.", "Theft is punishable.")
        log.info("models loaded; ready")
    except Exception:  # noqa: BLE001
        log.exception("seeding or model warm-up failed; the app still serves requests")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.environ.get("LEGAL_AI_SEED", "1") != "0":
        threading.Thread(target=seed_index, name="seed-index", daemon=True).start()
    yield


app = FastAPI(title="Legal AI", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", api_app)

if WEB_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def web_app(path: str) -> FileResponse:
        """A file from the build if it exists (favicon, ...), else index.html, so the
        web app's own router handles /ask, /ingest and the other pages."""
        file = (WEB_DIST / path).resolve()
        if path and file.is_file() and WEB_DIST in file.parents:
            return FileResponse(file)
        return FileResponse(WEB_DIST / "index.html")
