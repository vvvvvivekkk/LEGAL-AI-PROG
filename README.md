# Legal AI: Hallucination-Resistant Legal RAG

A Retrieval-Augmented Generation system for legal Q&A where every answer is checked against its sources before it's shown, and ships with a structured, auditable proof of where each claim came from.

**New here / wondering what's actually novel about this?** Read [docs/architecture-production.md](docs/architecture-production.md) — a full production-RAG reference stack mapped against this project layer by layer, with evidence for each claim.

**Guides:** [System guide](docs/guide/README.md) ([PDF](docs/guide/Legal_AI_System_Guide.pdf)) covers every page, workflow and algorithm. The research paper is in [docs/paper/paper.pdf](docs/paper/paper.pdf).

## The problem

LLMs answering legal questions hallucinate: invented facts, misattributed case law, citations to provisions that don't actually say what's claimed. Plain RAG helps but doesn't fix this — fixed-size chunking destroys legal context, retrieval doesn't check that a source *supports* a claim, and prior work (chunking, retrieval, citation auditing) tends to improve one piece in isolation rather than the full pipeline.

## What this system does differently

1. **Summary-Augmented Chunking (SAC)** — chunks keep their place in the document hierarchy (act → chapter → section → clause) and are embedded together with a contextual summary of their parent section, so retrieval doesn't lose legal context.
2. **Hybrid retrieval on a local, file-based vector DB** — [LanceDB](https://lancedb.github.io/lancedb/) stores the index as on-disk Lance files (no server process, fully local), and natively combines dense vector search with full-text search + reciprocal rank fusion, which is exactly the hybrid semantic+keyword retrieval this problem needs. Followed by cross-encoder reranking.
3. **Citation-forced generation** — the LLM must attribute every claim to a specific chunk id; unattributed claims are treated as violations, not accepted.
4. **A 6-layer verification/proof chain (V1–V6)** — not one hallucination check, a pipeline of them: citation existence → NLI entailment → atomic claim fidelity scoring → self-consistency cross-check → a single calibrated **Verification Confidence Score (VCS)** with abstention → a structured **Proof Object** per answer (claim → source chunk → verbatim quote → verdict). See `docs/architecture.md` §4.
5. **A React UI ("Legal AI") built around the pipeline's actual stages**, not a generic chat box: routed Home, Ingest, Ask, Search, and Evaluation pages, with the per-claim verification proof folded into each Ask answer — talking to a FastAPI backend over HTTP. See `docs/architecture.md` §6.

This is designed to produce a real ablation study (SAC on/off, hybrid vs dense-only, each verification layer on/off) so results can go directly into a research paper — see `docs/architecture.md` §5.

## Architecture (short version — full detail in `docs/architecture.md`)

```
Ingestion → SAC Chunking → Embedding → LanceDB (hybrid: vector + FTS + RRF) → Rerank
    → Citation-forced Generation → Verification chain V1–V6 → VCS gate (answer | abstain)
    → FastAPI backend ⇄ React SPA "Legal AI" (Home / Ingest / Ask / Search / Evaluation)
```

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Chunking | custom SAC implementation |
| Embeddings | BGE-M3 / GTE-Large (pluggable; small local model for dev) |
| Vector DB | **LanceDB** — embedded, local, file-based, native hybrid search |
| Sparse/lexical | LanceDB full-text index (BM25-backed) |
| Reranker | cross-encoder (BGE-reranker) |
| Generation LLM | pluggable — Claude / GPT-4o / Gemini (Flash) adapters, selected by `LLM_PROVIDER` |
| NLI (verification) | roberta-large-mnli or legal-domain NLI model |
| Backend | FastAPI |
| UI | React (Vite + React Router) SPA "Legal AI" — Home / Ingest / Ask / Search / Evaluation; talks only to the FastAPI backend |
| Experiment tracking | plain JSON/YAML configs + results under `/experiments` |

## Repo layout

```
docs/                 architecture + one doc per development phase
src/
  ingestion/          document loaders, cleaning, metadata extraction
  chunking/           Summary-Augmented Chunking (SAC)
  embedding/          embedding model wrappers (pluggable)
  indexing/           LanceDB index build/query
  retrieval/          hybrid retrieval, fusion, reranking
  generation/         citation-forced prompting, pluggable LLM backend
  verification/       V1–V6 proof-chain modules, VCS scoring
  evaluation/         metrics + ablation runners
  api/                FastAPI app (the only thing the UI talks to)
  ui/                 legacy Streamlit debug app (optional, not the product UI)
web/                  React SPA — the product UI, calls src/api/ over HTTP
data/                 small sample corpora only (large corpora/model weights are gitignored)
experiments/          per-run configs + results
tests/                mirrors src/
```

## Development phases

Each phase has its own doc under `docs/phases/` with goals, tasks, and a definition of done:

| Phase | Doc | What it delivers |
|---|---|---|
| 0 | [phase-00-scaffold.md](docs/phases/phase-00-scaffold.md) | repo/env scaffold |
| 1 | [phase-01-ingestion-chunking.md](docs/phases/phase-01-ingestion-chunking.md) | ingestion + SAC chunking |
| 2 | [phase-02-embedding-vectordb.md](docs/phases/phase-02-embedding-vectordb.md) | embeddings + LanceDB hybrid index |
| 3 | [phase-03-hybrid-retrieval.md](docs/phases/phase-03-hybrid-retrieval.md) | fusion + reranking, retrieval-only eval |
| 4 | [phase-04-generation.md](docs/phases/phase-04-generation.md) | citation-forced answer generation |
| 5 | [phase-05-verification-proof.md](docs/phases/phase-05-verification-proof.md) | V1–V6 verification chain + VCS + proof objects |
| 6 | [phase-06-evaluation.md](docs/phases/phase-06-evaluation.md) | metrics + ablation runs |
| 7 | [phase-07-api-ui.md](docs/phases/phase-07-api-ui.md) | FastAPI backend + React UI |
| 8 | [phase-08-paper.md](docs/phases/phase-08-paper.md) | consolidating results into a paper |

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# build indexes from the sample corpus
python -m src.ingestion.run --input data/sample --out data/processed
python -m src.indexing.build --chunks data/processed --db data/lancedb

# LLM key for /query (ingest, retrieve and search work without one)
cp .env.example .env   # then set LLM_PROVIDER / LLM_API_KEY (and optionally LLM_MODEL)

# backend (default): the LangChain API on :8001, own index data/lancedb_lc (fill it via the Ingest page)
# one-time setup: python -m venv .venv-lc && .venv-lc\Scripts\pip install -r lc/requirements.txt
.venv-lc\Scripts\activate
uvicorn lc.api:app --port 8001

# backend, reference implementation: the plain-Python API on :8000
# (point the UI at it with VITE_API_BASE=http://localhost:8000 npm run dev)
uvicorn src.api.main:app --reload

# React UI (separate terminal); web/.env points it at :8001
cd web && npm install && npm run dev

# optional: legacy Streamlit debug app, doesn't need the backend running
streamlit run src/ui/app.py
```

(Exact entry points land as each phase is built — see the phase docs for current status.)

## Datasets & evaluation

Primary corpus: LegalBench-RAG + public legal documents (statutes, case law). Metrics: retrieval Precision/Recall/F1, Citation Precision/Recall, Faithfulness/Fidelity score, hallucination rate, abstention accuracy, latency. Ablations and full plan: `docs/architecture.md` §5.

## Related work

| Paper | Method | Limitation | Our improvement |
|---|---|---|---|
| Reuter et al., *Towards Reliable Retrieval in RAG Systems for Large Legal Datasets*, NLLP 2025 | Summary-Augmented Chunking | No claim/citation verification | Add full verification chain |
| Figueiredo et al., *Grounded in Law* (EscavAI), PROPOR 2026 | Citation audit | Limited case-law coverage, weak retrieval | Hybrid retrieval + broader audit |
| Maghakian et al., Embedding-Free RAG, EMNLP 2025 | LLM-driven retrieval | Expensive per-query LLM calls | Hybrid semantic+keyword retrieval |
| Niu et al., *RAGTruth*, arXiv 2024 | Hallucination benchmark | Not legal-domain | Legal-focused evaluation |
| Pipitone & Alami, *LegalBench-RAG*, arXiv 2024 | Legal benchmark dataset | Evaluation only, no end-to-end system | Full practical pipeline built and evaluated on it |
| Magesh et al., *Hallucination-Free? Assessing AI Legal Research Tools*, JELS 2025 | Evaluation of commercial legal AI | — | Informs our hallucination metrics |

## License

TBD.
