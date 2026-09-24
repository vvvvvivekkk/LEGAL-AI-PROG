# Human-style end-to-end test — LangChain backend, 2026-09-24

Legal AI was used the way a person would use it: every step was a real
click, upload or typed question in the React UI, driven by Playwright
(`run_e2e.py`), against the LangChain API (`lc.api:app` on :8001, LLM_PROVIDER=groq,
model `openai/gpt-oss-120b`) on a **fresh, isolated index**
(`data/lancedb_lc_e2e`, chats in `data/chats_lc_e2e`).

**How correctness was judged.** Before anything was ingested or asked, the five
documents were read and `questions.json` was written with, for each question, the
expected behaviour, the expected answer and the exact source passage. It was
committed first (`2ea519d`) so the expectations could not be adjusted afterwards.
Each recorded answer was then compared against that expected answer and the source
text by hand, and labelled. Labels, per-claim checks and notes are in
`results.json` (built by `build_results.py` from the raw runs). Every number
below comes from `raw_run.json`, `raw_rerun.json` or `replay_fixed.json`.

## Headline

- **WRONG_VERIFIED: 0 of 15.** No wrong or mis-cited answer was ever shown with a
  Verified badge. Every Verified claim was correct, and its cited chunk supports it.
- **The main weakness was false abstention: 4 of 15.** Two were real bugs in the
  citation parser (both fixed, below). One was an over-strict NLI score on a
  correct claim. One was a cross-document retrieval gap.
- **2 of 15 were OTHER.** A cross-document answer was shown as Verified with one
  of its three parts silently missing. A document question was routed to the
  general-knowledge path, and the model refused under a "General knowledge"
  badge. The routing was fixed.
- Ingest, duplicate/Replace, Home counters, Search, Evaluation, chat history and
  document deletion all behaved correctly.

## Summary

| Label | Before fixes | After fixes¹ |
|---|---|---|
| CORRECT_VERIFIED | 3 | 4 |
| WRONG_VERIFIED | **0** | **0** |
| CORRECT_ABSTAIN | 4 | 5 |
| FALSE_ABSTAIN | 4 | 3 |
| CORRECT_GENERAL | 2 | 2 |
| OTHER | 2 | 1 |
| **Total** | 15 | 15 |

¹ Only the three questions touched by fixes (S1, S4, U2) were re-asked, live,
through the UI on a fresh index. The other 12 keep their original result.

By category, before fixes:

| Category | n | Result |
|---|---|---|
| specific | 5 | 2 CORRECT_VERIFIED, 3 FALSE_ABSTAIN |
| cross-document | 2 | 1 FALSE_ABSTAIN, 1 OTHER |
| unanswerable | 3 | 2 CORRECT_ABSTAIN, 1 OTHER |
| general concept | 2 | 2 CORRECT_GENERAL |
| false premise | 2 | 2 CORRECT_ABSTAIN |
| paraphrase | 1 | 1 CORRECT_VERIFIED |

## Documents

| id | File | Format | Pages | Kind |
|---|---|---|---|---|
| D1 | Confidentiality_Agreement_1.pdf | PDF | 2 | NDA, Helu Kabel GmbH (ContractNLI) |
| D2 | NDA_7.pdf | PDF | 2 | NDA dated 28 March 2014 (ContractNLI) |
| D3 | HALO-NDA.pdf | PDF | 2 | NDA, HALO Electronics (ContractNLI) |
| D4 | VIVINT SOLAR, INC. - NON-COMPETITION AGREEMENT.txt | TXT | — | Non-compete amendment (CUAD) |
| D5 | urban_tenancy_act_2019.txt | TXT | — | Statute with Chapter/Section/Clause structure |

SHA-256 hashes are in `documents.json`. D5 is the fictional sample act from
`data/sample/`. `data/corpus/` holds only contracts, so this was the only
Section-structured statute available to exercise SAC.

## Ingest (Ingest page, one file at a time)

