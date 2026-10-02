# Questions to ask Legal AI

Questions for the criminal-law demo pack in [`data/demo_crime/`](../data/demo_crime/). Every
question here is answered by one section of those files, and the expected answer was checked
against the text of that section. Copy a question into the Ask page exactly as written.

## Before you start

1. Start the app with `start.bat`.
2. On the Ingest page, upload the 27 `.txt` files from `data/demo_crime/`. The message
   "Duplicate document … already indexed" only means that file is already uploaded.
3. If other documents are indexed too (old contracts, the earlier 3-file crime version),
   remove them so answers come only from these files. The web app has no delete button, so
   either delete one document at http://localhost:8000/docs (**DELETE /documents/{source_id}**,
   Try it out, type the name, Execute), or start clean: close the backend window, delete the
   folder `data\lancedb_lc` (`rmdir /s /q data\lancedb_lc`), run `start.bat` again and upload
   the 27 files. Home should then show **27 documents, 493 chunks**.

## The 15 best questions for a live demo

For a demo where you upload the files in front of the audience, follow [`live_demo.md`](live_demo.md).

| # | Question | What should happen |
|---|---|---|
| 1 | What is the punishment for murder? | Verified: Death, or imprisonment for life, and also a fine (IPC Section 302). |
| 2 | Is an act done by accident, without any criminal intention, an offence? | Verified: No, if it is done by accident or misfortune, without criminal intention, in doing a lawful act in a lawful manner with proper care (IPC s80). |
| 3 | Can a child under seven years of age be punished for a crime? | Verified: No. Nothing is an offence which is done by a child under seven (IPC Section 82). |
| 4 | What is the punishment for theft? | Verified: Imprisonment up to three years, or fine, or both (IPC Section 379). |
| 5 | If someone steals my mobile phone, how long can he be sent to jail? | Verified, even though it never says "theft" (paraphrase) |
| 6 | What is the punishment for dishonour of a cheque for insufficient funds? | Verified: Imprisonment up to two years, or fine up to twice the amount of the cheque, or both (NI Act Section 138). |
| 7 | How long can the police keep an arrested person in custody without the order of a Magistrate? | Verified: Not more than twenty-four hours, not counting the journey to the Magistrate's court (CrPC Section 57). |
| 8 | Which courts can grant anticipatory bail to a person who fears arrest for a non-bailable offence? | Verified: The High Court or the Court of Session (CrPC Section 438). |
| 9 | What is the punishment for causing death by negligence? | Verified: Imprisonment up to two years, or fine, or both (IPC s304A). |
| 10 | What is the punishment if a husband or his relatives treat a woman with cruelty? | Verified: Imprisonment up to three years and also a fine (IPC Section 498A). |
| 11 | Can a confession made to a police officer be used against the accused? | Verified: No. A confession made to a police officer cannot be proved against a person accused of any offence (Evidence Act Section 25). |
| 12 | Why is the punishment for theft ten years of imprisonment? | **Abstained**, or corrected: theft is up to 3 years, not 10 |
| 13 | What is the fine for drunk driving? | **Abstained**: drunk driving is not in these files |
| 14 | What is mens rea? | **General knowledge** badge (purple), no citations |
| 15 | What is the punishment for a drunken person who misbehaves in a public place? | Verified: Simple imprisonment up to twenty-four hours, or fine up to ten rupees, or both (IPC s510). |

## All questions by topic

Each should come back **Verified**, citing the section shown. The section number is the
one in the cited chunk id (for example `ipc_theft::s379` is IPC Section 379).

### Murder, death and general exceptions

