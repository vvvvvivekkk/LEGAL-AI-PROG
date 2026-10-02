# Criminal-law demo pack

27 files of real Indian criminal law, one topic per file (theft, murder, bail, cheque
bounce, …). Each file is written in the format the structure parser reads, so it is split by
Section (SAC) and every answer cites a real section, such as `ipc_theft::s379`. Upload the
files on the Ingest page (all of them, or only the topics you need), then ask the questions
below on the Ask page.

| File | Act | Sections | Sections in file | Chunks |
|---|---|---|---|---|
| `ipc_general_exceptions.txt` | Indian Penal Code, 1860 | 76–106 | 31 | 31 |
| `ipc_abetment_conspiracy_and_attempt.txt` | Indian Penal Code, 1860 | 107–120B, 511 | 18 | 18 |
| `ipc_unlawful_assembly_and_rioting.txt` | Indian Penal Code, 1860 | 141–160 | 23 | 26 |
| `ipc_false_evidence.txt` | Indian Penal Code, 1860 | 191–229A | 46 | 46 |
| `ipc_murder_and_culpable_homicide.txt` | Indian Penal Code, 1860 | 299–311 | 14 | 14 |
| `ipc_hurt_and_grievous_hurt.txt` | Indian Penal Code, 1860 | 319–338 | 22 | 22 |
| `ipc_wrongful_restraint_and_confinement.txt` | Indian Penal Code, 1860 | 339–348 | 10 | 10 |
| `ipc_criminal_force_and_assault.txt` | Indian Penal Code, 1860 | 349–358 | 14 | 15 |
| `ipc_kidnapping_and_abduction.txt` | Indian Penal Code, 1860 | 359–374 | 21 | 24 |
| `ipc_theft.txt` | Indian Penal Code, 1860 | 378–382 | 5 | 5 |
| `ipc_extortion.txt` | Indian Penal Code, 1860 | 383–389 | 7 | 7 |
| `ipc_robbery_and_dacoity.txt` | Indian Penal Code, 1860 | 390–402 | 13 | 13 |
| `ipc_criminal_breach_of_trust_and_misappropriation.txt` | Indian Penal Code, 1860 | 403–409 | 7 | 7 |
| `ipc_receiving_stolen_property.txt` | Indian Penal Code, 1860 | 410–414 | 5 | 5 |
| `ipc_cheating.txt` | Indian Penal Code, 1860 | 415–424 | 10 | 10 |
| `ipc_mischief.txt` | Indian Penal Code, 1860 | 425–440 | 16 | 16 |
| `ipc_criminal_trespass.txt` | Indian Penal Code, 1860 | 441–462 | 22 | 22 |
| `ipc_forgery_and_counterfeit_currency.txt` | Indian Penal Code, 1860 | 463–477A, 489A–489E | 21 | 21 |
| `ipc_marriage_offences_and_cruelty_498a.txt` | Indian Penal Code, 1860 | 493–498A | 7 | 7 |
| `ipc_defamation.txt` | Indian Penal Code, 1860 | 499–502 | 4 | 4 |
| `ipc_criminal_intimidation_and_insult.txt` | Indian Penal Code, 1860 | 503–510 | 8 | 8 |
| `crpc_arrest.txt` | Code of Criminal Procedure, 1973 | 41–60A | 23 | 28 |
| `crpc_fir_and_investigation.txt` | Code of Criminal Procedure, 1973 | 154–176 | 26 | 57 |
| `crpc_bail.txt` | Code of Criminal Procedure, 1973 | 436–450 | 18 | 31 |
| `ni_act_cheque_bounce.txt` | Negotiable Instruments Act, 1881 | 138–148 | 13 | 20 |
| `evidence_act_confessions.txt` | Indian Evidence Act, 1872 | 24–30 | 7 | 7 |
| `evidence_act_burden_of_proof.txt` | Indian Evidence Act, 1872 | 101–114A | 18 | 19 |
| **Total** | | | **429** | **493** |

## Where the text comes from

The section text is from `IndiaLaw.db` in the public GitHub repository
[civictech-India/Indian-Law-Penal-Code-Json](https://github.com/civictech-India/Indian-Law-Penal-Code-Json),
which holds Indian Acts section by section as published on India Code.
`scripts/build_crime_pack.py` writes these files from it. The wording of each section is
unchanged except for whitespace and the source website's amendment footnotes (a digit glued
to a word, such as "thirty1", and notes such as "1 Criminal Law (Amendment) Act, 2018"),
which are removed. Chapter names are written out in full; where a file holds part of a
chapter, the name says which part.

**Legal status.** The Indian Penal Code, the Code of Criminal Procedure and the Indian
Evidence Act were replaced on 1 July 2024 by the Bharatiya Nyaya Sanhita, 2023, the
Bharatiya Nagarik Suraksha Sanhita, 2023 and the Bharatiya Sakshya Adhiniyam, 2023. These
files are those Acts as they stood before that date. The Negotiable Instruments Act, 1881 is
still in force. This pack is for demonstrating the system, not a source of current law.

**Clause letters.** The source lost the official (1)/(a) labels inside sections. A section
longer than 180 words is therefore split into parts at paragraph or sentence boundaries,
written as `Clause (a)`, `Clause (b)`, …: these letters number the parts in order and are
**not** the Act's own clause numbers. Section numbers are always the real ones. Short parts
keep every chunk within what the embedding model (about 256 tokens) and the NLI model (512
tokens) can read.

**Already uploaded the earlier 3-file version?** Delete `indian_penal_code_1860_crimes`,
`code_of_criminal_procedure_1973_arrest_fir_bail` and
`negotiable_instruments_act_1881_cheque_bounce` on the Ingest page first; otherwise every
section is indexed twice.

## Questions to ask

[`docs/questions.md`](../../docs/questions.md) lists all 91 questions by topic, with the
expected answer and section for each, a short list for a live demo, questions that should be
refused, and how to word questions. `questions.json` holds the same list, and
`scripts/check_demo_questions.py` asks all of them through a running backend and reports the
result for each. The expected answers were checked against the text of the cited section;
they have not all been run through the full pipeline (LLM and NLI) yet.

**Checked when the pack was built:** every file is parsed into all of its sections (no
paragraph fallback, no duplicate chunk ids, longest chunk 177 words), and the LangChain
splitter produces the same 493 chunk ids as the plain-Python chunker. With keyword (BM25)
search alone over the section heading plus text, the gold chunk is in the top 5 for 31 of
the 35 direct questions (V1–V35) and in the top 31 for all of them, and in the top 5 for 44
of the 48 easy questions (E1–E48, worst 23rd), all inside the pool of at least 100
candidates that the reranker sees. The paraphrase questions P1 and P2 share no
keywords with their sections, so they depend on dense retrieval, which was not tested here.