| Doc | HTTP | Chunks | Chunking | Time |
|---|---|---|---|---|
| D1 | 200 | 23 | paragraph fallback | 12.61 s² |
| D2 | 200 | 26 | paragraph fallback | 0.95 s |
| D3 | 200 | 9 | paragraph fallback | 1.22 s |
| D4 | 200 | 20 | paragraph fallback | 1.23 s |
| D5 | 200 | 23 | **SAC** (Act/Section parsed) | 0.97 s |

² The first upload includes loading the embedding model into the fresh API process.

Screenshots: `screens/ingest-D1.png` … `screens/ingest-D5.png`.

### Edge cases

| Check | Result |
|---|---|
| Upload D1 again | **409**, "Duplicate document: identical content is already indexed as 'Confidentiality_Agreement_1' (23 chunks)". The warning and the "Replace existing document" button were shown (`screens/edge-duplicate.png`). |
| Click Replace | **200**, 23 chunks, **the same as the first ingest** (0.70 s, `screens/edge-replace.png`) |
| Home counters | UI **5 documents / 101 chunks**; API `/stats` 5 / 101; sum of ingests 101 (`screens/home-after-ingest.png`) |

## Questions (Ask page, each in a new chat)

All 15 returned HTTP 200 on the first attempt. There were no 429/503 errors and
no retries.

| id | Question | Expected | Got | Badge | VCS | Label |
|---|---|---|---|---|---|---|
| S1 | How long is the Helu Kabel confidentiality agreement valid, and is it extended automatically? | 3 years; tacitly +1 year unless terminated 3 months before expiry | Correct text, cited `【…::p18】` | Abstained | — | FALSE_ABSTAIN |
| S2 | Which country's laws govern the NDA dated 28 March 2014? | Spain | "Spain" [NDA_7::p21] | Verified | 1.00 | CORRECT_VERIFIED |
| S3 | What remedy is HALO entitled to if the recipient breaches…? | Equitable remedies incl. injunction | Same [HALO-NDA::p7] | Verified | 1.00 | CORRECT_VERIFIED |
| S4 | When was the Vivint Solar amendment entered into, and who are the parties? | 16 Aug 2017; Vivint Solar, Inc. and Vivint, Inc. | Correct text and citation | Abstained | 0.00 | FALSE_ABSTAIN |
| S5 | Urban Tenancy Act: how long to appeal a rent-authority order, and to which court? | 60 days, District Court | Both correct, cited s10 | Abstained | 0.50 | FALSE_ABSTAIN |
| C1 | Which of the three NDAs has the shortest confidentiality term? | Helu Kabel, 3 years | "INSUFFICIENT_CONTEXT: … Helu Kabel term not included" | Abstained | — | FALSE_ABSTAIN |
| C2 | Governing law of Helu Kabel, HALO and the 28 March 2014 NDA? | Germany (excl. CISG); California; Spain | Germany ✓, California ✓, Spain missing | Verified | 1.00 | OTHER |
| U1 | Liquidated damages for breach of the Helu Kabel agreement? | Not stated → abstain | INSUFFICIENT_CONTEXT | Abstained | — | CORRECT_ABSTAIN |
| U2 | Maximum annual rent increase under the Urban Tenancy Act? | Not stated → abstain | "that isn't a general legal-concept question" | General knowledge | — | OTHER |
| U3 | Geographic area of the Vivint non-compete? | Not stated → abstain | INSUFFICIENT_CONTEXT | Abstained | — | CORRECT_ABSTAIN |
| G1 | What is an indemnity clause? | General answer, labelled | Accurate definition | General knowledge | — | CORRECT_GENERAL |
| G2 | Mutual vs one-way NDA? | General answer, labelled | Accurate explanation | General knowledge | — | CORRECT_GENERAL |
| F1 | Why does the HALO agreement require arbitration in Singapore? | No such clause → abstain/correct | INSUFFICIENT_CONTEXT | Abstained | — | CORRECT_ABSTAIN |
| F2 | Why must a landlord give 180 days' notice before eviction? | It's 90 days → abstain/correct | Abstained, text says "only … ninety-day notice" | Abstained | — | CORRECT_ABSTAIN |
| P1 | If the owner of my flat throws me out by force without permission, how much money am I owed? | Six months' rent, s7(a) | Same [s7:a] | Verified | 1.00 | CORRECT_VERIFIED |

