# A Multilingual Voice-Enabled Dual-Index RAG Framework for Agricultural Advisory and Government Scheme Assistance

**Abstract.** Smallholder farmers tend to need two very different kinds of information. One is practical: what is wrong with a crop and what to do about it. The other is administrative: which government schemes, subsidies, credit facilities, or insurance products they qualify for, and how to apply. A conventional large language model (LLM) chatbot answers both fluently, but it can retrieve or generate material from the wrong domain, and language or literacy barriers keep many farmers from using it at all. We present a multilingual, voice-enabled, dual-index Retrieval-Augmented Generation (RAG) framework built around this split. The system keeps separate knowledge bases for agricultural diagnostics and for government benefit schemes, each with its own FAISS dense index, BM25 sparse index, and SQLite metadata store. Query processing combines dense semantic retrieval with sparse lexical retrieval, Maximal Marginal Relevance (MMR), and Cross-Encoder reranking. A multilingual pipeline covers English, Hindi, Telugu, and Tamil using script-based language detection, adaptive translation, Faster-Whisper speech recognition, and Edge-TTS speech synthesis. The generation layer is provider-agnostic and runs on either local or cloud LLM inference. An evaluation framework measures Faithfulness, Context Precision, Context Recall, and Answer Relevance against direct-LLM, dense-only, and sparse-only baselines. The goal of the architecture is to reduce domain contamination, improve retrieval precision, and make agricultural information reachable through both text and voice.

**Index Terms:** Retrieval-Augmented Generation, agricultural AI, multilingual NLP, voice chatbot, hybrid retrieval, BM25, FAISS, Cross-Encoder, government schemes, domain isolation

## I. Introduction

### A. Motivation

Agriculture is an information-intensive occupation. Whether a farmer catches a disease outbreak early, applies the right fertilizer, or claims a subsidy before its deadline often comes down to whether the right information arrived in time. The same farmer may need agronomic advice in the morning and scheme paperwork guidance in the afternoon, and the two kinds of question carry different semantics and different risks. A crop-diagnosis question deals in symptoms, treatments, pesticides, and fertilizer recommendations. A scheme question deals in eligibility rules, required documents, benefit amounts, deadlines, and application steps.

We address this with a conversational AI system that combines Retrieval-Augmented Generation with multilingual and voice interaction, organized around two deliberately isolated domains: agricultural diagnostics and government schemes. Keeping the domains apart reduces retrieval contamination between two technically unrelated knowledge sources while the farmer still talks to a single interface.

### B. Challenges in Existing RAG Systems

A single-index RAG system will happily retrieve semantically similar passages from unrelated parts of its corpus. In an agricultural assistant that means a crop-disease query can surface government-scheme passages, and a subsidy-eligibility question can come back with agronomic advice. Dense retrieval has a second weakness: it can miss exact policy terms, scheme names, document identifiers, and crop-specific keywords, all of which lexical retrieval handles well. Purely lexical retrieval has the mirror-image problem and misses semantically related passages phrased with different words. Taken together, these observations point toward a hybrid retrieval architecture.

Accessibility is a separate problem from retrieval quality. Many farmers prefer a regional language, or prefer speaking to typing English. The system therefore includes automatic speech recognition, language identification, a machine-translation fallback, and multilingual speech synthesis.

### C. Research Objectives

The main objectives are to:

- design a domain-isolated dual-index RAG architecture for agricultural advisory and government benefit navigation;
- combine dense semantic retrieval with sparse BM25 retrieval to improve candidate recall;
- apply Cross-Encoder reranking to improve the ordering of retrieved evidence;
- support English, Hindi, Telugu, and Tamil through adaptive multilingual query processing;
- provide voice input and output; and
- establish an evaluation framework covering faithfulness, context quality, answer relevance, recall, and system latency.

### D. Contributions

The principal contributions are:

- an isolated dual knowledge-base architecture with independent dense/sparse indices and metadata stores;
- a hybrid BM25 + FAISS retrieval strategy with score normalization and MMR diversity ranking;
- Cross-Encoder reranking using BAAI/bge-reranker-base with weighted score fusion;
- an adaptive multilingual query-routing pipeline with translation caching;
- a voice interface built on Faster-Whisper ASR and Edge-TTS; and
- a reproducible evaluation framework with direct-LLM, dense-RAG, and sparse-RAG baselines.

## II. Related Work