| Question | Expected answer | File and section |
|---|---|---|
| What is the punishment for murder? | Death, or imprisonment for life, and also a fine (IPC Section 302). | `ipc_murder_and_culpable_homicide` s302 |
| Can a child under seven years of age be punished for a crime? | No. Nothing is an offence which is done by a child under seven (IPC Section 82). | `ipc_general_exceptions` s82 |
| A driver killed a pedestrian by careless driving, without any intention. What punishment can he get? | Causing death by a rash or negligent act: up to two years, or fine, or both (IPC Section 304A). | `ipc_murder_and_culpable_homicide` s304A |
| What happens if a person of unsound mind commits a crime? | Nothing is an offence if, because of unsoundness of mind, he could not know the nature of the act or that it was wrong or against the law (IPC s84). | `ipc_general_exceptions` s84 |
| Is an act done by accident, without any criminal intention, an offence? | No, if it is done by accident or misfortune, without criminal intention, in doing a lawful act in a lawful manner with proper care (IPC s80). | `ipc_general_exceptions` s80 |
| Is a person who was made drunk against his will guilty of an offence? | No, if the intoxication made him incapable of knowing what he was doing and the thing was given to him without his knowledge or against his will (IPC s85). | `ipc_general_exceptions` s85 |
| What is the punishment for culpable homicide not amounting to murder? | Imprisonment for life or up to ten years, and fine, if done with intention of causing death or such bodily injury as is likely to cause death (IPC s304). | `ipc_murder_and_culpable_homicide` s304 |
| What is the punishment for causing death by negligence? | Imprisonment up to two years, or fine, or both (IPC s304A). | `ipc_murder_and_culpable_homicide` s304A |

### Hurt, assault, restraint and kidnapping

| Question | Expected answer | File and section |
|---|---|---|
| What is the punishment for voluntarily causing hurt? | Imprisonment up to one year, or fine up to one thousand rupees, or both (IPC Section 323). | `ipc_hurt_and_grievous_hurt` s323 |
| What is the punishment for kidnapping? | Imprisonment up to seven years, and also a fine (IPC Section 363). | `ipc_kidnapping_and_abduction` s363 |
| What is the punishment for wrongful restraint? | Simple imprisonment up to one month, or fine up to five hundred rupees, or both (IPC Section 341). | `ipc_wrongful_restraint_and_confinement` s341 |
| What is the punishment for assaulting a woman with intent to outrage her modesty? | Imprisonment of not less than one year and up to five years, and also a fine (IPC Section 354). | `ipc_criminal_force_and_assault` s354 |
| What is the punishment for causing hurt with a dangerous weapon? | Imprisonment up to three years, or fine, or both (IPC s324). | `ipc_hurt_and_grievous_hurt` s324 |
| What is the punishment for causing hurt by a rash or negligent act? | Imprisonment up to six months, or fine up to five hundred rupees, or both (IPC s337). | `ipc_hurt_and_grievous_hurt` s337 |
| What is the punishment for causing grievous hurt by a rash or negligent act? | Imprisonment up to two years, or fine up to one thousand rupees, or both (IPC s338). | `ipc_hurt_and_grievous_hurt` s338 |
| What is the punishment for wrongful confinement? | Imprisonment up to one year, or fine up to one thousand rupees, or both (IPC s342). | `ipc_wrongful_restraint_and_confinement` s342 |
| What is the punishment for assault? | Imprisonment up to three months, or fine up to five hundred rupees, or both (IPC s352). | `ipc_criminal_force_and_assault` s352 |
| What is the punishment for stalking? | First conviction: up to three years and fine; second or later conviction: up to five years and fine (IPC s354D). | `ipc_criminal_force_and_assault` s354D |

### Theft, robbery and other property crimes

