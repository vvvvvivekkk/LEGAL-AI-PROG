# Phase 4 — Citation-forced generation

**Owner:** Uday

**Goal:** generate answers from retrieved context where every claim is attributed to a chunk id, using a pluggable LLM backend (no API keys required to build/test the interface).

**Tasks**
- `src/generation/`: one thin interface (`generate(query, context_chunks) -> Answer`) with adapters for Claude / GPT-4o / Llama 3.1 / Gemini, selected via config/env var — the pipeline never hardcodes a provider.
- Prompt template that forces inline citations to chunk ids for every factual claim, and forbids answering beyond the provided context.
- `Answer` structure: raw text + parsed `(claim, cited_chunk_ids)` list — this is what phase 5's verification chain consumes.
- Tests: with a mocked/stubbed LLM adapter, confirm the parser correctly extracts claims and citations from a known-format response, and rejects malformed ones.

**Definition of done:** generation interface + prompt template implemented and unit-tested against a stub adapter; a real adapter can be wired in later purely by supplying an API key, no code changes to the pipeline.
