# Verification-layer ablation sweep (V1-V6)

10 queries from `data/eval/retrieval_queryset.json` over a SAC index of
`data/sample/*.txt` (hybrid + rerank, k=5, n=100 — the `/query` settings).
Generation ran once per query on `gemini-flash-lite-latest` (21 LLM calls
total, including 2 resamples each for the first 5 queries) and was cached to
`data/eval/ablation_cache.json`; every arm then replays that cache offline
against the real roberta-large-mnli, so the arms differ only in the ablated
layer, not in the text being verified.

Reproduce:
```
python -m src.evaluation.run_verification_ablation generate   # LLM calls, writes the cache
python -m src.evaluation.run_verification_ablation ablate     # offline, no LLM calls
```

## Arms

| Arm | mean VCS | ANSWER | ABSTAIN | weak claims surfaced | abstention acc. |
|---|---|---|---|---|---|
| full_chain | 0.7675 | 7 | 3 | 0 | 0.70 |
| minus_v1 | 0.7675 | 7 | 3 | 0 | 0.70 |
| minus_v2 | 0.8125 | 8 | 2 | 1 | 0.80 |
| minus_v3 | 0.7769 | 7 | 3 | 0 | 0.70 |
| minus_v4 | 0.7233 | 7 | 3 | 0 | 0.70 |
| minus_v5 | 0.7675 | 10 | 0 | 5 | 1.00 |
| minus_v6 | 0.7675 | 7 | 3 | 0 | 0.70 |

## Known-bad probes

The clean set contains no fabricated citation and no contradiction, so the
strict error proxy has no signal on it. Two deterministic perturbations of the
*same cached answers* supply that signal — every citation rewritten to an id
that was never retrieved (`fabricated_citation`), and each claim's text swapped
for a real claim from a different query while keeping its citation
(`mismatched_claim`). 14 bad claims each, no LLM calls.

Bad claims surfaced to the user (out of 14):

| Arm | fabricated_citation | mismatched_claim |
|---|---|---|
| full_chain | 0 | 0 |
| minus_v1 | 0 | 0 |
| minus_v2 | 0 | 0 |
| minus_v3 | 0 | 0 |
| minus_v4 | 0 | 0 |
| **minus_v5** | **14** | **14** |
| minus_v6 | 0 | 0 |

## Findings

1. **V5 is the only layer whose removal lets known-bad claims reach the user** —
   28/28 across both probes, versus 0 for every other single-layer ablation. The
   detection layers score a corrupted claim at 0.0 regardless; V5 is what turns
   that score into a refusal.
2. **V1/V2/V3 are mutually redundant as detectors** under the current weights: a
   fabricated citation is zeroed by V1's gate, but with V1 off V2 finds no
   premise and V3's fidelity collapses, so the claim still scores 0. V1's unique
   contribution is *diagnosis* — it is the only layer that reports
   `gate_failed="citation"` with the missing ids.
3. **V2 moves the decision most on clean input**: removing it flips one query
   from ABSTAIN to ANSWER and lifts mean VCS 0.7675 -> 0.8125. V3 (+0.009) and
   V4 (-0.044) change no decision.
4. **The full chain is over-conservative here.** All 10 queries retrieved their
   gold chunk, yet only 7 are answered — 3 false abstentions, all from the NLI
   returning NEUTRAL on correctly-cited claims. The phase-6 threshold
   calibration is still outstanding and this is the evidence for it.
5. **V6 is structural** — disabling it changes no score and no decision, only
   whether a Proof Object is emitted. No numeric delta is claimed.

## Caveats

- **V4 ran on a 5-query subset** (2 resamples each) to stay inside the LLM
  budget; the other 5 had no resamples in any arm, so the `minus_v4` delta comes
  entirely from those 5.
- **The probes are synthetic perturbations of real answers**, not observed model
  hallucinations. They measure what each layer catches, not how often this model
  hallucinates.
- `abstention_accuracy` here equals "fraction answered", because every query in
  this set retrieved its gold chunk and is therefore expected-ANSWER. It cannot
  reward correct abstention, so `minus_v5` scoring 1.00 must not be read as
  "V5 hurts".
- Small-n throughout: 10 queries, 14 claims, one corpus, one LLM, one NLI model,
  uncalibrated 0.60 threshold.
- `load_runs()` walks only immediate children of `experiments/`, so it reads
  this directory's own `results.json` but not the per-arm subdirectories.