**Per-claim proof check.** Every proof panel of a Verified answer was opened and
screenshotted (`screens/ask-<id>-proof.png`). All 5 claims shown as Verified
(S2, S3, C2 ×2, P1) have a quoted source passage that supports them. For C2's
California claim, the quote is the whole HALO `p7` chunk. Paragraph fallback
merged section 6 (Remedies) and section 7 (Governing Law) into that one chunk, so
it supports the claim, but the panel shows the remedies text first.

**Latency** of `/query` over the 15 questions, measured client-side from the
click to the response: mean **17.30 s**, median **16.08 s**, min 13.59 s,
max 32.83 s (S1, the first question).

## The rest of the app

**Search** (top-5, rerank off). Rank of the gold passage in each column:

| Question | Dense | Lexical | Hybrid |
|---|---|---|---|
| S1 (Helu term) | 1 | 1 | 1 |
| S3 (HALO remedy) | 1 | 1 | 1 |
| S5 (appeal) | 1 | 1 | 1 |

**Evaluation page.** The embedding map shows all 5 documents and 101 points
(`screens/evaluation.png`). The statute and the Vivint amendment form separate
clusters; the three NDAs overlap.

**Chat history.** 15 chats were created. After a page reload, the UI listed 15
and the API listed 15. Deleting the P1 chat returned HTTP 200. After another
reload, the UI showed 14, the API returned 14, and the deleted chat was gone
(`screens/chats-after-reload.png`, `screens/chats-after-delete.png`).

