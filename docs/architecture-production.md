# Production RAG Architecture — the full picture, and where this project actually stands

This doc exists because it's hard to see what's unique about a project from inside a stream of small commits. It does two things: (1) lays out, end-to-end, what a *real production* RAG system looks like — the full stack, not a toy version — and (2) maps this project against every layer of it, explicitly, with evidence (file paths, real bugs found and fixed, test counts) rather than impressions.

We are **not deploying this anywhere** — it runs on a laptop for a demo. Section 4 says plainly which production layers that puts out of scope, and that's a deliberate, correct call, not a gap to feel bad about.

## 1. The full production RAG stack (reference)

A real, deployed production RAG system has roughly these layers:

1. **Data ingestion & connectors** — crawlers/APIs pulling from real sources, OCR for scanned documents, deduplication, versioning, access control per document.
2. **Preprocessing & chunking** — fixed-size (naive), semantic (embedding-similarity boundaries), or hierarchical/contextual chunking that preserves document structure.
3. **Embedding generation** — model choice, batching, caching so the same text is never re-embedded, sometimes multiple embedding "views" per chunk.
4. **Indexing & vector stores** — managed (Pinecone, Weaviate Cloud) or self-hosted, hybrid dense+sparse search, metadata filtering, sharding once the corpus is large.
5. **Retrieval** — dense/sparse/hybrid search, query rewriting or expansion, multi-hop retrieval for complex questions, reranking.
6. **Context assembly & prompting** — token budgeting across retrieved chunks, citation-friendly formatting, instructions the model actually follows.
7. **Generation** — model selection, streaming, tool use, output guardrails.
8. **Post-generation verification / grounding** — citation verification, factuality/entailment scoring, hallucination detection — most production systems have *none* of this beyond maybe a single toxicity filter.
9. **Confidence calibration & abstention** — deciding when *not* to answer, or when to escalate to a human — almost universally missing in shipped RAG products.
10. **Observability & evaluation** — structured logging, tracing, offline eval sets, online A/B testing, user feedback loops.
11. **Serving & scaling** — API layer, response caching, rate limiting, autoscaling, cost controls.
12. **Security & governance** — access control, PII handling, audit trails, data retention policy.
13. **CI/CD & lifecycle** — index rebuilds on new data, model version rollout, canary releases, rollback.

## 2. Where this project actually stands — layer by layer, with evidence

| Layer | Status | Evidence |
|---|---|---|
| 1. Ingestion | **Implemented**, real-world tested | `src/ingestion/loaders.py` (real PDF via `pypdf`, `.txt`), `src/indexing/dedup.py` (SHA-256 content hash + source-id collision → 409, prevents duplicate re-ingestion), `DELETE /documents/{source_id}` for clean re-ingestion of edited files. Tested against real CUAD/MAUD contract PDFs, not just fixtures. |
| 2. Chunking | **Implemented, dual-strategy** | `src/chunking/` — Summary-Augmented Chunking (SAC) for structured statutes (Act/Chapter/Section), automatic fallback to paragraph chunking for unstructured real-world contracts (`src/chunking/fallback.py`) — most systems pick one strategy and silently do badly on documents that don't fit it. |
| 3. Embedding | **Implemented, pluggable** | `src/embedding/` — swappable interface (MiniLM for dev speed, BGE-M3/GTE-Large slot documented for production quality), avoiding the common mistake of hardcoding one model. |
| 4. Indexing | **Implemented, hybrid** | LanceDB — embedded, file-based, no server to run — with native vector + full-text index on the same table. See `docs/architecture.md` §2 for why this beats hand-wiring FAISS + a separate BM25 index, which is what most tutorials do. |
| 5. Retrieval | **Implemented, with a real fixed bug** | `src/retrieval/` — hybrid search + cross-encoder reranking. **Real production bug found and fixed**: the candidate pool feeding the reranker was too shallow (`n = max(4*k, k)`), so the reranker could never promote a correct answer sitting at rank 39 — fixed to `n = max(8*k, 100)`. This is exactly the class of subtle bug that separates "it ran once" from "it's actually correct." |
| 6. Context assembly | **Implemented, with a real fixed bug** | Citation-forced prompt template (`src/generation/prompt.py`). **Real bug found**: Gemini's token budget was being consumed by internal "thinking" tokens before the answer, truncating output mid-citation — fixed by raising the budget and measuring `finish_reason`. |
| 7. Generation | **Implemented, pluggable, multi-provider** | `src/generation/adapters/` — Claude, OpenAI, Gemini, plus a general-knowledge fallback for questions the corpus can't answer, **explicitly labeled as unverified** so it's never confused with a sourced answer — an epistemic-honesty UX detail most chat products skip. |
| 8. Post-generation verification | **Implemented — this is the project's core contribution** | The V1–V6 chain (`src/verification/`): citation existence → NLI entailment → atomic claim fidelity → self-consistency → calibrated Verification Confidence Score → structured Proof Object. Most production RAG systems ship *zero* of this layer. See §3 below — this is the actual novelty. |
| 9. Abstention | **Implemented, with a real fixed bug** | VCS-gated abstention (`src/verification/v5_vcs.py`). **Real bug found**: a literal leading space in one corpus filename (`" 064-19 Non Disclosure..."`) propagated into every chunk's source id, silently breaking citation-matching in V1 and dragging VCS below threshold — fixed by stripping ids at ingest. This is a genuine data-hygiene class of production bug, not a logic error. |
| 10. Observability & evaluation | **Partial** | `/experiments` logging convention exists (`docs/phases/phase-06-evaluation.md`); ablation sweeps (SAC on/off, hybrid vs dense-only, verification layers on/off) are designed but not yet run at scale. Real batch end-to-end checks exist (`scripts/e2e_corpus_check.py`, a Playwright-driven Ask/Ingest batch check) but aren't a full offline eval harness yet. |
| 11. Serving & scaling | **Out of scope, deliberately** — see §4 | |
| 12. Security & governance | **Out of scope, deliberately** — see §4 | |
| 13. CI/CD & lifecycle | **Partial** | Dedup + delete/reingest covers the data lifecycle. No automated CI pipeline (tests are run manually before each push) — reasonable for a local demo, would be the first addition if this went further. |

