# LangChain port — comparison report

Branch `langchain-port`. The LangChain version lives in `lc/` (run with
`uvicorn lc.api:app --port 8001`, venv `.venv-lc`, requirements in
`lc/requirements.txt`). The plain-Python version in `src/` is unchanged and is
the baseline for every comparison below.

## Acceptance criteria (fixed before any measurement)

The LangChain version is adopted only if **all** of these hold:

1. **Same retrieval quality.** On the 10 labelled queries (SAC chunking, hybrid,
   rerank, k=5, n=50), F1 and recall within 0.02 of
   `experiments/2026-09-23-ablations/retrieval/sac-hybrid-rerank`
   (F1 0.4167, recall 1.000).
2. **Same safety.** Rerunning the verification ablation probes, the full chain
   still surfaces 0 of 28 corrupted claims, and the clean-set mean VCS is within
   0.03 of 0.768 with the same answered/refused counts (7 / 3), using the cached
   answers in `data/eval/ablation_cache.json` so LLM randomness does not decide
   the result.
3. **Tests and UI.** All ported API tests pass, and the React UI works end to end
   against port 8001: ingest a PDF, ask a question, open a proof, run a search,
   open Evaluation. Screenshots of each in `experiments/langchain_port/screens/`.
4. **Not slower.** Mean `/query` latency (reranking on, same machine, same
   questions, same session) no more than 10% above the plain-Python version.
5. **Every intermediate step stays visible.** Retrieved candidates with scores,
   the exact prompt sent, the raw model output and per-claim verdicts are all
   available in the proof/response.

Results are filled in below from logged runs only.
