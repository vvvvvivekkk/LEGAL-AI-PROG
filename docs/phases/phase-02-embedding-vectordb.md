# Phase 2 — Embedding + LanceDB hybrid index

**Goal:** embed SAC chunks and index them in LanceDB so both vector and keyword queries work locally, no server.

**Tasks**
- `src/embedding/`: a thin, swappable embedding interface. Default to a small local model for dev/test speed; BGE-M3 / GTE-Large selectable for real experiments (see `docs/architecture.md` §5).
- `src/indexing/`: build a LanceDB table from chunk records (text, contextual_summary, metadata, embedding vector); create the full-text index alongside it so hybrid (vector + FTS + RRF) search is available on the same table. Indexing must support **incremental append** (adding one newly-ingested document's chunks to an existing table) as well as full rebuild — the UI upload flow below depends on append working without re-embedding the whole corpus.
- Query helper: given a text query, return top-k via dense-only, FTS-only, and hybrid, for comparison (this feeds the Retrieval UI page and the retrieval ablation in phase 3/6).
- **Minimal ingest-to-vectordb UI** (`src/ui/pages/1_Ingestion.py`, pulled forward from phase 7's fuller version): a file uploader accepting `.pdf`/`.txt` that, on submit, runs phase-1 ingestion+SAC chunking → phase-2 embedding → appends into the LanceDB table, then shows the new chunks + a running total of indexed chunks/documents. This is the real path for "upload a PDF and it lands in the vector DB" — phase 7 later adds the other 3 pages around it.
- Tests: build the index over `data/sample/`, run a query whose answer is only findable by keyword and one only findable semantically, confirm hybrid finds both. Add a test for incremental append (index one doc, append a second, confirm both are searchable and the first wasn't duplicated/lost).

**Definition of done:** a local `data/lancedb/` index built from the sample corpus; dense, FTS, and hybrid queries all return sane results; incremental append works; uploading a PDF through the minimal ingestion UI page results in new, searchable rows in LanceDB; tests pass.