| Question | Expected answer | File and section |
|---|---|---|
| What is the punishment for theft? | Imprisonment up to three years, or fine, or both (IPC Section 379). | `ipc_theft` s379 |
| What is the punishment for cheating under section 420? | Imprisonment up to seven years, and also a fine (IPC Section 420). | `ipc_cheating` s420 |
| How many persons must commit a robbery together for it to be called dacoity? | Five or more persons (IPC Section 391). | `ipc_robbery_and_dacoity` s391 |
| What is the punishment for robbery committed on the highway between sunset and sunrise? | Rigorous imprisonment that may extend to fourteen years, and fine (IPC Section 392). | `ipc_robbery_and_dacoity` s392 |
| What is the punishment for dishonestly receiving stolen property? | Imprisonment up to three years, or fine, or both (IPC Section 411). | `ipc_receiving_stolen_property` s411 |
| What is the punishment for extortion? | Imprisonment up to three years, or fine, or both (IPC Section 384). | `ipc_extortion` s384 |
| What is the punishment for mischief? | Imprisonment up to three months, or fine, or both (IPC Section 426). | `ipc_mischief` s426 |
| What is the punishment for criminal breach of trust? | Imprisonment up to three years, or fine, or both (IPC Section 406). | `ipc_criminal_breach_of_trust_and_misappropriation` s406 |
| What is the punishment for criminal trespass? | Imprisonment up to three months, or fine up to five hundred rupees, or both (IPC Section 447). | `ipc_criminal_trespass` s447 |
| If someone steals my mobile phone, how long can he be sent to jail? | Up to three years, or fine, or both (theft, IPC Section 379). | `ipc_theft` s379 |
| What is the punishment for theft in a house? | Imprisonment up to seven years, and fine (IPC s380). | `ipc_theft` s380 |
| What is the punishment for attempting to commit robbery? | Rigorous imprisonment up to seven years, and fine (IPC s393). | `ipc_robbery_and_dacoity` s393 |
| What is the punishment for dacoity? | Imprisonment for life, or rigorous imprisonment up to ten years, and fine (IPC s395). | `ipc_robbery_and_dacoity` s395 |
| What is the punishment for dishonest misappropriation of property? | Imprisonment up to two years, or fine, or both (IPC s403). | `ipc_criminal_breach_of_trust_and_misappropriation` s403 |
| What is the punishment for criminal breach of trust by a clerk or servant? | Imprisonment up to seven years, and fine (IPC s408). | `ipc_criminal_breach_of_trust_and_misappropriation` s408 |
| What is the punishment for cheating? | Imprisonment up to one year, or fine, or both (IPC s417); cheating that induces delivery of property is punished under s420. | `ipc_cheating` s417 |
| What is the punishment for house-trespass? | Imprisonment up to one year, or fine up to one thousand rupees, or both (IPC s448). | `ipc_criminal_trespass` s448 |
| What is the punishment for house-breaking by night? | Imprisonment up to five years, and fine (IPC s457). | `ipc_criminal_trespass` s457 |
| What is the punishment for setting fire to a house? | Imprisonment for life, or up to ten years, and fine (IPC s436). | `ipc_mischief` s436 |
| What is theft? | Dishonestly moving movable property out of another person's possession without consent, intending to take it (IPC s378). | `ipc_theft` s378 |

### Forgery and fake currency

| Question | Expected answer | File and section |
|---|---|---|
| What is the punishment for forgery? | Imprisonment up to two years, or fine, or both (IPC Section 465). | `ipc_forgery_and_counterfeit_currency` s465 |
| What is the punishment for counterfeiting currency notes? | Imprisonment for life, or imprisonment up to ten years, and also a fine (IPC Section 489A). | `ipc_forgery_and_counterfeit_currency` s489A |
| What is the punishment for forgery for the purpose of cheating? | Imprisonment up to seven years, and fine (IPC s468). | `ipc_forgery_and_counterfeit_currency` s468 |
| What is the punishment for possessing counterfeit currency notes? | Imprisonment up to seven years, or fine, or both (IPC s489C). | `ipc_forgery_and_counterfeit_currency` s489C |

### Marriage offences and cruelty