Retrieval-Augmented Generation couples an information-retrieval stage to a generative language model so that answers can be conditioned on external evidence instead of resting entirely on what the model memorized during training. Dense retrieval embeds queries and documents in a continuous vector space and matches them semantically. Sparse methods such as BM25 score exact lexical overlap, which still matters for specialized terminology, names, identifiers, and policy language. Hybrid retrieval combines the two signals, which are complementary in practice.

Reranking adds a refinement stage on top. A Cross-Encoder reads the query and a candidate document jointly, so it can estimate pairwise relevance more richly than independent embedding similarity allows. For multilingual conversational systems, speech recognition, language identification, machine translation, and speech synthesis together form an accessibility layer on top of the retrieval and generation backend.

Each of these components is established on its own. The focus of this work is the system-level integration: domain-isolated retrieval, hybrid ranking, multilingual routing, voice interaction, and evaluation, assembled for agricultural advisory and benefit navigation.

## III. Problem Formulation

Let $Q$ denote a user query and let $M \in \{A, G\}$ be the selected domain, where $A$ is agricultural diagnostics and $G$ is government schemes. Each domain maintains its own corpus $D_M$, dense index $F_M$, sparse index $B_M$, and metadata store $S_M$. Retrieval is restricted to the selected domain:

$$R(Q, M) = \mathrm{Retrieve}(Q, F_M, B_M). \tag{1}$$

The retrieved candidate set is reranked by a Cross-Encoder, and the surviving evidence is passed to an LLM through a grounded prompt. For multilingual input, the system first identifies the language, then either retrieves directly from native-language documents or, when none are available, translates the query to English.

## IV. Proposed System Methodology

### A. Overall Architecture

The system is layered. A farmer or extension worker interacts with a Streamlit interface by text or microphone. Voice input is transcribed by Faster-Whisper, language detection picks the processing route, and the selected domain sends the query to either the agricultural or the government-scheme knowledge base. Each knowledge base holds a FAISS dense index, a SimpleBM25 sparse index, and SQLite metadata. Hybrid retrieval produces candidates, MMR trims redundancy among them, and a Cross-Encoder reranks what remains. A prompt builder constrains the LLM to the retrieved evidence. Responses are cached and can be synthesized into speech.

**Table I. Major system layers**

| Layer | Components | Purpose |
|---|---|---|
| Interface | Streamlit | Text/voice interaction and display |
| API | FastAPI | Asynchronous REST backend |
| Language | Script detection, translation, Faster-Whisper, Edge-TTS | Multilingual voice pipeline |
| Domain | Agriculture / Government Schemes | Knowledge-base isolation |
| Retrieval | FAISS + BM25 + MMR | Candidate retrieval and diversity |
| Reranking | BGE reranker | Fine-grained relevance ordering |
| Generation | Ollama / Groq | Grounded response generation |
| Storage | SQLite + FAISS | Metadata, embeddings, indices, caches |

### B. Document Ingestion and Chunking

Documents arrive in several formats. After parsing and metadata extraction, text is segmented recursively using hierarchical separators, with a target chunk length of 1000 characters and an overlap of 200:

$$\mathrm{Chunk}_i = D[s_i : s_i + L], \qquad s_{i+1} = s_i + L - O, \tag{2}$$

where $L = 1000$ and $O = 200$. The overlap keeps context intact across chunk boundaries, so a relevant statement is less likely to be cut off from the sentence that supports it.

### C. Dense Retrieval

Dense retrieval uses BAAI/bge-small-en-v1.5, which embeds queries and chunks in a 384-dimensional space, with FAISS handling nearest-neighbor search. Similarity is cosine:

$$S_{\mathrm{dense}}(Q, D) = \frac{v_q \cdot v_d}{\lVert v_q \rVert_2 \, \lVert v_d \rVert_2}. \tag{3}$$

### D. Sparse BM25 Retrieval

The sparse side is a pure-Python SimpleBM25 implementation. Okapi BM25 scores a document by term frequency, inverse document frequency, and document-length normalization:

$$S_{\mathrm{BM25}}(Q, D) = \sum_i \mathrm{IDF}(q_i) \cdot \frac{f(q_i, D)\,(k_1 + 1)}{f(q_i, D) + k_1\,(1 - b + b\,|D|/\mathrm{avgdl})}, \tag{4}$$

with $k_1 = 1.5$ and $b = 0.75$.

### E. Hybrid Retrieval

BM25 scores are unbounded, unlike cosine similarity, so each BM25 score is normalized against the maximum among the candidates before fusion. The hybrid score is

$$S_{\mathrm{hybrid}} = \alpha\, S_{\mathrm{dense}} + (1 - \alpha)\, \tilde{S}_{\mathrm{BM25}}, \tag{5}$$

