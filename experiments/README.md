# Experiments: what each run is and how to read it

Every folder here is one experiment. A run is a folder containing a `config.json`
(its settings) and/or a `results.json` (what it measured). The **Evaluation page**
of the app lists every run it finds here, in name order, with a one-line
description and its headline numbers. Those numbers are read from the files; none
are typed in by hand. This page explains each run in more detail.

Nothing here is regenerated when you use the app. These are records of tests that
were run once, and they stay as they were so the paper's numbers can be checked
against them.

---

## How to read the Evaluation page

### Embedding space (top of the page)

- Every chunk in the **current index** is one dot. Its 384-number embedding is
  squashed to 2D with PCA, so chunks with similar meaning land near each other.
- Each document gets its own colour and marker shape. The legend lists every
  document **followed by its number of chunks**, in a separate column. When you
  copy the page as text, the two run together: `2_waycda12` is the document
  `2_waycda` with 12 chunks, and `…391491047345` is `…3914910473` with 45.
- This section shows whatever you have ingested **right now**. It changes when you
  add or delete documents. The experiment cards below it never change.
- A name like `17.04.01%20BPS%20Non-Disclosure…` means the file was saved from a
  browser with `%20` in place of spaces. The app uses the file name as the
  document's id, so the `%20` shows up everywhere. Rename the file with real
  spaces (or underscores) before uploading if you want a clean name.

### Retrieval cards (Precision / Recall / F1 / Retrieval rate)

Only retrieval runs have these four numbers. Each run asks 10 labelled questions,
takes the top **k = 5** chunks for each, and compares them with the 14 "gold"
clauses that actually answer the questions.

| Number | Meaning | Example |
|---|---|---|
| **Precision** | Of the 5 chunks returned, how many were gold | 28% ≈ 1.4 of 5 on average |
| **Recall** | Of the gold clauses, how many were found | 100% = none missed |
| **F1** | One number combining the two: 2PR / (P + R) | 41.7% |
| **Retrieval rate** | Share of questions with at least one gold clause in the top 5 | 100% = every question |

The line on the right, for example `dense · rerank true · k5/N50`, is the setting:
the search method (dense vectors, or hybrid vectors + keywords), whether the
cross-encoder reranker was used, **k** = chunks kept, and **N** = candidates
fetched before reranking.

Why precision looks low: most questions have only one or two gold clauses, but
k = 5 chunks are always returned. So even a perfect search scores at most 20–40%
precision. Recall and F1 are the numbers to compare.

### All other cards

They show that test's own headline numbers, explained below.

---

## The runs

### `2026-09-20-e2e-corpus-check`: first smoke test on real contracts

- **What:** indexed two real contracts (1,444 chunks, both paragraph-chunked) and
  looked at what dense, keyword and hybrid search return for 10 queries.
- **Why there are no scores:** there were no labelled answers yet, so this only
  checked that ingestion and search work on real files. The top results per query
  are in `results.json`; `report.md` has the notes.

### `2026-09-23-ablations/retrieval/*`: retrieval and chunking ablation (8 runs)

- **What:** every combination of chunking (**SAC** or **paragraph fallback**) ×
  search (**dense** or **hybrid**) × reranker (**on** or **off**), on the 5
  synthetic statutes in `data/sample/` with the 10 labelled questions in
  `data/eval/`.
- **Folder names:** `sac-hybrid-rerank` = SAC chunking, hybrid search, reranker on,
  and so on.
- **Result:** SAC gets F1 **41.7%** in three of four settings (39.2% with hybrid and
  no reranker). Paragraph chunking gets **33.3%** in all four. Recall and
  retrieval rate are about 100% everywhere: the question set is too easy to tell
  the search methods apart, but SAC is more precise because its chunks are smaller.
  Reranking added 6.7–12.8 s per question.
- **Paper:** Table I and Fig. 6. More detail in `retrieval/README.md`.

### `2026-09-23-ablations/verification`: verification ablation (summary + 7 arms)

- **What:** 10 answers were generated once and cached. The same answers were then
  checked 7 times, each time with one of the checks V1–V6 switched off. This
  isolates what each check contributes, because the answers themselves don't
  change.
- **Corrupted claims:** two "probes" made 28 claims that must never be shown.
  Fabricated citation (14) replaced every citation with a chunk id that was never
  retrieved. Mismatched claim (14) swapped in a claim from a different question
  while keeping the citation.
- **The card numbers:**
  - **Mean VCS** is the average Verification Confidence Score over the 10 clean answers.
  - **Answered / refused** is how many of the 10 cleared the 0.60 threshold.
  - **Bad claims shown** is how many of the 28 corrupted claims reached the user.
