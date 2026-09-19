# Legal-RAG — Claude Code context (keep this file short)

Hallucination-resistant Legal RAG system. Full detail lives in `/docs`, not here — read `docs/architecture.md` first, then the relevant `docs/phases/phase-NN-*.md` before touching that phase's code. Don't re-derive or re-paste that content here or back to the user; reference file/section instead.

**One-liner:** legal Q&A over retrieved documents, where every claim in the answer is checked against its source before being shown, and ships with a structured proof trace.

**Core pipeline:** ingest → SAC chunk → embed → LanceDB (hybrid vector+FTS, local, file-based) → rerank → citation-forced generation → 6-layer verification chain (V1–V6) → abstain-or-answer → API + multi-page UI. Details: `docs/architecture.md`.

**Build order:** one phase at a time, per `docs/phases/`. Don't start phase N+1 until phase N has passing tests.

**Rules:**
- No fabricated metrics/results — anything quoted must come from a logged run in `/experiments`.
- Keep LLM + embedding backends behind thin swappable interfaces.
- Plain commit messages describing what changed — no AI/Claude attribution or co-author lines in commits on this repo (explicit user preference).
- Don't inflate this file — extend `/docs` instead.
