# Method

Drawn from `docs/architecture.md` and `docs/architecture-production.md`. No
numbers appear in this section; all measurements live in `results.md`.

## 1. Problem

LLMs answering legal questions hallucinate in three distinct ways: invented
facts, misattributed authority, and citations to provisions that do not say
what is claimed. Retrieval-augmented generation reduces but does not eliminate
this. Three failures survive plain RAG:

1. Fixed-size chunking severs a clause from the section that gives it meaning.
2. Retrieval optimises for *similarity*, not for whether a passage *supports*
   the claim the model went on to make.
3. Nothing checks the generated answer against the retrieved evidence before
   the user sees it.

Prior work improves one of these in isolation (see `related-work.md`). This
system addresses the full path from document to gated answer.

## 2. Pipeline

```
ingest → SAC chunk → embed → LanceDB (hybrid vector + FTS)
       → rerank → citation-forced generation
       → V1–V6 verification chain → VCS → answer or abstain (+ proof object)
```

### 2.1 Ingestion and chunking

Documents are loaded (PDF via `pypdf`, or plain text), cleaned, and parsed for
legal structure. Two chunking strategies coexist:

- **Summary-Augmented Chunking (SAC)** for structured instruments with an
  Act / Chapter / Section hierarchy. Each chunk carries a contextual summary of
  the section it belongs to, and that summary is prepended to the chunk text
  *before embedding*, so the vector encodes both the local clause and its
  governing context.
- **Fallback paragraph chunking** for documents with no parseable legal
  structure — which is what real-world contracts (NDAs, merger agreements) are.
  The system detects this and switches automatically rather than forcing a
  structure parser onto a document that has none.

Documents are fingerprinted by SHA-256 at ingest; a re-upload of identical
content, or of a different file with a colliding source id, is refused rather
than silently duplicated.

### 2.2 Indexing and retrieval

LanceDB holds dense vectors and a full-text index on the same table — embedded
and file-based, so there is no separate server and no hand-wired FAISS + BM25
pair. Retrieval fuses vector and keyword results (RRF), then re-scores the
fused candidate pool with a cross-encoder and truncates to *k*.

The candidate pool depth *n* is deliberately much larger than *k*: a
cross-encoder can only promote passages the bi-encoder actually fetched, so a
shallow pool silently caps achievable quality regardless of reranker strength.

**Neighbor expansion.** A clause can be split across adjacent chunks, where the
continuation ranks poorly in isolation because on its own it names neither the
subject nor the action. Relevance ranking cannot recover it; the signal that it
belongs in the context is *adjacency*. `RetrievalConfig.neighbor_window` pulls
each selected chunk's neighbours from the same document into the context, in
document order, unscored, after truncation to *k* — so expansion never evicts a
ranked result. It is disabled by default; see `results.md` §3 for the measured
precision cost.

### 2.3 Citation-forced generation

The generation prompt constrains the model two ways: it may use only the
supplied context, and every factual claim must terminate in a citation to the
chunk id(s) supporting it. One claim per line, citation-terminated. This format
is what makes verification tractable — the parser maps each claim to its
evidence deterministically, with no attribution guesswork. If the context
cannot support an answer the model must emit a single abstention marker.

Backends (Claude, OpenAI, Gemini) sit behind a thin adapter interface.

### 2.4 The verification chain

Each generated answer passes through six layers in order, each consuming the
last:

| Layer | Checks | Nature |
|---|---|---|
| V1 | every cited chunk id exists in the retrieved context | deterministic hard gate |
| V2 | the cited passage entails the claim (NLI) | model-based hard gate on CONTRADICTS |
| V3 | the claim decomposed into atoms, each checked for entailment | model-based, graded |
| V4 | the claim recurs across independent resamples | model-based, graded, optional |
| V5 | V1–V4 aggregated into one Verification Confidence Score; gates answer vs abstain | aggregation + decision |
| V6 | structured Proof Object: per-claim verdicts, quoted spans, score contributions | serialisation |

V1 and a V2 CONTRADICTS verdict are hard gates that zero a claim outright — a
fabricated citation or a refuting source cannot be rescued by fidelity or
consistency. Otherwise the claim score is a weighted mean of the entailment,
fidelity, and consistency components. A layer that did not run has its weight
excluded from the normalisation rather than scored as zero, so an answer is
never penalised for a layer that was skipped.

The answer-level VCS is the mean of per-claim scores. Below threshold, the
system abstains and says so.

### 2.5 Abstention and the general-knowledge fallback

Abstention is the designed outcome when the documents cannot support an answer.
One case is carved out: a question asking for a general legal concept the
corpus was never going to define is answered from model knowledge instead,
returned with no VCS, no citations, and a distinct label in the UI. The
classifier is conservative — any marker tying a question to the indexed
documents keeps it on the verified path, where abstaining is the honest answer.

### 2.6 Proof object

Every answer ships a structured trace: per claim, the cited chunk ids, the
quoted supporting span, each layer's verdict, and the claim's contribution to
the VCS. This is the auditable artifact — not a single "hallucinated: yes/no"
score, but a decomposed record of *why* an answer was trusted or refused.

## 3. Implementation

Python. LanceDB for the index, sentence-transformers for embeddings and the
cross-encoder, a RoBERTa MNLI model for entailment. FastAPI backend, React UI.
Embedding and LLM backends are swappable behind interfaces.

**TODO:** exact model identifiers, parameter counts, and hardware for the
reproducibility paragraph.
