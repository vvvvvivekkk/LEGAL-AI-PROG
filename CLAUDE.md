# Legal-RAG: Hallucination-Reduced Legal AI via Retrieval-Augmented Generation

> Mini Project (Review 1) — Dept. of AI, Anurag University, AY 2026–27
> Team: A. Vivek Reddy (23EG106C04) · N. Akshith Sai (23G106C03) · K. Uday (23EG106C30)
> Guide: Ms. S. Hemasri

This file is the persistent context for Claude Code on this repo. Read it fully before writing code. It defines what we're building, why, the exact pipeline, the verification/proof system that is our core contribution, the build order, and how to work in this repo without wasting tokens.

---

## 1. Problem & Goal

LLMs used for legal Q&A, contract analysis, and legal research **hallucinate**: they invent facts, misattribute case law, or cite provisions that don't say what the model claims. Plain RAG (retrieve-then-generate) reduces this but doesn't eliminate it, because:

- Fixed-size chunking destroys legal context (a clause read in isolation loses the section/act it belongs to).
- Retrieval alone doesn't check that a cited source actually **supports** the generated claim.
- Existing systems improve retrieval, chunking, or citation auditing **separately** — never as one integrated, verifiable pipeline.

**Goal:** build a Legal RAG system that produces answers which are not just retrieved-and-generated, but **verified and provable** — every claim in the final answer is traceable to a specific passage, and that passage is checked to actually entail the claim before the answer is shown.

This is a real, working system (not a slide deck exercise), built incrementally, instrumented well enough that results can be written up as a research paper.

---

## 2. Architecture (pipeline, in build order)

```
[1] Ingestion          raw legal docs (statutes, case law, contracts, PDFs/HTML)
        ↓                → cleaning, structure parsing, metadata (act/section/jurisdiction/date)
[2] SAC Chunking       Summary-Augmented Chunking — hierarchy-aware chunks + contextual summaries
        ↓
[3] Embedding + Index  dense (FAISS) + sparse (BM25) indexes, dual-built from the same chunks
        ↓
[4] Hybrid Retrieval   dense + sparse fusion (RRF) → cross-encoder rerank → top-k context
        ↓
[5] Generation         citation-forced prompting; LLM must attribute every claim to a chunk id
        ↓
[6] Verification       6-stage Proof Chain (V1–V6) — see §3. Produces a Verification
        ↓              Confidence Score (VCS) and a structured Proof Object per answer.
[7] Decision           VCS ≥ threshold → return answer + proof. VCS < threshold → abstain /
        ↓              ask for clarification instead of guessing.
[8] Serving            FastAPI backend + minimal web UI, returns answer + inline proof trace
```

Cross-cutting: an **evaluation harness** (§5) runs against every stage so we can ablate (SAC on/off, hybrid vs dense-only, verification on/off) and produce the tables a paper needs.

### Why this differs from typical/off-the-shelf RAG and from the papers we reviewed
| Prior work | What it does | What it lacks |
|---|---|---|
| Reuter et al. (SAC, 2025) | Summary-augmented chunking | No verification of citations/claims |
| EscavAI (Figueiredo et al., 2026) | Citation audit | Weak retrieval, limited case-law coverage |
| Embedding-Free RAG (Maghakian et al., 2025) | LLM-driven retrieval | Expensive per-query LLM calls |
| RAGTruth (Niu et al., 2024) | Hallucination benchmark | Not legal-domain |
| LegalBench-RAG (Pipitone & Alami, 2024) | Legal benchmark | Evaluation only, no end-to-end system |

**Our contribution:** SAC + hybrid retrieval + a *multi-layer, scored, auditable* verification stage, combined into one pipeline, with a single interpretable output (VCS + Proof Object) — no reviewed system does context preservation, hybrid retrieval, and graded citation verification together with a calibrated abstention mechanism.

---

## 3. The Verification / Proof layer (core contribution — this is what "reduces hallucination")

This is not one hallucination check, it's a **chain of six independent, increasingly strict layers**. Each stage can reject or downgrade the answer before the user ever sees it. This directly maps to the user's requirement: *verification layers that reduce hallucination AND produce proofs*.

1. **V1 — Citation Existence Check** (deterministic, cheap)
   Does every citation the LLM emitted actually correspond to a chunk id that was in the retrieved context? Fabricated citation ids are rejected immediately.

2. **V2 — Entailment / Support Verification (NLI)**
   For each (claim, cited-chunk) pair, run an NLI model (or LLM-as-judge fallback) to classify ENTAILS / CONTRADICTS / NEUTRAL. Only ENTAILS passes.

3. **V3 — Atomic Claim Decomposition + Fidelity Scoring**
   Decompose the answer into atomic factual claims (FActScore/RAGTruth-style). Verify each claim independently against its cited evidence. Produces a per-claim fidelity score, not just a pass/fail for the whole answer.

4. **V4 — Self-Consistency Cross-Check**
   Sample the generation step N times (and/or vary retrieval slightly). Claims that don't recur across samples are flagged as unstable / hallucination-prone (SelfCheckGPT-style uncertainty estimation).

5. **V5 — Calibrated Confidence & Abstention**
   Aggregate V1–V4 into a single **Verification Confidence Score (VCS)** — this is our own metric, calibrated on held-out data. Below threshold → the system abstains or asks a clarifying question instead of answering. This is the novel, paper-worthy metric.

