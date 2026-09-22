# Architecture

## 1. Pipeline

```
[1] Ingestion          raw legal docs (statutes, case law, contracts; PDF/HTML/TXT)
        ↓                cleaning, structure parsing, metadata (act/section/jurisdiction/date)
[2] SAC Chunking       Summary-Augmented Chunking — hierarchy-aware chunks + contextual summaries
        ↓
[3] Embedding + Index  LanceDB: dense vectors + full-text index, built from the same chunks
        ↓
[4] Hybrid Retrieval   LanceDB native hybrid search (vector + FTS, RRF-fused) → cross-encoder rerank
        ↓
[5] Generation         citation-forced prompting; LLM must attribute every claim to a chunk id
        ↓
[6] Verification       6-stage Proof Chain V1–V6 (§4) → Verification Confidence Score (VCS) + Proof Object
        ↓
[7] Decision           VCS ≥ threshold → answer + proof. VCS < threshold → abstain / ask for clarification,
                       except general concept questions, which fall back to uncited general knowledge (§7).
        ↓
[8] Serving            FastAPI backend + 4-page UI (§6), returns answer + inline proof trace
```

An **evaluation harness** (§5) runs against every stage so SAC, hybrid retrieval, and each verification layer can be ablated independently.

## 2. Why LanceDB (the vector DB choice)

Requirement: a *better*, local, file-based vector store — no server process, easy to hand off/run on anyone's machine.

- **Embedded & file-based**: LanceDB is a library, not a service — the whole index is a directory of Lance files on disk. `pip install lancedb`, point it at a path, done. No Docker, no separate DB process to keep alive.
- **Native hybrid search**: LanceDB supports vector search and full-text search (BM25-backed) over the same table, with built-in reciprocal rank fusion (RRF) reranking between them — this *is* the hybrid semantic+keyword retrieval the project needs, not something we have to hand-roll on top of a plain vector index.
- **Versioning**: table versions are retained, so an index can be rebuilt/compared across experiments without extra bookkeeping.
- Compare to plain FAISS (no metadata/filtering, no built-in lexical search, needs BM25 hand-wired separately) or Chroma (server-oriented, heavier). FAISS stays available only as an ablation baseline in `evaluation/` if we want to show hybrid > dense-only on our own index type.

## 3. Summary-Augmented Chunking (SAC)

- Parse documents into their natural legal hierarchy (act → chapter → section → clause), not fixed-size windows.
- For each chunk, generate a short contextual summary of its parent section (extractive first, LLM-abstractive as a later option) and prepend/attach it to the chunk before embedding — the embedding then encodes both the local text and the context it lives in.
- Store structured metadata per chunk: source doc id, act/section reference, jurisdiction, date — needed later for citation verification (V1/V2) and for the UI's proof view.

## 4. Verification / Proof chain (V1–V6)

Each stage can reject or downgrade an answer before it reaches the user. Layers run in order because later ones consume earlier ones' outputs.

| # | Layer | What it checks | Kind |
|---|---|---|---|
| V1 | Citation Existence | Every cited chunk id actually exists in the retrieved context (catches fabricated citations) | deterministic, cheap |
| V2 | Entailment/Support (NLI) | For each (claim, cited chunk): ENTAILS / CONTRADICTS / NEUTRAL — only ENTAILS passes | NLI model or LLM-judge |
| V3 | Atomic Claim Fidelity | Decompose answer into atomic claims (FActScore/RAGTruth-style), verify each independently against its evidence | per-claim score |
| V4 | Self-Consistency | Resample generation N times / vary retrieval slightly; claims that don't recur are flagged unstable | SelfCheckGPT-style |
| V5 | Calibrated Confidence & Abstention | Aggregate V1–V4 into one **Verification Confidence Score (VCS)**, calibrated on held-out data; below threshold → abstain/ask for clarification instead of guessing | our novel metric |
| V6 | Proof Object | Structured trace per answer: `claim → supporting chunk id(s) → verbatim quoted span → verdict → VCS contribution` | output artifact |

The VCS + Proof Object pair is the paper-worthy contribution: one interpretable, calibrated score plus a fully auditable evidence chain, produced by a chain of layers rather than a single hallucination classifier.

## 5. Evaluation & ablations (feeds the paper)

- **Corpus:** LegalBench-RAG + curated public legal documents.
- **Metrics:** retrieval Precision/Recall/F1, Retrieval Rate (RR%), Document Retrieval Match (DRM), Citation Precision/Recall, Faithfulness/Fidelity score (from V3), hallucination rate, abstention accuracy, latency.
- **Ablations:** fixed chunking vs. SAC · dense-only vs. hybrid · with/without reranking · with/without each of V1–V6 individually · embedding choice (BGE-M3 vs GTE-Large) · generation LLM choice.
- Every run: a config + a results JSON under `/experiments/<date>-<name>/`. No number gets quoted anywhere unless it came from a logged run.