- **The summary card** (`verification`) holds all arms together: bad claims shown
  are 0/28 with the full chain and 28/28 without V5.

| Arm | Switched off | Mean VCS | Answered / refused | Bad shown |
|---|---|---|---|---|
| `full_chain` | nothing | 0.768 | 7 / 3 | 0 / 28 |
| `minus_v1` | citation-exists check | 0.768 | 7 / 3 | 0 / 28 |
| `minus_v2` | NLI entailment | 0.813 | 8 / 2 | 0 / 28 |
| `minus_v3` | atomic fidelity | 0.777 | 7 / 3 | 0 / 28 |
| `minus_v4` | self-consistency | 0.723 | 7 / 3 | 0 / 28 |
| `minus_v5` | **the score gate** | 0.768 | **10 / 0** | **28 / 28** |
| `minus_v6` | proof object | 0.768 | 7 / 3 | 0 / 28 |

- **Reading it:**
  - Removing any single detector (V1–V4) still blocks every bad claim, because
    the detectors overlap.
  - Removing the **gate (V5)** lets all 28 through: the detectors still score
    them zero, but nothing acts on the score.
  - The 3 refusals in the full chain are false refusals. All 10 questions are
    answerable, and the NLI model was too strict on 3 of them.
- **Paper:** Table II and Fig. 7. More detail in `verification/README.md`.

### `2026-09-24-human-e2e`: end-to-end test through the web app

- **What:** the app used like a person would, with real uploads, typed questions
  and clicks, driven by Playwright on the LangChain backend.
  - **Documents:** 5 real ones. Three ContractNLI NDAs, a CUAD non-compete and the
    tenancy statute.
  - **Questions:** 15, whose expected answers and source passages were written and
    committed **before** anything was uploaded.
- **Card numbers:**
  - **Wrong but verified: 0 / 15.** No wrong answer was ever shown as Verified;
    this is the key safety number.
  - **Correct and verified: 3 / 15.**
  - **False refusals: 4 / 15.** Two were parser bugs, fixed afterwards; one was the
    NLI model being too strict; one was a comparison question whose third document
    was never retrieved.
  - **Mean time per question: 17.3 s.**
- **Other labels:** 4 correct refusals, 2 general-knowledge answers labelled
  correctly, 2 "other". The card shows the results **before** the fixes. After them,
  correct-verified is 4 and false refusals are 3.
- **Paper:** Section III-E, Table III and Fig. 8.
- **Files:** `report.md` has every question with its expected and actual answer;
  `screens/` has 44 screenshots.

### `batch_ask_check`: early batch test on real contracts

- **What:** 10 ContractNLI agreements uploaded, 5 specific and 5 general questions
  asked through the API, with Gemini as the model.
- **The card:** shows only the **last** of three runs, 2 verified, 4 general
  knowledge and 4 backend errors. The errors were free-tier rate limits, not app
  failures. `report.md` combines all three runs, and that combined picture is what
  the paper reports (Section III-D).

### `langchain_port/*`: LangChain vs plain Python

The same pipeline was built twice: `src/` (plain Python) and `lc/` (LangChain,
now the default). These runs check that they behave identically.

| Run | What it compared | Result |
|---|---|---|
| `langchain_port/retrieval/python` and `/langchain` | The retrieval test above (SAC, hybrid, rerank) on each version | Both F1 41.7%, recall 100%, same top 5 in the same order for all 10 questions |
| `langchain_port/safety/python` and `/langchain` | The cached answers and 28 corrupted claims through each version's full chain | Both mean VCS 0.768, 7 answered / 3 refused, 0 / 28 bad shown |
| `langchain_port/latency` | Time per question, 20 requests each, alternating | Python 13.86 s, LangChain 14.50 s (+4.6%, within the LLM's run-to-run variation) |

`langchain_port/report.md` has the full comparison and the decision to switch.

### Folders that are not runs

- **`ui_reskin/`:** before and after screenshots of the orange-and-white redesign.
  It has no `config.json` or `results.json`, so the Evaluation page doesn't list it.
- **`*/screens`, `*/screenshots`:** evidence images for the runs above.

---

## Adding a new run

Make a folder here with a `config.json` and `results.json`. A retrieval run written
by `python -m src.evaluation.run_retrieval_eval` appears with the four
retrieval numbers. Other result shapes are recognised in
`src/evaluation/results_store.py` (`describe_run`). Add a case there, and a
section in this file, when you add a new kind of experiment.