6. **V6 — Proof Object Generation**
   For the final answer, emit a structured, auditable trace:
   `claim → supporting chunk id(s) → verbatim quoted span → verdict (V1–V4 results) → VCS contribution`.
   This *is* the "proof" — every answer ships with its own evidence chain, renderable in the UI and citable in the paper's qualitative examples.

---

## 4. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | |
| Orchestration | LangChain | matches team's plan; keep usage thin/wrappable so it's swappable |
| Embeddings | BGE-M3 (primary), GTE-Large (comparison) | select after experimentation, log both |
| Dense index | FAISS | |
| Sparse index | BM25 (`rank_bm25`, or Elasticsearch/OpenSearch if corpus grows) | |
| Reranker | cross-encoder (e.g. BGE-reranker) | |
| Generation LLM | pluggable: Claude / GPT-4o / Llama 3.1 / Gemini 1.5 | keep behind one interface, swap for experiments |
| NLI (V2) | roberta-large-mnli or a legal-domain NLI model | |
| Backend | FastAPI | |
| Demo UI | Streamlit (simple) | |
| Experiment tracking | plain JSON/YAML configs + results in `/experiments`, no heavyweight MLOps tooling needed for a mini-project |

---

## 5. Datasets & evaluation (for the paper)

- **Primary corpus:** LegalBench-RAG + public legal datasets/curated documents (statutes, case law).
- **Metrics:** retrieval Precision/Recall/F1, Retrieval Rate (RR%), Document Retrieval Match (DRM), **Citation Precision/Recall**, **Faithfulness/Fidelity score** (from V3), **hallucination rate**, abstention accuracy, latency.
- **Ablations to run (this is the paper's results section):**
  1. Fixed chunking vs. SAC
  2. Dense-only vs. Hybrid (dense+BM25) retrieval
  3. With vs. without reranking
  4. With vs. without each verification layer (V1–V6), isolating each one's contribution to hallucination reduction
  5. Embedding choice: BGE-M3 vs GTE-Large
  6. Generation LLM choice: comparison across candidates
- Every experiment run gets a config file + a results JSON in `/experiments/<date>-<name>/`. Never hand-report numbers that weren't produced by a logged run — this is what makes the later paper defensible.

---

## 6. Repo layout

```
/data/                raw + processed legal corpora (small samples only; large corpora stay out of git)
/src/
  ingestion/          loaders, cleaners, metadata extraction         (owner: Vivek)
  chunking/           Summary-Augmented Chunking (SAC)                (owner: Vivek)
  embedding/          embedding model wrappers                       (owner: Akshith)
  indexing/           FAISS + BM25 index builders                    (owner: Akshith)
  retrieval/          hybrid retrieval, RRF fusion, reranking         (owner: Akshith)
  generation/         prompt templates, citation-forced generation   (owner: Uday)
  verification/       V1–V6 proof-chain modules, VCS scoring         (owner: Uday)
  evaluation/         metrics, benchmark + ablation runners
  api/                FastAPI backend
  ui/                 Streamlit demo
/experiments/         per-run configs + results (for the paper)
/tests/               unit + integration tests, mirrors /src
/docs/                architecture notes, literature survey, paper drafts
CLAUDE.md
README.md
pyproject.toml / requirements.txt
```

Module ownership mirrors the team's actual work-plan split from the review deck, so real collaborators can each own a folder.

---

## 7. Build order (do this one phase at a time — don't jump ahead)

0. Scaffold repo structure, `pyproject.toml`, env setup, `.gitignore` for data/models.
1. Ingestion + SAC chunking on a small sample corpus (get this correct before scaling).
2. Embedding + FAISS + BM25 indexing over the chunked corpus.
3. Hybrid retrieval: RRF fusion + reranking, with retrieval-only eval (Precision/Recall/F1) before touching generation.
4. Citation-forced generation (pluggable LLM backend).
5. Verification chain V1 → V2 → V3 → V4 → V5 → V6, built and tested in that order since later layers depend on earlier ones' outputs.
6. Evaluation harness + first ablation runs.
7. FastAPI + Streamlit demo wrapping the finished pipeline.
8. Paper support: consolidate `/experiments` results into tables/figures, write up method + results in `/docs`.

At each phase: implement → write tests → run on the sample corpus → log a result → only then move to the next phase.

---

## 8. Working agreement for Claude Code in this repo

- **Build incrementally, phase by phase (§7).** Don't scaffold all 8 phases' code at once — implement one, verify it runs, then move on.
- **No fabricated results.** Every metric quoted anywhere (chat, docs, comments) must come from an actual run logged in `/experiments`. This matters because the output feeds a research paper.
- **Keep the LLM/embedding backends pluggable** — one thin interface per swappable component (generation LLM, embedding model), so experimentation (§5) doesn't require rewiring the pipeline.
- **Every verification layer must be independently testable** with synthetic cases (e.g. a hand-crafted fabricated citation for V1, a contradicting passage for V2) — write these tests before wiring layers together.
- **Small, real corpus samples in git**, never large legal corpora or model weights — those go in `/data/.gitignore`'d paths with a fetch script instead.
- **Minimize token spend:** prefer editing/extending existing modules over regenerating whole files; keep responses and generated docs concise; don't re-summarize this file back to the user — reference section numbers instead.
- Commit messages describe the phase/module completed, not "misc changes".