## 6. UI architecture

A React SPA (`web/`), branded **Legal AI**, talking to a FastAPI service (`src/api/`) — the API is the only thing that touches the pipeline; the UI is a pure client over HTTP, so the frontend can be replaced or restyled without ever touching pipeline code. Real routed pages (React Router), not tabs on one screen:

1. **Home (`/`)** — landing page: what the product does, live index stats (documents/chunks indexed), entry points into Ask and Ingest. This is the front door, not a tab.
2. **Ingest (`/ingest`)** — drag-and-drop a document, watch it get cleaned, chunked (SAC), and indexed; inspect the resulting chunks + metadata. Calls `POST /ingest`.
3. **Ask (`/ask`)** — a chat interface, not a query-and-results form: the user asks a question, the answer streams in with inline citation markers per claim. Clicking a citation expands that claim's proof inline (supporting chunk, verbatim quote, V1–V5 verdicts, VCS) — the verification/audit layer lives *inside* the chat turn, not as a separate disconnected tool. Calls `POST /query`.
4. **Search (`/search`)** — the retrieval debugging view: dense/FTS/hybrid results side by side. Calls `GET /retrieve`.
5. **Evaluation (`/evaluation`)** — ablation tables/metrics from `GET /evaluation`, plus a 2D embedding-space visualization (chunks projected via PCA/UMAP, colored by source document) so "embeddings" is something you can actually see, not just a number. Shows "no runs yet" until phase 6 lands.

There is no standalone "Proof viewer" page — the proof/verification-audit experience is folded into Ask (#3), where it's actually useful, rather than being a disconnected tab.

Visual language: a real design system (not utility-class defaults) — deliberate color/typography tokens, motion (page transitions, staggered reveals, hover/press states — Framer Motion) on every page, and a lightweight animated/3D hero on Home. This is what makes it read as a product, not a debug harness.

An early Streamlit multi-page app served ingestion/retrieval debugging during phases 1-2 development and can stay around as an internal-only tool, but it is not and never was the product UI. Nothing in `src/` (ingestion, chunking, embedding, indexing, retrieval, generation, verification, evaluation) depends on either frontend; both just call the FastAPI service.

## 7. Repo layout

```
docs/                 this file + docs/phases/*.md
src/
  ingestion/          loaders, cleaning, metadata extraction
  chunking/           Summary-Augmented Chunking (SAC)
  embedding/          embedding model wrappers (pluggable)
  indexing/           LanceDB index build/query (hybrid)
  retrieval/          fusion + reranking on top of LanceDB hybrid search
  generation/         citation-forced prompting, pluggable LLM backend
  verification/       V1–V6 modules, VCS scoring, proof object builder
  evaluation/         metrics + ablation runners
  api/                FastAPI app (the only thing the UI talks to)
  ui/                 legacy Streamlit debug app (optional, not the product UI)
web/                  React SPA — Ingestion / Retrieval / Evaluation / Proof viewer views, calls src/api/ over HTTP
data/                 small sample corpora only (gitignored: large corpora, model weights, lancedb data)
experiments/          per-run configs + results
tests/                mirrors src/
```


## 7. Answer modes

`POST /query` returns an `answer_mode` telling the caller how the answer was
produced. The three modes are kept strictly separate — a general-knowledge
answer is never presented as a sourced one.

| mode | meaning | VCS | citations |
|---|---|---|---|
| `verified` | VCS ≥ threshold; every claim passed the chain | a score | yes |
| `abstained` | the documents could not support an answer | a score or none | none |
| `general_knowledge` | the question was a general legal concept the corpus was never going to answer, so the model answered from its own knowledge | always `null` | none |

The fallback is deliberately narrow, in `src/generation/general_knowledge.py`.
A query qualifies only if it opens like a definition request ("what is…",
"define…", "explain…") *and* carries no marker tying it to the indexed
documents ("this agreement", "section 4", "according to…", "what happens
if…"). Anything ambiguous stays on the verified path, where abstaining is the
honest answer — a question that the documents *should* answer must never be
quietly satisfied from model priors. Callers can disable it entirely with
`allow_general_knowledge: false`.

The UI badges the three modes distinctly; `general_knowledge` gets its own
colour off the verified/abstained axis and renders as plain prose with no
citation affordances.

### Batch check

`scripts/batch_ask_check.py` drives the real UI with Playwright: it ingests ten
ContractNLI agreements through the Ingest page, asks five document-specific and
five general questions through the Ask page, and records outcome / VCS /
whether citations point at the document that actually contains the answer. It
runs against an isolated index (`LEGAL_AI_DB_PATH`) and writes results plus
screenshots under `experiments/batch_ask_check/`.