| Question | Expected answer | File and section |
|---|---|---|
| What is the punishment if a husband or his relatives treat a woman with cruelty? | Imprisonment up to three years and also a fine (IPC Section 498A). | `ipc_marriage_offences_and_cruelty_498a` s498A |
| What is the punishment for marrying again while the husband or wife is still living? | Imprisonment up to seven years, and also a fine (IPC Section 494). | `ipc_marriage_offences_and_cruelty_498a` s494 |
| What is the punishment for hiding a former marriage and marrying again? | Imprisonment up to ten years, and fine (IPC s495). | `ipc_marriage_offences_and_cruelty_498a` s495 |

### Defamation, intimidation and insult

| Question | Expected answer | File and section |
|---|---|---|
| What is the punishment for defamation? | Simple imprisonment up to two years, or fine, or both (IPC Section 500). | `ipc_defamation` s500 |
| What is the punishment for criminal intimidation? | Imprisonment up to two years, or fine, or both (IPC Section 506). | `ipc_criminal_intimidation_and_insult` s506 |
| What is the punishment for intentionally insulting someone to provoke a breach of the peace? | Imprisonment up to two years, or fine, or both (IPC s504). | `ipc_criminal_intimidation_and_insult` s504 |
| What is the punishment for insulting the modesty of a woman by words or gestures? | Simple imprisonment up to three years, and fine (IPC s509). | `ipc_criminal_intimidation_and_insult` s509 |
| What is the punishment for a drunken person who misbehaves in a public place? | Simple imprisonment up to twenty-four hours, or fine up to ten rupees, or both (IPC s510). | `ipc_criminal_intimidation_and_insult` s510 |
| What is defamation? | Making or publishing an imputation about a person, by words, signs or visible representations, intending or knowing it will harm that person's reputation (IPC s499). | `ipc_defamation` s499 |

### Rioting, conspiracy, false evidence

| Question | Expected answer | File and section |
|---|---|---|
| What is the punishment for criminal conspiracy to commit a serious offence? | Punished in the same manner as if he had abetted that offence, where the Code has no express provision (IPC Section 120B). | `ipc_abetment_conspiracy_and_attempt` s120B |
| How many persons make an assembly an unlawful assembly? | Five or more persons with a common object listed in the section (IPC Section 141). | `ipc_unlawful_assembly_and_rioting` s141 |
| What is the punishment for rioting? | Imprisonment up to two years, or fine, or both (IPC Section 147). | `ipc_unlawful_assembly_and_rioting` s147 |
| What is the punishment for giving false evidence in a judicial proceeding? | Imprisonment up to seven years, and also a fine (IPC Section 193). | `ipc_false_evidence` s193 |
| What is the punishment for being a member of an unlawful assembly? | Imprisonment up to six months, or fine, or both (IPC s143). | `ipc_unlawful_assembly_and_rioting` s143 |
| What is the punishment for rioting with a deadly weapon? | Imprisonment up to three years, or fine, or both (IPC s148). | `ipc_unlawful_assembly_and_rioting` s148 |
| What is the punishment for committing an affray? | Imprisonment up to one month, or fine up to one hundred rupees, or both (IPC s160). | `ipc_unlawful_assembly_and_rioting` s160 |
| What is the punishment for making a false criminal charge to injure someone? | Imprisonment up to two years, or fine, or both (IPC s211, basic case). | `ipc_false_evidence` s211 |
| What is the punishment for escaping from lawful custody? | Imprisonment up to two years, or fine, or both (IPC s224). | `ipc_false_evidence` s224 |
| What is criminal conspiracy? | When two or more persons agree to do an illegal act, or a legal act by illegal means (IPC s120A). | `ipc_abetment_conspiracy_and_attempt` s120A |
| What is rioting? | Force or violence used by an unlawful assembly, or any member of it, in pursuing its common object (IPC s146). | `ipc_unlawful_assembly_and_rioting` s146 |

### Arrest, FIR and bail (CrPC)