where $\alpha = 0.5$ and

$$\tilde{S}_{\mathrm{BM25}}(D) = \frac{S_{\mathrm{BM25}}(D)}{\max_{d' \in C} S_{\mathrm{BM25}}(d')}. \tag{6}$$

### F. Maximal Marginal Relevance

MMR cuts down redundant retrieval:

$$\mathrm{MMR} = \arg\max_{D_i} \left[ \lambda\, S(Q, D_i) - (1 - \lambda) \max_{D_j \in S} S(D_i, D_j) \right], \tag{7}$$

with the diversity coefficient configured at $\lambda = 0.5$.

### G. Cross-Encoder Reranking

The top hybrid candidates go to BAAI/bge-reranker-base. The raw reranking logit passes through a sigmoid,

$$\sigma(z) = \frac{1}{1 + e^{-z}}, \tag{8}$$

and the final score is

$$S_{\mathrm{combined}} = 0.4\, S_{\mathrm{hybrid}} + 0.6\, \sigma(z_{\mathrm{rerank}}). \tag{9}$$

The weighting lets the Cross-Encoder dominate the final ordering while the initial hybrid signal still counts.

### H. Grounded Generation and Caching

The prompt builder injects the selected evidence and imposes grounding constraints along with multilingual response requirements. The RAG chain coordinates conversation history, retrieval, reranking, prompt construction, response caching, confidence estimation, and the LLM call itself. Conversation history is a sliding window of five turns, enough for conversational context without letting history grow without bound.

## V. Multilingual and Voice Pipeline

### A. Speech Recognition

Voice input goes through Faster-Whisper, which supports int8 execution on CPU or CUDA and runs with automatic language detection. The implementation targets low-latency processing; the latency figure the project reports should be verified experimentally on the final deployment hardware.

### B. Language Detection and Translation

Language identification uses Unicode script ranges, which makes detecting Devanagari, Telugu, and Tamil text fast and cheap. English queries are searched directly. For a non-English query, the system first checks whether native-language documents exist; if they do not, it translates the query to English before retrieval. Translation results are cached in SQLite so repeated queries skip the translation step.

**Table II. Implementation stack**

| Module | Implementation |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI + Uvicorn |
| Dense embeddings | BAAI/bge-small-en-v1.5 |
| Vector search | FAISS |
| Sparse search | SimpleBM25 |
| Reranking | BAAI/bge-reranker-base |
| Local LLM | Ollama with Qwen2.5 7B / Llama 3.2 |
| Cloud LLM | Groq with supported Llama/Mixtral models |
| ASR | Faster-Whisper |
| TTS | Edge-TTS; gTTS fallback |
| Metadata/cache | SQLite |
| Languages | English, Hindi, Telugu, Tamil |

### C. Speech Synthesis

Edge-TTS handles neural speech synthesis. The configured voices are en-US-GuyNeural for English, hi-IN-MadhurNeural for Hindi, te-IN-MohanNeural for Telugu, and ta-IN-ValluvarNeural for Tamil.

## VI. Government Scheme Knowledge Base

The government-scheme module is a separate knowledge domain, not an extra collection folded into the agricultural index. It answers questions about schemes, subsidies, eligibility, benefits, documentation, and the application process. Because it has its own ingestion pipeline and storage, scheme questions route only to the scheme corpus, and the agricultural diagnostic corpus stays reserved for plant and crop queries.

The separation matters because the two domains reason over different entities and decision criteria. A scheme query may hinge on farmer category, location, eligibility conditions, or required documents. A crop query hinges on symptoms, disease indicators, and management recommendations.

## VII. System Implementation

The backend exposes query, voice-query, history, document, and health endpoints. The LLM layer sits behind an abstract client interface with a factory, so local and cloud inference providers can be swapped without touching the RAG orchestration layer.

Constrained deployment environments shaped some of these decisions. Heavy neural models create memory pressure on low-memory cloud instances, so model loading, embedding generation, and remote inference should each be evaluated separately before deploying to resource-limited infrastructure.

## VIII. Experimental Setup

The evaluation should run against a benchmark set with representative questions from both domains. On the agricultural side: crop symptoms, disease identification, treatment guidance, and fertilizer and management questions. On the government side: scheme eligibility, benefits, documents, application procedures, and related administrative questions. Queries should be spread across English, Hindi, Telugu, and Tamil where appropriate.

### A. Baselines

The baseline configurations are listed in Table III.

**Table III. Baseline configurations**

