# Phase 0 — Scaffold

**Goal:** a clean, runnable repo skeleton before any pipeline logic exists.

**Tasks**
- `pyproject.toml` / `requirements.txt` with initial deps: `lancedb`, `sentence-transformers`, `rank_bm25` (fallback/comparison), `fastapi`, `uvicorn`, `streamlit`, `pytest`.
- Package skeleton under `src/` matching `docs/architecture.md` §7 (`ingestion/ chunking/ embedding/ indexing/ retrieval/ generation/ verification/ evaluation/ api/ ui/`), each with `__init__.py`.
- `.gitignore`: `.venv/`, `__pycache__/`, `data/lancedb/`, `data/raw/`, model weight caches, `experiments/*/artifacts/` (keep configs + result JSON, not large blobs).
- `data/sample/` — a handful (3–5) of small synthetic legal text snippets (fake statute/section text) to develop and test against without needing a real corpus yet.
- `tests/` mirroring `src/`, with a `conftest.py` pointing at `data/sample/`.

**Definition of done:** `pip install -e .` (or `-r requirements.txt`) succeeds, `pytest` runs (even with zero tests collected), sample data exists.
