# Phase 7 — FastAPI backend + React UI

**Goal:** wrap the finished pipeline in a usable local app. See `docs/architecture.md` §6 for the UI design. React replaces the earlier Streamlit prototype as the product UI — Streamlit can stay as an optional internal debug tool, but nothing here depends on it.

**Tasks**

- `src/api/` (FastAPI):
  - `POST /ingest` — upload a file, run ingestion → SAC chunking → embedding → append into LanceDB, return the new chunks + updated totals. (Ready now — wraps existing phase 1/2 code.)
  - `GET /retrieve?q=...` — run dense/FTS/hybrid (+ reranked, once phase 3 lands) search, return all variants side by side. (Ready now for dense/FTS/hybrid; add reranked once phase 3 lands.)
  - `POST /query` — full pipeline: retrieval → generation → verification, return the answer + Proof Object. (Needs phases 4-5.)
  - `GET /evaluation` — read `/experiments` results. (Useful once phase 6 has runs; returns "no runs yet" until then.)
  - CORS enabled for the local Vite dev server origin.
- `web/` (React + Vite): one view per endpoint above —
  1. **Ingestion** — drag-and-drop upload, shows returned chunks/metadata + running totals.
  2. **Retrieval** — query box, three-column dense/FTS/hybrid comparison.
  3. **Evaluation** — renders `/evaluation` results as tables/charts; "no runs yet" state.
  4. **Proof viewer** — query box, renders the answer plus its full Proof Object (claim → source → quote → verdict).
  - Views call the API only, never the pipeline directly.

**Build order:** ship `/ingest` + `/retrieve` and their two React views first — they work today, independent of phases 4/5. Add `/query` + the Proof viewer once phase 5 lands. Add `/evaluation` once phase 6 has runs.

**Definition of done:** `uvicorn src.api.main:app` + `npm run dev` (in `web/`) both run locally; the Ingestion and Retrieval views work end-to-end against real pipeline output now; Proof viewer and Evaluation views work once their phases land.