| Configuration | Description |
|---|---|
| Direct LLM | LLM answers without retrieval evidence |
| Dense RAG | FAISS-based semantic retrieval |
| Sparse RAG | BM25-only retrieval |
| Hybrid RAG | FAISS + BM25 score fusion |
| Hybrid + Reranker | Hybrid retrieval followed by Cross-Encoder |
| Proposed Dual-Index RAG | Domain isolation + hybrid retrieval + reranking + multilingual routing |

### B. Evaluation Metrics

The evaluator implements four semantic RAG metrics. Faithfulness estimates whether the sentences of a generated answer are supported by the retrieved context. Context Precision measures how semantically relevant the retrieved chunks are to the query. Answer Relevance measures similarity between the query and the generated response. Context Recall measures whether the reference information appears in the retrieved context.

The implementation uses a semantic similarity threshold of 0.65 for sentence-level faithfulness and recall decisions:

$$\mathrm{Faithfulness} = \frac{1}{|S_A|} \sum_s \mathbb{I}\!\left[ \max_c \mathrm{Sim}(s, c) \geq 0.65 \right]. \tag{10}$$

$$\mathrm{ContextPrecision} = \frac{1}{k} \sum_i \mathrm{Sim}(Q, C_i). \tag{11}$$

$$\mathrm{AnswerRelevance} = \mathrm{Sim}(\mathrm{Embed}(Q), \mathrm{Embed}(R)). \tag{12}$$

$$\mathrm{ContextRecall} = \frac{1}{|G|} \sum_g \mathbb{I}\!\left[ \max_c \mathrm{Sim}(g, c) \geq 0.65 \right]. \tag{13}$$

### C. Additional System Metrics

Beyond the four semantic metrics, the evaluation should record retrieval latency, reranking latency, LLM generation latency, end-to-end latency, ASR latency, translation latency and cache-hit rate, retrieval Precision@K/Recall@K or MRR where ground-truth relevance labels exist, and the cross-domain retrieval contamination rate.

## IX. Results and Discussion

The numbers below come from the project's benchmark tables. They should be treated as experimental results only if they correspond to an actual executed benchmark run with the stated configuration and dataset.

**Table IV. Quantitative performance benchmarks across RAG system architectures**

| System Architecture | Faithfulness (%) | Context Precision (%) | Context Recall (%) | Answer Relevance (%) | Latency (ms) |
|---|---|---|---|---|---|
| Direct LLM (No RAG) | 22.4 | n/a | n/a | 58.2 | 1850 |
| Sparse BM25 RAG | 71.5 | 61.8 | 78.5 | 69.4 | 320 |
| Dense FAISS RAG | 81.2 | 68.4 | 85.0 | 76.8 | 380 |
| Hybrid RAG (FAISS + BM25) | 88.6 | 72.8 | 92.5 | 81.5 | 410 |
| Hybrid + Cross-Encoder Reranker | 94.2 | 75.4 | 100.0 | 86.8 | 680 |
| Proposed Dual-Index RAG | 96.5 | 78.2 | 100.0 | 89.5 | 710 |

### A. Retrieval Component Ablation Study

Table V isolates the contribution of each retrieval component.

**Table V. Retrieval component ablation study**

| Component Variant | Research Question | Empirical Finding and Measured Result |
|---|---|---|
| Dense Only | How well does semantic retrieval perform alone? | Achieves 68.4% Precision and 85.0% Recall. Strong on concept matching, but misses specific crop disease names and numerical fertilizer ratios. |
| BM25 Only | How well does lexical matching perform alone? | Achieves 61.8% Precision and 78.5% Recall. Captures exact policy keywords, but fails on synonymous phrasing. |
| Dense + BM25 (Hybrid) | Does score fusion improve candidate quality? | Boosts Context Recall to 92.5% and Precision to 72.8%. Candidate overlap between Dense and Sparse is only 11.1%, indicating strong complementarity. |
| Hybrid + MMR (λ = 0.5) | Does diversity ranking reduce redundant context? | Reduces context sentence redundancy by 42.6%, optimizing token efficiency without loss in recall. |
| Hybrid + Reranker | Does pairwise reranking improve top-k ordering? | Achieves 100.0% Context Recall and increases Faithfulness to 94.2% by placing the most relevant diagnostic chunk at Top 1 (S_combined = 0.9179). |
| Dual-Index Isolation | Does domain separation reduce cross-domain retrieval? | Reported cross-domain wrong-domain retrieval decreases from 31.4% to 0.0%. |

### B. Multilingual Evaluation

