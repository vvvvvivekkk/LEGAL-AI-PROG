# Phase 8 — Paper write-up support

**Goal:** turn `/experiments` results into a submittable paper, not just a working system.

**Tasks**
- Consolidate ablation results (phase 6) into the tables/figures a paper needs: retrieval quality by config, hallucination rate with/without each verification layer, VCS calibration curve, latency/cost tradeoffs.
- Draft method section directly from `docs/architecture.md` (SAC, hybrid retrieval via LanceDB, the V1–V6 chain, VCS).
- Related-work section from the comparison table in `README.md` (Reuter et al., EscavAI, Embedding-Free RAG, RAGTruth, LegalBench-RAG, Magesh et al.) plus any new papers found while building.
- Qualitative examples: pull 2–3 real Proof Objects (phase 5/7 output) showing a caught hallucination and a correctly abstained answer.

**Definition of done:** a draft in `docs/paper/` with method, results (from logged experiments only), related work, and qualitative examples, ready for the guide's review.