**Test evidence, not a claim:** 160+ automated tests, run and passing before every commit in this repo's history — including real integration tests against a real embedder and a real LLM provider, not just mocks.

## 3. What's actually unique here — the pitch, stated plainly

Most RAG projects (student and production alike) do retrieval-then-generation and stop. A smaller number add *one* hallucination check — usually a single classifier score. This project does neither. It does:

1. **Context-preserving chunking that adapts to the document** (SAC for structured law, fallback for real-world contracts) instead of one-size-fits-all fixed windows.
2. **A local, embedded, file-based hybrid vector store** (LanceDB) instead of the common FAISS-plus-hand-wired-BM25 pattern — simpler to run, same capability.
3. **A six-layer verification chain that produces one calibrated score (VCS) and a full auditable Proof Object** — not "is this hallucinated: yes/no", but a decomposed, per-claim, per-layer trace of *why* an answer is trusted or rejected. This is the genuinely novel piece: citation existence, entailment, atomic-claim fidelity, and self-consistency are each real, separately-studied techniques in the hallucination-reduction literature (see `README.md`'s Related Work table) — this project is what integrating all four into one gated pipeline, with a research-paper-ready ablation plan, actually looks like.
4. **Calibrated abstention with a labeled fallback** — the system knows the difference between "I can prove this" and "I don't know, but here's my general knowledge, clearly marked as such" — most chat products blur that line on purpose.
5. **Real production bugs, found and fixed through actual diagnosis, not guesswork** — the shallow-pool, token-budget, and leading-space bugs above are the kind of thing that only surfaces from testing against real documents and real questions, and the fix for each traces to a measured root cause. That's the difference between a demo that happened to work once and a system that's been debugged.

## 4. What's explicitly out of scope, and why that's the right call

Because this runs on a laptop for a demo, not a deployed service, the following are **documented and understood, not missing by accident**:

- No cloud deployment, container orchestration, or autoscaling — there's one process, on one machine, for one demo.
- No multi-tenant auth, rate limiting, or API-key management for external users — nobody but the presenter uses this.
- No managed vector database, sharding, or horizontal scaling — the corpus is small enough that LanceDB on local disk is not just adequate, it's the *correct* choice at this scale (see `docs/architecture.md` §2).
- No CI/CD pipeline or canary releases — tests are run manually before each push, which is appropriate for a project at this stage.

If asked "how would this scale to production," the honest answer is: swap LanceDB for a managed hybrid-search vector store, add an API gateway with auth/rate-limiting, wire `/experiments` logging into real observability (traces + dashboards), and automate the ablation suite into CI. None of that changes the core pipeline or the verification chain — it's infrastructure around something that's already architecturally sound.