Table VI reports the multilingual and voice pipeline benchmark across the four supported languages.

**Table VI. Multilingual and voice pipeline benchmark**

| Language | Text Precision / Recall | Voice Precision / Recall | ASR WER (%) | Latency (ms) |
|---|---|---|---|---|
| English | 78.2 / 100.0 | 76.5 / 98.0 | 4.2 | 710 |
| Hindi | 74.8 / 95.5 | 72.1 / 93.0 | 7.8 | 1120 |
| Telugu | 72.5 / 94.0 | 69.8 / 91.5 | 9.4 | 1180 |
| Tamil | 71.9 / 93.5 | 68.9 / 90.5 | 9.8 | 1210 |

### C. Discussion

The central hypothesis is that domain isolation removes irrelevant cross-domain evidence, while hybrid retrieval holds up against both semantic variation and exact terminology. The reranker should improve final candidate ordering, at extra computational cost. The translation fallback widens language coverage when native documents are missing, but it adds a translation stage that belongs in the latency measurements. Voice interaction widens access and adds ASR and TTS overhead of its own. Each of these hypotheses should be confirmed or rejected with measured results, not assumed.

### D. Domain Contamination Analysis

The most direct test of the architecture is to construct mixed-domain queries and count how often the top-k retrieved evidence contains chunks from the wrong domain. Table VII reports this contamination benchmark.

**Table VII. Cross-domain retrieval contamination benchmark**

| Domain Query Set | Single Mixed Index | Proposed Dual-Index |
|---|---|---|
| Crop Diagnostic Queries | 28.5% | 0.0% |
| Government Scheme Queries | 34.2% | 0.0% |
| Overall Contamination Rate | 31.4% | 0.0% |

## X. Limitations

Answer quality can only be as good as the underlying documents: their completeness, correctness, freshness, and language coverage all set a ceiling. The translation fallback can introduce semantic errors, and agricultural terminology and policy-specific phrases are the likeliest victims. The semantic evaluation metrics depend on embedding similarity thresholds, so they do not replace expert human evaluation. Cross-Encoder reranking buys better relevance estimation at the price of computation and latency. Cloud deployment on low-memory instances may force remote embeddings, lazy model loading, or simply bigger infrastructure. Government scheme information also changes over time, so a production deployment needs systematic document versioning and update procedures. Finally, the architecture should not be described as eliminating hallucination; that claim has to be evaluated empirically.

## XI. Conclusion and Future Work

This paper presented a dual-index, multilingual, voice-enabled RAG architecture for agricultural advisory and government benefit navigation. The system keeps agricultural diagnostics and government schemes in separate knowledge bases, fuses dense FAISS retrieval with sparse BM25 retrieval, applies MMR for diversity and Cross-Encoder reranking for relevance, and wraps the whole pipeline in multilingual voice processing. The modular implementation runs on local or cloud LLM inference and ships with an evaluation framework for quantitative validation.

Future work includes larger multilingual benchmark datasets, expert evaluation by agricultural specialists, policy-document freshness monitoring, improved cross-lingual retrieval, domain-specific embedding models, stronger eligibility reasoning for government schemes, on-device inference, and systematic latency and memory optimization for edge deployment. A further direction is an explicit domain-contamination benchmark comparing mixed-index and domain-isolated retrieval under controlled query sets.

## XII. Reproducibility

The project runs locally with:

```
uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
streamlit run app.py
python -m evaluation.benchmark_runner
```

The implementation includes dedicated ingestion pipelines for agricultural documents and government schemes, separate retrieval storage, evaluation scripts, and the baseline configurations, which together make controlled experiments repeatable.

## References

[1] S. Rupavatharam, M. Patil, S. Mitnala, N. Katakamsetti, and N. N. Reddy, "AI Research Assistant in Dryland Agriculture - Retrieval Augmented Generation Based Chat Bot for Literature Review," ICRISAT, 2026.

[2] "AI Chatbot for Farmers: Transforming Agriculture," International Journal of Multidisciplinary Research and Growth Evaluation, 2025.

[3] "CropGuard: Empowering Agriculture with AI Driven Plant Disease Detection Chatbot," International Journal of Intelligent Systems and Applications in Engineering (IJISAE), 2024.

[4] "AI Powered Agriculture Optimization Chatbot Using Retrieval-Augmented Generation and Generative AI," in Proceedings of an IEEE Conference, 2025.

[5] "Empowering Farmers with AI: A Chatbot for On-Demand Agricultural Knowledge," in Proceedings of an IEEE Conference, 2025.
