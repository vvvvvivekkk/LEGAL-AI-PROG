# Results

**Every number below comes from a logged run in `/experiments`.** Each table
names its source directory. Where a quantity has not been measured, it says so
instead of carrying a figure.

## 1. Experimental setup

| | |
|---|---|
| Corpus | `data/sample/*.txt` — 5 synthetic statutes |
| Query set | `data/eval/retrieval_queryset.json` — 10 hand-labeled queries, 14 labeled clauses |
| Embedder | sentence-transformers MiniLM |
| Reranker | `BAAI/bge-reranker-base` cross-encoder |
| NLI | `roberta-large-mnli` |
| Generator | `gemini-flash-lite-latest` |
| VCS threshold | 0.60 (uncalibrated — see §5) |

The retrieval sweep makes no LLM calls. The verification sweep generates once
per query (21 LLM calls total) and replays every ablation arm offline against
the cached generations, so arms differ only in the ablated layer.

## 2. Retrieval and chunking ablation

Source: `experiments/2026-09-23-ablations/retrieval/`. k=5, n=50.

| chunking | mode | rerank | P | R | F1 | RR% | mean ctx chars |
|---|---|---|---|---|---|---|---|
| SAC | dense | on | 0.280 | 1.000 | 0.417 | 100% | 549 |
| SAC | dense | off | 0.280 | 1.000 | 0.417 | 100% | 574 |
| SAC | hybrid | on | 0.280 | 1.000 | 0.417 | 100% | 549 |
| SAC | hybrid | off | 0.260 | 0.967 | 0.392 | 100% | 575 |
| fallback | dense | on | 0.200 | 1.000 | 0.333 | 100% | 1800 |
| fallback | dense | off | 0.200 | 1.000 | 0.333 | 100% | 1508 |
| fallback | hybrid | on | 0.200 | 1.000 | 0.333 | 100% | 1800 |
| fallback | hybrid | off | 0.200 | 1.000 | 0.333 | 100% | 1552 |

Relevance is scored by chunk *text* rather than chunk id, because the query set
labels relevance by SAC id and a paragraph chunker can never string-match those
ids. The same matcher is applied to both arms and reproduces the id-exact
ground truth on all four SAC configs.

**Findings.**

1. **SAC's advantage here is context efficiency, not hit rate.** Both chunkers
   reach RR=100% and R≥0.967, but SAC returns the answer in ~549–575 characters
   of top-5 context against ~1508–1800 for paragraph chunking — roughly 3x less
   text for the same coverage. Since prompt cost and per-claim verification cost
   both scale with context size, this is the operative difference.
2. **The reranker does not improve quality on this corpus.** Seven of eight
   configs sit at the metric ceiling with or without it. The sole exception is
   SAC+hybrid, where reranking lifts R 0.967→1.000 and F1 0.392→0.417 — one
   query. Latency was not measured precisely enough to quote (see §6), but the
   gap between reranked and non-reranked configs is two-plus orders of
   magnitude.
3. **Dense-only matches hybrid on this query set**, and SAC+hybrid without
   reranking is the *worst* SAC configuration. These are paraphrase-style
   queries with no exact-term or citation lookups, which is where keyword fusion
   earns its place — so this does not generalise.
4. **Cross-chunker precision is not comparable** and should not be reported as
   a result. A fallback chunk here is a whole section, so one chunk absorbs all
   of a query's labeled clauses and precision at k=5 is structurally capped at
   0.200 — exactly what all four fallback configs scored on every query.

## 3. Neighbor expansion

Source: measured during implementation on `data/eval` over `data/sample`
(hybrid + rerank, n=50). **Not yet logged as its own `/experiments` run.**

| window | k | P | R | F1 | RR% | avg ctx chunks |
|---|---|---|---|---|---|---|
| 0 | 5 | 0.280 | 1.000 | 0.417 | 100% | 5.0 |
| 1 | 5 | 0.148 | 1.000 | 0.245 | 100% | 10.1 |
| 2 | 5 | 0.112 | 1.000 | 0.193 | 100% | 13.6 |
| 0 | 12 | 0.117 | 1.000 | 0.203 | 100% | 12.0 |
| 1 | 12 | 0.080 | 1.000 | 0.143 | 100% | 19.2 |
| 2 | 12 | 0.068 | 1.000 | 0.123 | 100% | 23.5 |

Expansion costs roughly half the precision at k=5, window=1, and buys nothing
on this query set — because no query in it has an answer split across chunks,
which is the only case expansion exists for. **The benefit is therefore
unmeasured**: demonstrating it requires a labeled split-clause query set, which
does not yet exist. The feature ships disabled by default on this evidence.

## 4. Verification-layer ablation

Source: `experiments/2026-09-23-ablations/verification/`.

### 4.1 Clean query set (10 queries, 14 claims)

