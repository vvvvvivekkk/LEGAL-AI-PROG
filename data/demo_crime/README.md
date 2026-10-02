# Criminal-law demo pack

Three real Indian criminal-law texts, written in the format the structure parser reads,
so each one is split by Section (SAC) and every answer cites a section such as
`indian_penal_code_1860_crimes::s302`. Upload the three `.txt` files on the Ingest page,
then ask the questions below on the Ask page.

| File | What it contains | Sections | Chunks |
|---|---|---|---|
| `indian_penal_code_1860_crimes.txt` | IPC: general exceptions (child, private defence), murder and homicide, hurt, wrongful restraint, assault, kidnapping, offences against property (theft, extortion, robbery, dacoity, breach of trust, cheating, mischief, trespass), offences relating to marriage and cruelty (498A), defamation, criminal intimidation, attempts | 217 | 221 |
| `code_of_criminal_procedure_1973_arrest_fir_bail.txt` | CrPC: arrest (41–60A), FIR and investigation (154–176), bail (436–450) | 67 | 116 |
| `negotiable_instruments_act_1881_cheque_bounce.txt` | NI Act Chapter XVII: cheque bounce (138–148) | 13 | 20 |

## Where the text comes from

The section text is from `IndiaLaw.db` in the public GitHub repository
[civictech-India/Indian-Law-Penal-Code-Json](https://github.com/civictech-India/Indian-Law-Penal-Code-Json),
which holds Indian Acts section by section as published on India Code.
`scripts/build_crime_pack.py` turns it into these files. The wording of each section is
unchanged except for whitespace and the source website's amendment footnotes (a digit glued
to a word, such as "thirty1", and notes such as "1 Criminal Law (Amendment) Act, 2018"),
which are removed.

**Legal status.** The Indian Penal Code and the Code of Criminal Procedure were replaced on
1 July 2024 by the Bharatiya Nyaya Sanhita, 2023 and the Bharatiya Nagarik Suraksha Sanhita,
2023. These files are the IPC and CrPC as they stood before that date. The Negotiable
Instruments Act, 1881 is still in force. This pack is for demonstrating the system, not a
source of current law.

**Clause letters.** The source lost the official (1)/(a) labels inside sections. A section
longer than 180 words is therefore split into parts at paragraph or sentence boundaries,
written as `Clause (a)`, `Clause (b)`, …: these letters number the parts in order and are
**not** the Act's own clause numbers. Section numbers are always the real ones. Short parts
keep every chunk within what the embedding model (about 256 tokens) and the NLI model (512
tokens) can read.

## Questions to ask

The expected answers below were checked against the text of the cited section. They have not
been run through the full pipeline (LLM and NLI), so an answer may still abstain if the NLI
model judges a correct claim as neutral.