| Question | Expected answer | File and section |
|---|---|---|
| How long can the police keep an arrested person in custody without the order of a Magistrate? | Not more than twenty-four hours, not counting the journey to the Magistrate's court (CrPC Section 57). | `crpc_arrest` s57 |
| Must the police tell a person why he is being arrested without a warrant? | Yes, they must immediately tell him the full particulars of the offence or other grounds for the arrest (CrPC Section 50). | `crpc_arrest` s50 |
| Which courts can grant anticipatory bail to a person who fears arrest for a non-bailable offence? | The High Court or the Court of Session (CrPC Section 438). | `crpc_bail` s438 |
| What can a person do if the police station refuses to record his information about a cognizable offence? | Send the substance of the information in writing, by post, to the Superintendent of Police concerned (CrPC Section 154). | `crpc_fir_and_investigation` s154 |
| What must the police do when told about a non-cognizable offence? | Enter the substance in the prescribed book and refer the informant to the Magistrate (CrPC s155). | `crpc_fir_and_investigation` s155 |
| Should a person sign the statement he gives to the police during investigation? | No, the statement shall not be signed by the person making it (CrPC s162). | `crpc_fir_and_investigation` s162 |
| Who can record a confession during an investigation? | A Metropolitan Magistrate or a Judicial Magistrate (CrPC s164). | `crpc_fir_and_investigation` s164 |
| Can the amount of a bail bond be excessive? | No; it must be fixed with regard to the circumstances and shall not be excessive, and the High Court or Court of Session may reduce it (CrPC s440). | `crpc_bail` s440 |
| Can an arrested person ask for a medical examination? | Yes; if he asks, the Magistrate shall direct an examination by a registered medical practitioner, unless the request is for vexation or delay (CrPC s54). | `crpc_arrest` s54 |

### Cheque bounce (NI Act)

| Question | Expected answer | File and section |
|---|---|---|
| What is the punishment for dishonour of a cheque for insufficient funds? | Imprisonment up to two years, or fine up to twice the amount of the cheque, or both (NI Act Section 138). | `ni_act_cheque_bounce` s138 |
| Within how many days of a cheque bouncing must the payee send a written notice to the drawer? | Within thirty days of hearing from the bank that the cheque was returned unpaid; the drawer then has fifteen days to pay (NI Act Section 138). | `ni_act_cheque_bounce` s138 |
| Within what time must a complaint for a cheque bounce offence be made? | Within one month of the date on which the cause of action arises (NI Act Section 142). | `ni_act_cheque_bounce` s142 |
| How much must a person convicted of cheque bounce deposit when he appeals? | At least twenty percent of the fine or compensation awarded by the trial court (NI Act Section 148). | `ni_act_cheque_bounce` s148 |
| My friend gave me a cheque and it bounced because his account had no money. What punishment can he get? | Up to two years, or fine up to twice the cheque amount, or both (NI Act Section 138). | `ni_act_cheque_bounce` s138 |
| Is a cheque bounce offence compoundable? | Yes, every offence under the Act is compoundable (NI Act s147). | `ni_act_cheque_bounce` s147 |
| What does the court presume about a cheque received by its holder? | That it was received for the discharge of a debt or other liability, unless the contrary is proved (NI Act s139). | `ni_act_cheque_bounce` s139 |
| If a company's cheque bounces, who can be held guilty? | The company and every person who was in charge of and responsible to the company for its business at the time (NI Act s141). | `ni_act_cheque_bounce` s141 |

### Evidence: confessions and burden of proof

| Question | Expected answer | File and section |
|---|---|---|
| Can a confession made to a police officer be used against the accused? | No. A confession made to a police officer cannot be proved against a person accused of any offence (Evidence Act Section 25). | `evidence_act_confessions` s25 |
| Who has to prove that the accused acted in private defence or comes within a general exception? | The accused; the burden of proving it is on him, and the Court presumes those circumstances are absent (Evidence Act Section 105). | `evidence_act_burden_of_proof` s105 |
| Can a confession made while in police custody be used against the accused? | No, unless it is made in the immediate presence of a Magistrate (Evidence Act s26). | `evidence_act_confessions` s26 |
| Is a confession obtained by a threat or promise valid in a criminal case? | No, it is irrelevant if caused by an inducement, threat or promise from a person in authority (Evidence Act s24). | `evidence_act_confessions` s24 |
| Who must prove a fact that is especially within his own knowledge? | That person (Evidence Act s106). | `evidence_act_burden_of_proof` s106 |
| If a man has not been heard of for seven years, who must prove that he is alive? | The person who says he is alive (Evidence Act s108). | `evidence_act_burden_of_proof` s108 |
| What does the court presume in a dowry death case? | If the woman was subjected to cruelty or harassment for dowry soon before her death, the court shall presume that person caused the dowry death (Evidence Act s113B). | `evidence_act_burden_of_proof` s113B |