| Arm | mean VCS | ANSWER | ABSTAIN | weak claims surfaced |
|---|---|---|---|---|
| full_chain | 0.7675 | 7 | 3 | 0 |
| minus_v1 | 0.7675 | 7 | 3 | 0 |
| minus_v2 | 0.8125 | 8 | 2 | 1 |
| minus_v3 | 0.7769 | 7 | 3 | 0 |
| minus_v4 | 0.7233 | 7 | 3 | 0 |
| minus_v5 | 0.7675 | 10 | 0 | 5 |
| minus_v6 | 0.7675 | 7 | 3 | 0 |

The clean set contains zero fabricated citations and zero contradictions across
14 real claims, so the strict error proxy has no signal on it.

### 4.2 Known-bad probes

Two deterministic perturbations of the *same cached answers* supply that
signal: every citation rewritten to an id never retrieved
(`fabricated_citation`), and each claim's text swapped for a real claim from a
different query while keeping its citation (`mismatched_claim`). 14 bad claims
each; no LLM calls.

Bad claims surfaced to the user, out of 14:

| Arm | fabricated_citation | mismatched_claim |
|---|---|---|
| full_chain | 0 | 0 |
| minus_v1 | 0 | 0 |
| minus_v2 | 0 | 0 |
| minus_v3 | 0 | 0 |
| minus_v4 | 0 | 0 |
| **minus_v5** | **14** | **14** |
| minus_v6 | 0 | 0 |

**Findings.**

1. **V5 is the only layer whose removal lets known-bad claims reach the user** —
   28/28 across both probes, against 0 for every other single-layer ablation.
   The detection layers drive a corrupted claim to 0.0 either way; V5 is what
   converts that score into a refusal. Detection without a gate changes nothing
   the user sees.
2. **V1, V2 and V3 are mutually redundant as detectors** under the current
   weighting: with V1 disabled, a fabricated citation still scores 0 because V2
   finds no premise and V3's fidelity collapses. V1's unique contribution is
   *diagnosis* — it is the only layer that names the missing ids in the proof
   trace.
3. **V2 moves the decision most on clean input**: removing it flips one query
   from ABSTAIN to ANSWER and lifts mean VCS 0.7675→0.8125. V3 (+0.009) and V4
   (−0.044) change no decision.
4. **V6 is structural** — disabling it alters no score and no decision, only
   whether a proof object is emitted. No numeric delta is claimed for it.

## 5. Calibration — outstanding

All 10 queries retrieved their gold chunk, yet the full chain answers only 7:
**three false abstentions**, each from the NLI returning NEUTRAL on a correctly
cited claim. One ("grounds for eviction") scores 0.0 across all three of its
claims with no hard gate firing.

The 0.60 threshold is the provisional default and **has not been calibrated**.
Phase 6's calibration task remains open, and §4.1 is the evidence motivating
it. No calibration curve is presented because none has been computed.

## 6. Threats to validity

- **Small n throughout**: 10 queries, 14 claims, 5 synthetic statutes, one
  embedder, one reranker, one NLI model, one generator.
- **The query set is saturated.** Every retrieval config scores RR=100% and
  R≥0.967; F1 varies 0.333–0.417 driven almost entirely by chunk granularity.
  It cannot discriminate between retrieval configurations, and conclusions about
  dense-vs-hybrid or reranking drawn from it are at noise level. Harder queries
  — cross-section, unanswerable, exact-citation lookup — are needed before those
  questions can be settled.
- **The probes are synthetic perturbations**, not observed model hallucinations.
  They measure what each layer catches, not how often this generator
  hallucinates. A hallucination *rate* has not been measured.
- **`abstention_accuracy` as computed equals "fraction answered"**, since every
  query in this set retrieved its gold chunk and is expected-ANSWER. It cannot
  reward correct abstention; `minus_v5` scoring 1.00 on it must not be read as
  "V5 hurts".
- **V4 ran on a 5-query subset** (2 resamples each) within the LLM budget, so
  the `minus_v4` delta comes entirely from those 5.
- **Fallback R=1.000 is partly a corpus artifact**: each sample statute section
  is one short paragraph, so one fallback chunk equals one section. On documents
  whose sections span paragraphs it would fall.
- **Latency was measured but is not quoted.** Reranked configs ranged
  6.7–12.8 s/query across two sweeps of the same configuration (the first
  reranked config in each sweep also carries cross-encoder warm-up);
  non-reranked 0.020–0.085 s. Only the order-of-magnitude gap is reliable.
- **No evaluation on a public benchmark.** LegalBench-RAG is named as the
  intended corpus in `README.md` but has not been run. **Not yet measured.**
- **No end-to-end hallucination rate, citation precision/recall, or DRM** —
  these are listed in phase 6 and remain unimplemented.
