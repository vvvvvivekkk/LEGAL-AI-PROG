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

Every file has at least one question. The expected answers were checked against the text
of the cited section. They have not been run through the full pipeline (LLM and NLI), so an
answer may still abstain if the NLI model judges a correct claim as neutral.

| id | Question | Expected badge | Expected answer | Gold chunk |
|---|---|---|---|---|
| V1 | What is the punishment for murder? | Verified | Death, or imprisonment for life, and also a fine (IPC Section 302). | `ipc_murder_and_culpable_homicide::s302` |
| V2 | What is the punishment for theft? | Verified | Imprisonment up to three years, or fine, or both (IPC Section 379). | `ipc_theft::s379` |
| V3 | Can a child under seven years of age be punished for a crime? | Verified | No. Nothing is an offence which is done by a child under seven (IPC Section 82). | `ipc_general_exceptions::s82` |
| V4 | What is the punishment for cheating under section 420? | Verified | Imprisonment up to seven years, and also a fine (IPC Section 420). | `ipc_cheating::s420` |
| V5 | What is the punishment if a husband or his relatives treat a woman with cruelty? | Verified | Imprisonment up to three years and also a fine (IPC Section 498A). | `ipc_marriage_offences_and_cruelty_498a::s498A` |
| V6 | How many persons must commit a robbery together for it to be called dacoity? | Verified | Five or more persons (IPC Section 391). | `ipc_robbery_and_dacoity::s391` |
| V7 | What is the punishment for robbery committed on the highway between sunset and sunrise? | Verified | Rigorous imprisonment that may extend to fourteen years, and fine (IPC Section 392). | `ipc_robbery_and_dacoity::s392` |
| V8 | What is the punishment for defamation? | Verified | Simple imprisonment up to two years, or fine, or both (IPC Section 500). | `ipc_defamation::s500` |
| V9 | What is the punishment for voluntarily causing hurt? | Verified | Imprisonment up to one year, or fine up to one thousand rupees, or both (IPC Section 323). | `ipc_hurt_and_grievous_hurt::s323` |
| V10 | What is the punishment for marrying again while the husband or wife is still living? | Verified | Imprisonment up to seven years, and also a fine (IPC Section 494). | `ipc_marriage_offences_and_cruelty_498a::s494` |
| V11 | How long can the police keep an arrested person in custody without the order of a Magistrate? | Verified | Not more than twenty-four hours, not counting the journey to the Magistrate's court (CrPC Section 57). | `crpc_arrest::s57` |
| V12 | Must the police tell a person why he is being arrested without a warrant? | Verified | Yes, they must immediately tell him the full particulars of the offence or other grounds for the arrest (CrPC Section 50). | `crpc_arrest::s50` |
| V13 | Which courts can grant anticipatory bail to a person who fears arrest for a non-bailable offence? | Verified | The High Court or the Court of Session (CrPC Section 438). | `crpc_bail::s438` |
| V14 | What can a person do if the police station refuses to record his information about a cognizable offence? | Verified | Send the substance of the information in writing, by post, to the Superintendent of Police concerned (CrPC Section 154). | `crpc_fir_and_investigation::s154:b` |
| V15 | What is the punishment for dishonour of a cheque for insufficient funds? | Verified | Imprisonment up to two years, or fine up to twice the amount of the cheque, or both (NI Act Section 138). | `ni_act_cheque_bounce::s138` |
| V16 | Within how many days of a cheque bouncing must the payee send a written notice to the drawer? | Verified | Within thirty days of hearing from the bank that the cheque was returned unpaid; the drawer then has fifteen days to pay (NI Act Section 138). | `ni_act_cheque_bounce::s138:a` |
| V17 | Within what time must a complaint for a cheque bounce offence be made? | Verified | Within one month of the date on which the cause of action arises (NI Act Section 142). | `ni_act_cheque_bounce::s142` |
| V18 | How much must a person convicted of cheque bounce deposit when he appeals? | Verified | At least twenty percent of the fine or compensation awarded by the trial court (NI Act Section 148). | `ni_act_cheque_bounce::s148` |
| V19 | What is the punishment for criminal conspiracy to commit a serious offence? | Verified | Punished in the same manner as if he had abetted that offence, where the Code has no express provision (IPC Section 120B). | `ipc_abetment_conspiracy_and_attempt::s120B` |
| V20 | How many persons make an assembly an unlawful assembly? | Verified | Five or more persons with a common object listed in the section (IPC Section 141). | `ipc_unlawful_assembly_and_rioting::s141` |
| V21 | What is the punishment for rioting? | Verified | Imprisonment up to two years, or fine, or both (IPC Section 147). | `ipc_unlawful_assembly_and_rioting::s147` |
| V22 | What is the punishment for giving false evidence in a judicial proceeding? | Verified | Imprisonment up to seven years, and also a fine (IPC Section 193). | `ipc_false_evidence::s193` |
| V23 | What is the punishment for forgery? | Verified | Imprisonment up to two years, or fine, or both (IPC Section 465). | `ipc_forgery_and_counterfeit_currency::s465` |
| V24 | What is the punishment for counterfeiting currency notes? | Verified | Imprisonment for life, or imprisonment up to ten years, and also a fine (IPC Section 489A). | `ipc_forgery_and_counterfeit_currency::s489A` |
| V25 | What is the punishment for dishonestly receiving stolen property? | Verified | Imprisonment up to three years, or fine, or both (IPC Section 411). | `ipc_receiving_stolen_property::s411` |
| V26 | What is the punishment for extortion? | Verified | Imprisonment up to three years, or fine, or both (IPC Section 384). | `ipc_extortion::s384` |
| V27 | What is the punishment for mischief? | Verified | Imprisonment up to three months, or fine, or both (IPC Section 426). | `ipc_mischief::s426` |
| V28 | What is the punishment for criminal breach of trust? | Verified | Imprisonment up to three years, or fine, or both (IPC Section 406). | `ipc_criminal_breach_of_trust_and_misappropriation::s406` |
| V29 | What is the punishment for criminal trespass? | Verified | Imprisonment up to three months, or fine up to five hundred rupees, or both (IPC Section 447). | `ipc_criminal_trespass::s447` |
| V30 | What is the punishment for kidnapping? | Verified | Imprisonment up to seven years, and also a fine (IPC Section 363). | `ipc_kidnapping_and_abduction::s363` |
| V31 | What is the punishment for wrongful restraint? | Verified | Simple imprisonment up to one month, or fine up to five hundred rupees, or both (IPC Section 341). | `ipc_wrongful_restraint_and_confinement::s341` |
| V32 | What is the punishment for assaulting a woman with intent to outrage her modesty? | Verified | Imprisonment of not less than one year and up to five years, and also a fine (IPC Section 354). | `ipc_criminal_force_and_assault::s354` |
| V33 | What is the punishment for criminal intimidation? | Verified | Imprisonment up to two years, or fine, or both (IPC Section 506). | `ipc_criminal_intimidation_and_insult::s506` |
| V34 | Can a confession made to a police officer be used against the accused? | Verified | No. A confession made to a police officer cannot be proved against a person accused of any offence (Evidence Act Section 25). | `evidence_act_confessions::s25` |
| V35 | Who has to prove that the accused acted in private defence or comes within a general exception? | Verified | The accused; the burden of proving it is on him, and the Court presumes those circumstances are absent (Evidence Act Section 105). | `evidence_act_burden_of_proof::s105` |
| P1 | If someone steals my mobile phone, how long can he be sent to jail? | Verified (paraphrase) | Up to three years, or fine, or both (theft, IPC Section 379). | `ipc_theft::s379` |
| P2 | A driver killed a pedestrian by careless driving, without any intention. What punishment can he get? | Verified (paraphrase) | Causing death by a rash or negligent act: up to two years, or fine, or both (IPC Section 304A). | `ipc_murder_and_culpable_homicide::s304A` |
| P3 | My friend gave me a cheque and it bounced because his account had no money. What punishment can he get? | Verified (paraphrase) | Up to two years, or fine up to twice the cheque amount, or both (NI Act Section 138). | `ni_act_cheque_bounce::s138` |
| F1 | Why is the punishment for theft ten years of imprisonment? | Abstained (false premise) | Abstain, or correct it: theft is punishable with up to three years (Section 379). | `ipc_theft::s379` |
| F2 | Why can the police keep an arrested person for 72 hours without producing him before a Magistrate? | Abstained (false premise) | Abstain, or correct it: the limit is twenty-four hours (Section 57). | `crpc_arrest::s57` |
| U1 | What is the fine for drunk driving? | Abstained (not in the pack) | Abstain: drunk driving is in the Motor Vehicles Act, which is not in this pack. | — |
| U2 | What is the punishment for hacking into someone's computer? | Abstained (not in the pack) | Abstain: hacking is in the Information Technology Act, which is not in this pack. | — |
| G1 | What is mens rea? | General knowledge | General knowledge answer (labelled purple): the guilty mind or criminal intent. | — |

`questions.json` holds the same list.

**Checked when the pack was built:** every file is parsed into all of its sections (no
paragraph fallback, no duplicate chunk ids, longest chunk 177 words), and the LangChain
splitter produces the same 493 chunk ids as the plain-Python chunker. With keyword (BM25)
search alone over the section heading plus text, the gold chunk is in the top 5 for 31 of
the 35 direct questions (V1–V35) and in the top 31 for all of them, inside the pool of at
least 100 candidates that the reranker sees. The paraphrase questions P1 and P2 share no
keywords with their sections, so they depend on dense retrieval, which was not tested here.
