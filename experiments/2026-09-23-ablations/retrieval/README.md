# Retrieval / chunking ablation sweep

Full factorial: chunking (SAC vs fallback paragraph) x mode (dense vs hybrid)
x reranker (on/off) = 8 runs. Corpus `data/sample/*.txt` (5 statutes), query
set `data/eval/retrieval_queryset.json` (10 queries, 14 labeled clauses),
k=5, n=50, MiniLM embedder + BAAI/bge-reranker-base. No LLM calls.

Reproduce: `python -m src.evaluation.run_ablation_sweep --out experiments/<date>-ablations/retrieval`

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

## How relevance is scored across chunkers

The query set labels relevance by SAC chunk id (`act::s4:b`), which can never
string-match a paragraph id (`act::p12`), so scoring the fallback arm by id
would report a fake 0.000. Instead each labeled id is resolved to its text and
a retrieved chunk counts as relevant when it substantially carries that text
(verbatim containment either way, else >=0.8 of the labeled clause's tokens
present). The same matcher is applied to both arms. On all four SAC configs it
reproduces the id-exact ground truth exactly — stored per run as
`id_exact_crosscheck`, whose `mean_retrieved_chars` is 0.0 because the id-exact
path does not read chunk text.

## Caveats

- **Cross-chunker precision is not directly comparable.** A fallback chunk here
  is a whole section, so one chunk absorbs every labeled clause of a query and
  precision at k=5 is structurally capped at 0.200 — which is exactly what all
  four fallback configs scored on every query. Recall and RR% are sound;
  precision restates granularity. Compare `mean_retrieved_chars` instead.
- **Latency figures are noisy** and are not quoted here. Reranked configs
  ranged 6.7-12.8 s/query across two sweeps for the same config (the first
  reranked config in each sweep also carries cross-encoder warm-up), and
  non-reranked 0.020-0.085 s. Only the order-of-magnitude gap is reliable.
- **Fallback's R=1.000 is partly an artifact of this corpus**: each sample
  statute section is a single short paragraph, so one fallback chunk = one
  section. On documents whose sections span several paragraphs it would drop.
- The query set is saturated (every config RR=100%, R>=0.967), so it cannot
  discriminate further; see the findings note in the paper draft.
- `fts`-only mode was not swept.
