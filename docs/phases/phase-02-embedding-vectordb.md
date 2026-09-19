# Phase 2 — Embedding + LanceDB hybrid index

**Owner:** Akshith

**Goal:** embed SAC chunks and index them in LanceDB so both vector and keyword queries work locally, no server.

**Tasks**
- `src/embedding/`: a thin, swappable embedding interface. Default to a small local model for dev/test speed; BGE-M3 / GTE-Large selectable for real experiments (see `docs/architecture.md` §5).
- `src/indexing/`: build a LanceDB table from chunk records (text, contextual_summary, metadata, embedding vector); create the full-text index alongside it so hybrid (vector + FTS + RRF) search is available on the same table.
- Query helper: given a text query, return top-k via dense-only, FTS-only, and hybrid, for comparison (this feeds the Retrieval UI page and the retrieval ablation in phase 3/6).
- Tests: build the index over `data/sample/`, run a query whose answer is only findable by keyword and one only findable semantically, confirm hybrid finds both.

**Definition of done:** a local `data/lancedb/` index built from the sample corpus; dense, FTS, and hybrid queries all return sane results; tests pass.
