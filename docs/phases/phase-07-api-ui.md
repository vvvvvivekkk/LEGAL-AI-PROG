# Phase 7 — FastAPI backend + 4-page UI

**Goal:** wrap the finished pipeline in a usable local app. See `docs/architecture.md` §6 for the UI design.

**Tasks**
- `src/api/`: FastAPI endpoints — ingest documents, run a query end-to-end (retrieval→generation→verification), read evaluation results.
- `src/ui/` (Streamlit multi-page):
  1. **Ingestion** — upload/point at docs, watch SAC chunking + indexing happen, inspect chunks/metadata.
  2. **Retrieval** — query box showing dense/FTS/hybrid results side by side.
  3. **Evaluation** — renders `/experiments` ablation results as tables/charts.
  4. **Proof viewer** — run a query, see the answer plus its full Proof Object (claim → source → quote → verdict).
- UI calls the API, not the pipeline directly — keeps the API reusable for a different frontend later.

**Definition of done:** `uvicorn src.api.main:app` + `streamlit run src/ui/app.py` both run locally; a query typed in the Retrieval or Proof viewer page returns real pipeline output end-to-end.
