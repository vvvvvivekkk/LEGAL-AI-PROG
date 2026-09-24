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

## Results

All runs on 2026-09-24, same Windows machine, same session. Reproduce with the
commands listed per criterion; raw numbers are in the linked `results.json`.

| # | Criterion | Target | Python (`src/`) | LangChain (`lc/`) | Result |
|---|---|---|---|---|---|
| 1 | Retrieval F1 / recall | within 0.02 of 0.4167 / 1.000 | 0.4167 / 1.000 | 0.4167 / 1.000 | **PASS** |
| 2 | Corrupted claims surfaced | 0 / 28 | 0 / 28 | 0 / 28 | **PASS** |
| 2 | Clean mean VCS, answered / refused | within 0.03 of 0.768, 7 / 3 | 0.7675, 7 / 3 | 0.7675, 7 / 3 | **PASS** |
| 3 | Ported API tests + UI end to end | all pass, 5 screenshots | — | 111 passed, 5 / 5 steps HTTP 200 | **PASS** |
| 4 | Mean `/query` latency | ≤ +10% | 13.86 s | 14.50 s (+4.6%) | **PASS** |
| 5 | Intermediate steps visible | candidates, prompt, raw output, verdicts | — | present with `trace: true` | **PASS** |

### 1. Retrieval — `experiments/langchain_port/retrieval/`

`.venv-lc/Scripts/python -m lc.eval.retrieval_eval`. Both pipelines are built in
one process on the same models over `data/sample/*.txt` (SAC, hybrid, rerank,
k=5, n=50). Both give P 0.28, R 1.000, F1 0.4167, retrieval rate 1.00, which
equals the `sac-hybrid-rerank` ablation run. The top-5 ids are **identical in
order for 10/10 queries** (`comparison.json`), so the two retrievers produce the
same results, not just the same score.

### 2. Safety — `experiments/langchain_port/safety/`

`.venv-lc/Scripts/python -m lc.eval.safety_eval`. Replays the cached answers in
`data/eval/ablation_cache.json` (no LLM calls, same roberta-large-mnli). The
LangChain path uses `CitationOutputParser` and the `verification_step` Runnable,
and the Python path uses `parse_answer` and `verify_answer`. Full chain:

- clean set: mean VCS 0.7675, 7 ANSWER / 3 ABSTAIN in both. Decision and VCS
  are **identical for 10/10 queries**.
- probes: fabricated_citation 0/14 and mismatched_claim 0/14 surfaced in both
  (0/28 total).

This is expected, not independent evidence of safety: `lc/verification.py`
calls the `src/verification` functions directly. The run shows the LangChain
parsing and wiring feed those functions exactly the same inputs.

### 3. Tests and UI — `experiments/langchain_port/screens/`

- `.venv-lc/Scripts/python -m pytest lc/tests`: **111 passed**. This includes
  the fix to `test_db_path_can_be_overridden_by_env`, which used to reload
  `lc.deps` and break `dependency_overrides` for later tests.
- `.venv/Scripts/python -m lc.eval.ui_screens` runs the React dev server with
  `VITE_API_BASE=http://localhost:8001` against an isolated index (`steps.json`):
  1. `1-ingest-pdf.png`: a real PDF ingested (HTTP 200, 229 chunks, fallback
     paragraph chunking as expected for a non-statute).
  2. `2-ask.png`: the tenancy deposit question answered as Verified, VCS 1.00.
  3. `3-proof.png`: the claim's proof opened (V1 citation exists, V2 entails
     0.99, V3 fidelity 100%, V4 skipped).
  4. `4-search.png`: dense, lexical and hybrid columns (HTTP 200).
  5. `5-evaluation.png`: the embedding map and logged runs, including these.

### 4. Latency — `experiments/langchain_port/latency/`

`.venv-lc/Scripts/python -m lc.eval.latency_eval`. Both APIs run side by side
(src on :8000 from `.venv`, lc on :8001 from `.venv-lc`) with separate fresh
indexes of `data/sample/*.txt`. Settings: rerank on, `self_consistency` 0,
LLM_PROVIDER=groq, one warm-up query each. The 10 labelled questions run ×2
rounds, alternating servers with the order flipped on every question. Timing is
client-side wall clock.

| | n | mean | median | stdev |
|---|---|---|---|---|
| Python | 20 | 13.86 s | 13.02 s | 2.77 s |
| LangChain | 20 | 14.50 s | 14.06 s | 2.56 s |

LangChain is +4.6% on the mean, inside the 10% limit. With n=20 and a
stdev of about 2.6 s, almost all of which is Groq round-trip time, this
difference is not distinguishable from zero.

Answered counts differed (Python 8/20, LangChain 10/20). This is sampling
variance, not a pipeline difference: both run at temperature 1.0, and
criterion 2 shows identical decisions on identical text. It is not a latency
criterion and is not counted.

**The first latency run failed**, with all 20 LangChain requests returning 503:
`langchain-groq` 1.1.3 rejects `ChatGroq(temperature=None)`. None of the
ported API tests caught this because they all stub the LLM. The fix passes
temperature 1.0, which is Groq's API default and so the same as `src/`, which
sends none. `lc/tests/test_chat_model_factory.py` now constructs every provider,
and it failed before the fix. The numbers above come from the rerun after the
fix.

### 5. Intermediate steps

With `"trace": true`, `/query` returns the reranked candidates with score and
score kind, the exact system and human prompt messages, the raw model output,
the parsed claims, and the per-claim V1–V6 verdicts in the proof. The default
response stays byte-compatible with `src/`'s `QueryResponse`. Both are covered
by `lc/tests/api/test_trace.py`, which passes.

## Verdict: **ADOPT**

All five criteria, which were fixed before measuring, hold. Retrieval and
verification are identical query for query, the UI works unchanged against the
LangChain API, and latency is within noise.

Conditions and caveats that come with the adoption:

- **Most of the value still lives in `src/`.** LangChain supplies the loaders,
  splitters interface, vector store, BM25, cross-encoder wrapper, prompt
  templates, chat-model clients and LCEL composition. It has no equivalent of
  the V1–V6 chain, so that is wrapped rather than ported. Adopting means
  keeping `src/verification` (and the SAC parser) as first-class code.
- **`langchain-community` is being sunset.** It is the deprecation warning seen
  on every test run. The loader, LanceDB store, BM25 retriever and
  cross-encoder all come from it. Before `src/` is retired, these should move
  to standalone integration packages or thin local code.
- **Provider wrappers need live smoke tests.** The ChatGroq bug shows that
  stubbed API tests do not exercise the real client construction. Keep
  `test_chat_model_factory.py` and run one live `/query` per provider before
  releases.
- Small n throughout: 10 labelled queries, 28 synthetic bad claims, 20 timed
  requests per arm, one machine, one LLM provider.
