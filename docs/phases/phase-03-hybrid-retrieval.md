# Phase 3 — Hybrid retrieval: fusion + reranking

**Goal:** turn phase 2's raw hybrid search into a retrieval stage with a quality bar, evaluated on its own before generation touches it.

**Tasks**
- `src/retrieval/`: wrap LanceDB's hybrid search, add cross-encoder reranking on the fused top-N before truncating to top-k context.
- Retrieval-only evaluation: Precision/Recall/F1 and Retrieval Rate (RR%) against a small hand-labeled query set on the sample (later real) corpus — no generation involved yet.
- Config knobs for ablation (phase 6): dense-only vs hybrid, with/without reranking, k and N values.

**Definition of done:** given a query, the module returns a ranked, reranked context set with scores; retrieval-only metrics are computed and logged (not generation-dependent).
