# Phase 7 — FastAPI backend + React UI ("Legal AI")

**Goal:** wrap the finished pipeline in a real product-feeling app, not a debug harness. See `docs/architecture.md` §6 for the full UI design (pages, the chat-integrated proof/audit layer, visual language). A first pass (tabs-in-one-page, plain styling) already exists — this phase's remaining work is turning it into the actual designed product below.

**Tasks**

- `src/api/` (FastAPI) — all four should exist now, phases 1-5 are done:
  - `POST /ingest` — ingestion → SAC chunking → embedding → LanceDB append, return new chunks + totals.
  - `GET /retrieve?q=...` — dense/FTS/hybrid + reranked results side by side.
  - `POST /query` — full pipeline: retrieval → generation → verification, return the answer with its Proof Object.
  - `GET /evaluation` — read `/experiments` results; "no runs yet" until phase 6 has any.
  - CORS enabled for the Vite dev origin.
- `web/` (React + Vite + React Router), branded **Legal AI**, real routed pages per `docs/architecture.md` §6:
  1. **Home (`/`)** — landing page, live index stats, entry points to Ask/Ingest. Animated/lightweight-3D hero.
  2. **Ingest (`/ingest`)** — drag-and-drop upload, resulting chunks + running totals.
  3. **Ask (`/ask`)** — chat UI. Each answer's claims render as inline citation chips; clicking one expands that claim's proof (source chunk, verbatim quote, V1–V5 verdicts, VCS) inline in the chat turn. No separate "Proof viewer" tab — this page *is* the verification/audit experience.
  4. **Search (`/search`)** — dense/FTS/hybrid comparison (was "Retrieval").
  5. **Evaluation (`/evaluation`)** — ablation tables/metrics + a 2D embedding-space scatter (PCA/UMAP projection of indexed chunks, colored by source document).
  - Motion (Framer Motion) on transitions and interactive states across every page — this is what separates it from the phases-1-2 debug prototype.
  - Views call the API only, never the pipeline directly.

**Build order:** the backend endpoints are unblocked now (phases 1-5 all landed) — build/finish all four first if any are missing. Then the pages, in this order: Ingest and Search first (they're mostly the existing views, just moved onto real routes + restyled), then Ask (new — this is the chat + inline-proof page and the most work), then Home, then Evaluation's embedding visualization last (needs a projection endpoint or client-side PCA over returned vectors).

**Definition of done:** `uvicorn src.api.main:app` + `npm run dev` (in `web/`) run locally; navigating between Home/Ingest/Ask/Search/Evaluation changes the URL (real routes); asking a question on `/ask` returns a real answer with expandable per-claim proof; Evaluation shows the embedding scatter once chunks are indexed.