## Questions that should NOT be verified

These show that the system refuses instead of guessing.

| Question | What should happen |
|---|---|
| Why is the punishment for theft ten years of imprisonment? | Abstain, or correct it: theft is punishable with up to three years (Section 379). |
| Why can the police keep an arrested person for 72 hours without producing him before a Magistrate? | Abstain, or correct it: the limit is twenty-four hours (Section 57). |
| What is the fine for drunk driving? | Abstain: drunk driving is in the Motor Vehicles Act, which is not in this pack. |
| What is the punishment for hacking into someone's computer? | Abstain: hacking is in the Information Technology Act, which is not in this pack. |

## General-knowledge questions

The files don't answer these, so the system answers from the model's own knowledge, with a
purple **General knowledge** badge and no citations or score.

| Question | What should happen |
|---|---|
| What is mens rea? | General knowledge answer (labelled purple): the guilty mind or criminal intent. |

## A real-life case, asked the right way

"My friend hit a man with his car when he had a heart attack. How can he be saved?" comes back
**Abstained**, correctly: the files state the law, they don't give legal advice. Ask what the
law says instead:

| Question | Expected answer |
|---|---|
| Is an act done by accident, without any criminal intention, an offence? | No, if it is done by accident or misfortune, without criminal intention, in doing a lawful act in a lawful manner with proper care (IPC s80). |
| What is the punishment for causing death by negligence? | Imprisonment up to two years, or fine, or both (IPC s304A). |
| What is the punishment for causing grievous hurt by a rash or negligent act? | Imprisonment up to two years, or fine up to one thousand rupees, or both (IPC s338). |
| What is the punishment for causing hurt by a rash or negligent act? | Imprisonment up to six months, or fine up to five hundred rupees, or both (IPC s337). |

Together these cover the case: a sudden heart attack points to an accident (s80); if
it was negligence, s337 or s338 apply when the man was hurt, and s304A if he died.

## Tips for asking

- Use the words of the law: "punishment for …", "rash or negligent act", "anticipatory bail".
- Ask one thing per question. Two-part questions are refused more often.
- "What should I do?" or "how can he escape?" asks for advice, which the files don't contain.
- A correct answer can still come back **Abstained** when the checking model (NLI) is unsure.
  Click the citation chip to see which check marked it down. This strictness is a known
  limitation; the system is built so that a wrong answer is never shown as Verified.

## Test all of them automatically

With the backend running (`start.bat`), from the project folder, in the `.venv-lc` environment:

```
python scripts/check_demo_questions.py
```

It uploads the 27 files (skipping any already uploaded), asks all 91 questions through
the API, prints PASS / CHECK / FALSE_REFUSAL / RETRIEVAL_MISS for each with a summary, and
saves the results to `data/processed/demo_crime_check.json`. Add `--only V1,E5,U1` to ask a
few, or `--skip-ingest` if the files are already uploaded. At 15–20 seconds per question, the
full run takes about half an hour.

**Status:** the expected answers come from the text of each section. The questions have not
yet been run through the full pipeline (LLM and NLI); the script above does that. The IPC,
CrPC and Evidence Act files are the texts as they stood before 1 July 2024, when the BNS,
BNSS and BSA replaced them; see `data/demo_crime/README.md`.
