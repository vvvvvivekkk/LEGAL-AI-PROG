# Phase 5 — Verification chain (V1–V6) + Proof Object

**Goal:** the core contribution. Build and test each layer independently, in order, since later layers consume earlier ones' outputs. See `docs/architecture.md` §4 for what each layer checks.

**Tasks, in order**
1. **V1 Citation Existence** — deterministic lookup; test with a hand-crafted fabricated citation id.
2. **V2 Entailment (NLI)** — local NLI model (roberta-large-mnli or legal-domain equivalent) classifying (claim, cited chunk) pairs; test with a hand-crafted contradicting passage.
3. **V3 Atomic Claim Fidelity** — decompose answers into atomic claims, verify each independently, produce a per-claim fidelity score.
4. **V4 Self-Consistency** — resample generation / vary retrieval, flag claims that don't recur.
5. **V5 VCS aggregation + abstention** — combine V1–V4 into one calibrated Verification Confidence Score; define and document the aggregation formula; below-threshold → abstain/clarify instead of answering. Calibrate the threshold on a held-out set once real data exists (phase 6).
6. **V6 Proof Object** — structured output: `claim → supporting chunk id(s) → verbatim quoted span → per-layer verdict → VCS contribution`, serializable to JSON for the UI's proof viewer.

**Definition of done:** each layer has its own unit tests with synthetic pass/fail cases; the full chain runs end-to-end on a phase-4 generated answer and produces a VCS + Proof Object.
