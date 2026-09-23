# Paper draft (phase 8)

Working draft assembled from logged runs only. Every number in `results.md`
traces to a directory under `/experiments`; nothing here is hand-written or
estimated. If a number has no logged run behind it, it is marked as **not yet
measured** rather than filled in.

| file | contents | source |
|---|---|---|
| `method.md` | system description | `docs/architecture.md`, `docs/architecture-production.md` |
| `results.md` | tables + findings | `experiments/2026-09-23-ablations/` |
| `related-work.md` | positioning | `README.md` comparison table |
| `qualitative.md` | worked examples | logged proof objects + `experiments/batch_ask_check/` |
| `paper.pdf`, `paper.docx` | full two-column article (author block left blank) | all of the above |
| `figures/` | Figs. 1–7 of the article | `make_figures.py` |
| `make_figures.py` | regenerates every figure from the logged result files and UI screenshots | `experiments/2026-09-23-ablations/`, `experiments/ui_reskin/after/` |

## Status

The full article is in `paper.pdf`. Regenerate the figures with
`python docs/paper/make_figures.py`. The markdown files are the working
notes it was written from. Sections marked **TODO** need either a run that has not been
done yet or a judgement call from the author — they are deliberately empty
rather than plausibly filled.
