---
name: verify-pipeline
description: Start the Legal AI backend + UI and run a real, end-to-end smoke check of ingestion, retrieval, and Ask (generation + verification) against real files — not just the pytest suite. Use when asked to check whether ingestion/retrieval/Ask actually works, to verify a fix before reporting it, or before a demo.
---

# Verify the Legal AI pipeline end-to-end

This project has been debugged multiple times by *assuming* something was broken from one Ask response, when the real fault was somewhere else in the pipeline. Don't repeat that — isolate the stage.

## 1. Start both servers (background, then poll for readiness — don't just launch and assume)

The default backend is the LangChain API (`lc/`) on port 8001, run from its own venv `.venv-lc`. Start it before the UI; `web/.env` already points the UI at `http://localhost:8001`.

```bash
.venv-lc/Scripts/python -m uvicorn lc.api:app --port 8001 &
(cd web && npm run dev) &
```
Poll `curl -sf http://localhost:8001/health` and `curl -sf http://localhost:5173` until both respond before doing anything else. All API calls below go to `:8001`.

## 2. Ingest at least one real file (not a synthetic fixture)

**`lc` has its own index, `data/lancedb_lc`, separate from the plain-Python `data/lancedb`.** Documents indexed for one backend are not visible to the other, so an empty `/stats` or an abstention right after switching usually means "nothing ingested into `data/lancedb_lc` yet", not a bug.

Use a real file from `data/corpus/` (gitignored, ask the user where theirs lives if it's not present in this checkout) via `POST /ingest` or the Ingest page. Confirm via `GET /stats` that chunk/document counts actually increased — don't trust the UI success banner alone.

## 3. Isolate retrieval from generation/verification

Before touching Ask, hit `GET /retrieve?q=...` directly with the exact question. This tells you what the retriever actually found, with no generation or verification in the way. If the relevant clause isn't in the top results here, the bug is in retrieval (chunking, embedding, reranker), not generation.

## 4. Only then test Ask (`POST /query`)

Send `"trace": true` in the request body to get the reranked candidates with scores, the exact prompt, the raw model output and per-claim verdicts. Compare what context reached generation against what step 3 showed. If Search found it but Ask didn't answer, the bug is in generation/verification (token budget, an over-strict verification threshold, a citation-matching bug), not retrieval.

## 5. Distinguish a real bug from correct behavior

An **abstained** answer is not automatically a bug — this system is specifically designed to refuse general/definitional questions ("what is an NDA") that the indexed documents don't define, and to refuse when a specific-seeming question genuinely isn't answered by any indexed clause. Only treat an abstention as a bug if you've confirmed (via step 3) that a relevant, specific clause *is* actually indexed and retrievable.

## 6. Report with evidence, not impressions

State exactly what you ran and what came back (the actual `/retrieve` results, the actual `/query` response, actual chunk counts) — see `docs/phases/phase-06-evaluation.md` and this repo's `CLAUDE.md` rule against fabricated/unverified numbers. A screenshot or a raw JSON response is evidence; "it works now" is not.

## Optional: check the plain-Python reference (`src/`) on port 8000

Use this to tell whether a problem is specific to the LangChain port. The reference API uses the main venv and its own index `data/lancedb`, so ingest the same file there too.

```bash
.venv/Scripts/python -m uvicorn src.api.main:app --port 8000 &
(cd web && VITE_API_BASE=http://localhost:8000 npm run dev) &
```
Poll `http://localhost:8000/health`, then repeat steps 2–4 against `:8000`. Stop the other UI first, or run this one with `-- --port 5174`; note that the reference API only allows CORS from the default dev origins, so a second port also needs `LEGAL_AI_CORS_ORIGINS=http://localhost:5174` on the API.
