# Batch Ask check

Driver: `scripts/batch_ask_check.py` — Playwright against the real Ingest and
Ask pages, both servers started by the script, isolated index.
Model: `gemini-flash-lite-latest` (the `gemini-2.5-flash` free-tier daily quota
of 20 requests was already exhausted).

## Ingestion

All ten ContractNLI agreements were uploaded through the Ingest page and
indexed, in every run.

| file | status |
|---|---|
| `1013322_0000912057-00-023405_document_2.txt` (Yahoo! / Restrac) | indexed |
| `1013687_0000950144-96-001973_document_37.txt` (Phoenix International) | indexed |
| `1012459_0000912057-97-027209_document_4.txt` (Federal Express / IBS) | indexed |
| `1002276_0001036050-99-002047_document_13.txt` | indexed |
| `1010471_0000950134-97-006281_document_5.txt` | indexed |
| `1011671_0000936392-99-000246_document_46.txt` | indexed |
| `1013687_0000950144-96-001973_document_38.txt` | indexed |
| `1014959_0000950116-96-000618_document_7.txt` | indexed |
| `1016503_0000929624-00-000894_0010.txt` | indexed |
| `1017358_0001017358-97-000002_document_4.txt` | indexed |

## Questions

No single run produced a clean result for all ten questions. The free-tier
backend returns `503 UNAVAILABLE` in bursts; run 2 lost four specific questions
to it, and run 3 — which answered all five specific questions cleanly after
question-level retry was added — was killed by the host for low memory before
it reached the general half. The table below states which run each row is from.
`results.json` holds run 2 verbatim.

| # | kind | question | outcome | VCS | cited expected doc | run |
|---|---|---|---|---|---|---|
| 1 | specific | Which state's laws govern the Yahoo!/Restrac agreement? | **abstained** | 0.47 (run 1) | — | 3 |
| 2 | specific | Within how many days must an oral disclosure be confirmed in writing? | **verified** | — | — | 3 |
| 3 | specific | What is Residual Information and may the receiving party use it? | **verified** | — | — | 3 |
| 4 | specific | Whose prior written authorization is required (Phoenix)? | **abstained** | — | — | 3 |
| 5 | specific | Which two companies are parties to the FedEx agreement? | **verified** | 1.00 | yes | 2 |
| 6 | general | What is a non-disclosure agreement? | **general_knowledge** | — | n/a | 2 |
| 7 | general | What is confidential information? | **verified** | 0.99 | n/a | 2 |
| 8 | general | Define a mutual NDA. | **general_knowledge** | — | n/a | 2 |
| 9 | general | What does consideration mean in contract law? | **general_knowledge** | — | n/a | 2 |
| 10 | general | Explain what injunctive relief is. | **general_knowledge** | — | n/a | 2 |

Run 3's per-question VCS and citation checks were lost when the process was
killed before it wrote `results.json`; only the printed outcomes survive.

## What this shows

- **The general-knowledge fallback works and is correctly scoped.** Four of
  five general questions fell back and were badged as unverified; none of them
  produced a citation or a VCS. Question 7 was *not* a fallback — the corpus
  actually defines "Confidential Information", so it was answered and verified
  from the documents at VCS 0.99. That is the intended precedence: the fallback
  only fires when verification declines.
- **No general question was silently passed off as sourced**, and no specific
  question was answered from model priors.
- **Citations point at the right document** where an answer was verified with
  recorded citations (question 5 → the FedEx/IBS file).
- **Two specific questions still abstain** (1 and 4) on clauses that are
  present in the corpus. Question 1 reached VCS 0.47 in run 1 against the 0.60
  threshold while containing the correct answer ("California"), so this is a
  verification-threshold/retrieval issue, not a missing document. Not yet
  diagnosed.

## Screenshots

`screenshots/verified.png`, `screenshots/abstained.png`,
`screenshots/general_knowledge.png` — one real Ask response per outcome,
captured from the live UI.

## Reproducing

```
python scripts/batch_ask_check.py --model gemini-flash-lite-latest \
    --pause 10 --question-retries 3 --retry-wait 90
```
