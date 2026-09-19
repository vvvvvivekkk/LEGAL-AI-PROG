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
[7] Decision           VCS ≥ threshold → answer + proof. VCS < threshold → abstain / ask for clarification.
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

A Streamlit multi-page app (`src/ui/`), one page per pipeline concern rather than a single generic chat box:

1. **Ingestion** — upload/point at documents, watch them get cleaned, chunked (SAC), and indexed; inspect the resulting chunks + metadata.
2. **Retrieval** — a query box that shows, side by side: dense results, lexical (FTS) results, and the final hybrid-fused + reranked set — for debugging retrieval quality directly.
3. **Evaluation** — reads `/experiments` results and renders the ablation tables/metrics (retrieval quality, hallucination rate, VCS distribution) as they're produced; shows "no runs yet" until phase 6 lands.
4. **Proof viewer** (hallucination check) — run a query end-to-end and see the final answer alongside its full Proof Object: each claim, its supporting chunk, the verbatim quoted span, and the V1–V5 verdicts that produced its VCS.

Backed by a FastAPI service (`src/api/`) exposing ingestion, query, and evaluation-read endpoints — the UI is a thin client over it, so the same API can serve a different frontend later without touching the pipeline.

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
  api/                FastAPI app
  ui/                 Streamlit multi-page app (pages/ = Ingestion, Retrieval, Evaluation, Proof viewer)
data/                 small sample corpora only (gitignored: large corpora, model weights, lancedb data)
experiments/          per-run configs + results
tests/                mirrors src/
```

Module ownership mirrors the team's role split: Vivek — ingestion/chunking; Akshith — embedding/indexing/retrieval; Uday — generation/verification.
