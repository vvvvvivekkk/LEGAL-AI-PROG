# Phase 1 — Ingestion + Summary-Augmented Chunking (SAC)

**Goal:** turn raw legal documents into SAC chunks with metadata, correctly, on the sample corpus, before scaling to a real one.

**Tasks**
- `src/ingestion/`: a real PDF loader (text extraction via `pypdf`/`pdfplumber`, not stubbed — this is the primary real-world input format) plus a `.txt` loader, text cleaning, structural parsing (act → chapter → section → clause where present), metadata extraction (source id, act/section ref, jurisdiction, date). HTML loader can stay a stub for now.
- `src/chunking/`: SAC implementation —
  1. split by structural boundaries first (not fixed windows),
  2. attach a contextual summary of each chunk's parent section,
  3. emit chunk records: `{chunk_id, text, contextual_summary, metadata}`.
- Unit tests: a document with known structure chunks the way it should; metadata is correctly extracted; a chunk's contextual summary actually reflects its parent section (spot-check on synthetic docs).

**Definition of done:** running ingestion+chunking over `data/sample/` produces a deterministic, inspectable list of chunk records; tests pass.
