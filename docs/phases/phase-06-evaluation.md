# Phase 6 — Evaluation harness + ablations

**Goal:** produce the actual numbers the paper will report, from real logged runs — never hand-written.

**Tasks**
- `src/evaluation/`: metric implementations — retrieval Precision/Recall/F1, RR%, DRM, Citation Precision/Recall, Faithfulness/Fidelity (from V3), hallucination rate, abstention accuracy, latency.
- Ablation runner: config-driven sweeps over `docs/architecture.md` §5's ablation list (SAC on/off, dense-only vs hybrid, with/without reranking, each of V1–V6 on/off, embedding choice, generation LLM choice).
- Every run writes `experiments/<date>-<name>/config.json` + `results.json`. The Evaluation UI page (phase 7) reads directly from these.
- Calibrate the V5 VCS abstention threshold using held-out results from this phase.

**Definition of done:** at least one full ablation sweep run and logged; Evaluation UI page can render it.
