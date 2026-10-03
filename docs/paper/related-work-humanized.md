# Related work

From the comparison table in `README.md`. Positioning claims about this system
are backed by `results.md`; claims about prior work are from the cited papers.

| Work | What it contributes | Gap it leaves | How this system relates |
|---|---|---|---|
| Reuter et al., *Towards Reliable Retrieval in RAG Systems for Large Legal Datasets*, NLLP 2025 | Summary-Augmented Chunking | No claim or citation verification | SAC is adopted directly and measured here (`results.md` §2); the verification chain is added on top |
| Figueiredo et al., *Grounded in Law* (EscavAI), PROPOR 2026 | Citation auditing | Limited case-law coverage, weak retrieval | Citation existence is V1, the cheapest layer, not the whole answer; paired with hybrid retrieval |
| Maghakian et al., *Embedding-Free RAG*, EMNLP 2025 | LLM-driven retrieval | An LLM call per query is expensive | Hybrid dense + keyword retrieval, with the LLM reserved for generation |
| Niu et al., *RAGTruth*, arXiv 2024 | Hallucination benchmark | Not legal-domain | Informs the error taxonomy; the probes in `results.md` §4.2 are a local analogue, not a run of RAGTruth |
| Pipitone & Alami, *LegalBench-RAG*, arXiv 2024 | Legal RAG benchmark | Evaluation only, no end-to-end system | Named as the intended evaluation corpus; **not yet run** (`results.md` §6) |
| Magesh et al., *Hallucination-Free? Assessing AI Legal Research Tools*, JELS 2025 | Empirical evaluation of commercial legal AI | — | Motivates gating answers rather than scoring them |

## The gap this work addresses

Each prior system improves one stage. Reuter improves chunking but ships no
verification. EscavAI audits citations but treats citation existence as the
whole check. RAGTruth benchmarks hallucination without a system that acts on
the finding. None of them gate the answer.

We claim **integration plus a gate** as the contribution: four independently
studied checks (citation existence, entailment, atomic-claim fidelity,
self-consistency) composed into a single calibrated score that decides
whether the user sees the answer at all, with a per-claim audit trail.

The ablation in `results.md` §4 supports that framing and also sharpens it:
the detection layers are largely redundant with one another on the
perturbations tested, while the **gate** (V5) is the only component whose
removal lets a known-bad claim reach the user. The novelty is therefore less
"four detectors" than "detection wired to refusal".

**TODO:** a literature pass for work published since the table was written,
particularly on calibrated abstention in RAG, which §5 of `results.md` shows is
this system's weakest measured area.
