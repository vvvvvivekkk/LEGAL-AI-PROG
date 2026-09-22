# AGENTS.md

Cross-tool agent context for this repo (Claude Code, Cursor, Aider, etc.). If you're Claude Code, `CLAUDE.md` has the same content plus Claude-specific notes — either file is a valid starting point.

## What this is

A hallucination-resistant Legal RAG system: legal Q&A where every claim in an answer is checked against its source before being shown, with a structured proof trace attached. Full architecture: `docs/architecture.md`. Development phases and their status: `docs/phases/*.md`.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set LLM_PROVIDER + LLM_API_KEY for /query; ingest/retrieve/search work without one
cd web && npm install
```

## Running

```bash
uvicorn src.api.main:app --reload      # backend, port 8000
cd web && npm run dev                   # frontend, port 5173
```

## Testing

```bash
pytest -q
```
161+ tests should pass. Some skip in network-restricted sandboxes (they need to download an embedding model) — that's expected there, not a failure.

## Conventions

- One phase at a time (`docs/phases/`) — don't start phase N+1 until phase N's tests pass.
- Diagnose before fixing: measure the actual failing stage (hit the API directly) before changing code.
- No fabricated metrics — anything quoted must trace to a logged run in `/experiments`.
- Small, frequent commits with plain descriptions. No AI/tool attribution in commit messages on this repo.
- The real document corpus lives in `data/corpus/` (gitignored) — real contracts (NDAs, mergers), not statutes, so most documents go through fallback paragraph chunking rather than the Act/Section parser. That's expected, not a bug.