**Delete a document** (`DELETE /documents/HALO-NDA`). HTTP 200, 9 chunks
removed. The Home counters went from **5 / 101 to 4 / 92**
(`screens/home-after-delete.png`). Re-asking S3 (the HALO remedy) then
**abstained** ("…do not contain any information about the specific remedies
HALO is entitled to", `screens/after-delete-S3-answer.png`).

## Failures

### S1 — FALSE_ABSTAIN (bug, fixed)
`screens/ask-S1-answer.png`. The answer was right and cited the right clause,
but Groq wrote the citations with full-width brackets:
`…expiration【Confidentiality_Agreement_1::p18】`. The parser only recognised
`[ ]`, found no claims, and the answer abstained with no VCS. The user saw the
correct text under an "Abstained" badge.

### S4 — FALSE_ABSTAIN (bug, fixed)
`screens/ask-S4-answer.png`. The answer and citation were right, but the source
id comes from the file name `VIVINT SOLAR, INC. - NON-COMPETITION AGREEMENT`,
which contains a comma. The parser supports `[a, b]` lists and split the
citation at that comma. V1 then found neither half in the context, every claim
scored 0, and the answer abstained.

### S5 — FALSE_ABSTAIN (not fixed)
`screens/ask-S5-answer.png`. Both claims are correct and cite Section 10. The
NLI model (roberta-large-mnli) scored "The appeal must be made to the District
Court" at 0.51 against "…to appeal to the District Court within sixty days…".
That claim contributed 0, so VCS was 0.50, below the 0.60 threshold. This is the
same over-strictness already noted in the verification ablation (the threshold
calibration is still outstanding), so it was not changed here.

### C1 — FALSE_ABSTAIN (not fixed)
`screens/ask-C1-answer.png`. One retrieval pool serves the whole question, and it
was taken up by HALO (9 chunks) and NDA_7 (3). The Helu Kabel term clause (`p18`)
never reached the model. The model honestly answered INSUFFICIENT_CONTEXT, so
this is a retrieval-breadth limit for cross-document questions, not a
verification error. A fix would need per-document retrieval for comparison
questions, which is a design change, not a bug fix.

### C2 — OTHER: Verified but incomplete (not fixed)
`screens/ask-C2-proof.png`. Two of the three governing laws are shown as Verified
and are correct. The Spain clause (`NDA_7::p21`) was not retrieved, for the same
reason as C1. The model's third line, "INSUFFICIENT_CONTEXT: The governing law
for the 28 March 2014 NDA is not stated in the provided excerpts.", has no
citation, so it was treated as a malformed line and **not displayed**. The user
sees a Verified answer that looks complete, with no sign that one of the three
agreements was left out. Nothing false was shown, but this is the case closest
to misleading.

### U2 — OTHER: wrong route (bug, fixed)
`screens/ask-U2-answer.png`. "What is the maximum annual rent increase … under
the Urban Tenancy Act?" opens like a definition request and had none of the
document markers, so after the grounded attempt declined it was sent to the
general-knowledge path. The model replied "I'm sorry, but that isn't a general
legal-concept question.", and the UI showed that refusal under the purple
"General knowledge" badge. It should have been a plain abstention.

## Fixes, reruns and replays

The run itself used unchanged code. After it finished, three bugs were fixed,
each in its own commit with a test that fails before the fix and passes after.
Full suites after the fixes: `tests/` 263 passed and 1 skipped; `lc/tests` 113
passed.

| Commit | Bug | Question | Test |
|---|---|---|---|
| `6b6a0f5` | A comma inside a source id split the citation | S4 | `tests/generation/test_parser.py::test_extract_keeps_a_comma_inside_the_source_id` + lc parity case |
| `f7f8dd9` | Full-width citation brackets `【】`/`［］` not recognised | S1 | `tests/generation/test_parser.py::test_full_width_brackets_are_citations` + lc parity case |
| `fb7bf75` | "… under the <Act>?" routed to general knowledge | U2 | `tests/generation/test_general_knowledge.py` (the U2 question) |

Both parsers were fixed (`src/generation/parser.py`, and `lc/generation.py`,
which reuses the new helper). The LangChain parity test covers both new cases.

**Live rerun through the UI** (`raw_rerun.json`, commit `fb7bf75`, fresh index
`data/lancedb_lc_e2e_rerun`, same 5 documents through the Ingest page):

| id | Before | After (live) | Label after |
|---|---|---|---|
| S1 | Abstained, — | Abstained, VCS 0.50 | FALSE_ABSTAIN (different cause) |
| S4 | Abstained, VCS 0.00 | **Verified, VCS 1.00** | CORRECT_VERIFIED |
| U2 | General knowledge (refusal) | **Abstained** | CORRECT_ABSTAIN |

The live S1 rerun did not exercise the bracket fix, because this time the model
used normal brackets. It still abstained, for a different reason. Claim 1, "The
Helu Kabel confidentiality agreement is valid for three years…", was judged
NEUTRAL: chunk `p18` never names Helu Kabel (only the header chunk `p1` does), so
the NLI model would not confirm the entity. That is the same over-strict pattern
as S5.

**Replay of the recorded outputs** (`replay_fixed.py` → `replay_fixed.json`).
Because model output varies, the exact S1 and S4 answers recorded in the run were
passed through the fixed parser and the full V1–V6 chain, with the same chunks
and the real roberta-large-mnli:

| id | In the run | Replayed through the fixed code |
|---|---|---|
| S1 | Abstained, no VCS | **ANSWER, VCS 1.00** (per-claim 1.00, 1.00) |
| S4 | Abstained, VCS 0.00 | **ANSWER, VCS 1.00** (per-claim 1.00, 1.00) |

## Caveats

- 15 questions, 5 short documents, one LLM (Groq `openai/gpt-oss-120b`, whose
  output varies from run to run) and one NLI model. These are observations from
  one run, not rates.
- Labels were assigned by one reviewer against pre-written expectations. The
  expectations were fixed in advance; the judging was not blind.
- D5 is a fictional statute (the only sectioned one available locally).
- The "after" column combines 3 live reruns with 12 original results. It is not a
  full second run.

## Files

`documents.json`, `questions.json` (written before the run), `run_e2e.py` (the
UI driver; `--rerun` for the re-ask), `raw_run.json`, `raw_rerun.json`,
`replay_fixed.py`/`replay_fixed.json`, `build_results.py` → `results.json`,
`screens/` (44 screenshots). Server and driver logs are in the gitignored `logs/`.