| id | Question | Expected badge | Expected answer | Section |
|---|---|---|---|---|
| V1 | What is the punishment for murder? | Verified | Death, or imprisonment for life, and also a fine (IPC Section 302). | `s302` |
| V2 | What is the punishment for theft? | Verified | Imprisonment up to three years, or fine, or both (IPC Section 379). | `s379` |
| V3 | Can a child under seven years of age be punished for a crime? | Verified | No. Nothing is an offence which is done by a child under seven (IPC Section 82). | `s82` |
| V4 | What is the punishment for cheating under section 420? | Verified | Imprisonment up to seven years, and also a fine (IPC Section 420). | `s420` |
| V5 | What is the punishment if a husband or his relatives treat a woman with cruelty? | Verified | Imprisonment up to three years and also a fine (IPC Section 498A). | `s498A` |
| V6 | How many persons must commit a robbery together for it to be called dacoity? | Verified | Five or more persons (IPC Section 391). | `s391` |
| V7 | What is the punishment for robbery committed on the highway between sunset and sunrise? | Verified | Rigorous imprisonment that may extend to fourteen years, and fine (IPC Section 392). | `s392` |
| V8 | What is the punishment for defamation? | Verified | Simple imprisonment up to two years, or fine, or both (IPC Section 500). | `s500` |
| V9 | What is the punishment for voluntarily causing hurt? | Verified | Imprisonment up to one year, or fine up to one thousand rupees, or both (IPC Section 323). | `s323` |
| V10 | What is the punishment for marrying again while the husband or wife is still living? | Verified | Imprisonment up to seven years, and also a fine (IPC Section 494). | `s494` |
| V11 | How long can the police keep an arrested person in custody without the order of a Magistrate? | Verified | Not more than twenty-four hours, not counting the journey to the Magistrate's court (CrPC Section 57). | `s57` |
| V12 | Must the police tell a person why he is being arrested without a warrant? | Verified | Yes, they must immediately tell him the full particulars of the offence or other grounds for the arrest (CrPC Section 50). | `s50` |
| V13 | Which courts can grant anticipatory bail to a person who fears arrest for a non-bailable offence? | Verified | The High Court or the Court of Session (CrPC Section 438). | `s438` |
| V14 | What can a person do if the police station refuses to record his information about a cognizable offence? | Verified | Send the substance of the information in writing, by post, to the Superintendent of Police concerned (CrPC Section 154). | `s154:b` |
| V15 | What is the punishment for dishonour of a cheque for insufficient funds? | Verified | Imprisonment up to two years, or fine up to twice the amount of the cheque, or both (NI Act Section 138). | `s138` |
| V16 | Within how many days of a cheque bouncing must the payee send a written notice to the drawer? | Verified | Within thirty days of hearing from the bank that the cheque was returned unpaid; the drawer then has fifteen days to pay (NI Act Section 138). | `s138:a` |
| V17 | Within what time must a complaint for a cheque bounce offence be made? | Verified | Within one month of the date on which the cause of action arises (NI Act Section 142). | `s142` |
| V18 | How much must a person convicted of cheque bounce deposit when he appeals? | Verified | At least twenty percent of the fine or compensation awarded by the trial court (NI Act Section 148). | `s148` |
| P1 | If someone steals my mobile phone, how long can he be sent to jail? | Verified (paraphrase) | Up to three years, or fine, or both (theft, IPC Section 379). | `s379` |
| P2 | A driver killed a pedestrian by careless driving, without any intention. What punishment can he get? | Verified (paraphrase) | Causing death by a rash or negligent act: up to two years, or fine, or both (IPC Section 304A). | `s304A` |
| P3 | My friend gave me a cheque and it bounced because his account had no money. What punishment can he get? | Verified (paraphrase) | Up to two years, or fine up to twice the cheque amount, or both (NI Act Section 138). | `s138` |
| F1 | Why is the punishment for theft ten years of imprisonment? | Abstained (false premise) | Abstain, or correct it: theft is punishable with up to three years (Section 379). | `s379` |
| F2 | Why can the police keep an arrested person for 72 hours without producing him before a Magistrate? | Abstained (false premise) | Abstain, or correct it: the limit is twenty-four hours (Section 57). | `s57` |
| U1 | What is the fine for drunk driving? | Abstained (not in the pack) | Abstain: drunk driving is in the Motor Vehicles Act, which is not in this pack. | — |
| U2 | What is the punishment for hacking into someone's computer? | Abstained (not in the pack) | Abstain: hacking is in the Information Technology Act, which is not in this pack. | — |
| G1 | What is mens rea? | General knowledge | General knowledge answer (labelled purple): the guilty mind or criminal intent. | — |

`questions.json` holds the same list.

**Checked when the pack was built:** all 297 sections are parsed into the expected sections
(no paragraph fallback, no duplicate chunk ids, longest chunk 177 words); the LangChain
splitter produces the same 357 chunk ids as the plain-Python chunker; and with keyword (BM25)
search over the section heading plus text, the gold section ranks first or second for 16 of
the 18 direct questions (s302 is 4th, s148 18th). The paraphrase questions P1 and P2 share no
keywords with their sections, so they depend on dense retrieval, which was not tested here.
