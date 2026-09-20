# E2E corpus check — 2026-09-20

Corpus `C:\Users\11020\Desktop\LEGAL-AI-PROG\data\corpus`, index `C:\Users\11020\Desktop\LEGAL-AI-PROG\data\lancedb_corpus_check`, embedder `sentence-transformers/all-MiniLM-L6-v2`, k=3.

## Ingestion

| status | chunks | chunking | secs | file |
|---|---|---|---|---|
| ok | 308 | fallback | 14.07 | `data\corpus\civil_law\cuad\CUAD_v1\full_contract_pdf\Part_I\License_Agreements\CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement.pdf` |
| ok | 1136 | fallback | 30.76 | `data\corpus\civil_law\maud\contracts\contract_0.txt` |

**2/2 files indexed, 1444 chunks (0 structured, 2 fallback), 0 failed.**

## Retrieval — top-1 per variant

### limitation period for filing a suit to recover property

| variant | source | score | overlap | snippet |
|---|---|---|---|---|
| dense | contract_0 · Paragraph 822 | 1.1436 | suit | ny such case, other than the settlement of any action, suit, proceeding, claim, arbitration or investigation (but not a criminal proceeding) that requires payments by the Company (net of insurance proceeds received and i |
| fts | contract_0 · Paragraph 939 | 7.5739 | limitation, period | Without limiting Parent’s cooperation obligations described in this Section 5.6 (subject to the limitations herein), Parent will control the ultimate strategy (including with respect to negotiating any remedies) for secu |
| hybrid | contract_0 · Paragraph 822 | 0.0164 | suit | ny such case, other than the settlement of any action, suit, proceeding, claim, arbitration or investigation (but not a criminal proceeding) that requires payments by the Company (net of insurance proceeds received and i |

### remedies available for breach of contract

| variant | source | score | overlap | snippet |
|---|---|---|---|---|
| dense | CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement · Paragraph 231 | 1.0893 | breach | Either Party (the “Non-Breaching Party”) may terminate this Agreement in the event the other Party (the “Breaching Party”) commits a material breach of this Agreement, and such material breach (excluding breaches of paym |
| fts | contract_0 · Paragraph 1115 | 11.5546 | — | The parties hereto agree that irreparable damage for which monetary damages, even if available, would not be an adequate remedy, would occur in the event that any of the provisions of this Agreement were not performed in |
| hybrid | CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement · Paragraph 217 | 0.032 | breach, remedie | Given the nature of the Confidential Information and the competitive damage that could result to a Party upon unauthorized disclosure, use or transfer of its Confidential Information to any Third Party, the Parties agree |

### when is specific performance granted instead of damages

| variant | source | score | overlap | snippet |
|---|---|---|---|---|
| dense | CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement · Paragraph 264 | 1.0315 | damage, performance | The arbitrators shall have no Source: CYTODYN INC., 10-Q, 1/9/2020 authority to award punitive or any other type of damages not measured by a Party’s compensatory damages. The Parties further agree that the decision of t |
| fts | contract_0 · Paragraph 1115 | 14.5977 | damage, specific | The parties hereto agree that irreparable damage for which monetary damages, even if available, would not be an adequate remedy, would occur in the event that any of the provisions of this Agreement were not performed in |
| hybrid | CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement · Paragraph 264 | 0.0164 | damage, performance | The arbitrators shall have no Source: CYTODYN INC., 10-Q, 1/9/2020 authority to award punitive or any other type of damages not measured by a Party’s compensatory damages. The Parties further agree that the decision of t |

### registration requirements for a sale deed

| variant | source | score | overlap | snippet |
|---|---|---|---|---|
| dense | contract_0 · Paragraph 519 | 1.2112 | registration | (v) “Company Registered Intellectual Property Rights” means all United States, international and foreign: (A) patents and patent applications (including provisional applications), (B) registered trademarks or service mar |
| fts | CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement · Paragraph 154 | 7.1276 | sale | on is solely related to the sale, offer for sale or use of a Licensed Product in the Field in the Territory, and the provisions of Section 13.2 shall not apply if Vyera is the Party that did not agree to pursue such Requ |
| hybrid | contract_0 · Paragraph 519 | 0.0164 | registration | (v) “Company Registered Intellectual Property Rights” means all United States, international and foreign: (A) patents and patent applications (including provisional applications), (B) registered trademarks or service mar |

### termination of the agreement for material breach and cure period

| variant | source | score | overlap | snippet |
|---|---|---|---|---|
| dense | CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement · Paragraph 233 | 0.6512 | agreement, breach, cure, material, period, termination | Any termination of this Agreement pursuant to this Section 11.4 shall become effective at the end of the Cure Period, unless the Breaching Party has cured any such material breach prior to the expiration of such Cure Per |
| fts | CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement · Paragraph 233 | 23.0747 | agreement, breach, cure, material, period, termination | Any termination of this Agreement pursuant to this Section 11.4 shall become effective at the end of the Cure Period, unless the Breaching Party has cured any such material breach prior to the expiration of such Cure Per |
| hybrid | CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement · Paragraph 233 | 0.0328 | agreement, breach, cure, material, period, termination | Any termination of this Agreement pursuant to this Section 11.4 shall become effective at the end of the Cure Period, unless the Breaching Party has cured any such material breach prior to the expiration of such Cure Per |

### indemnification obligations of the licensee

| variant | source | score | overlap | snippet |
|---|---|---|---|---|
| dense | CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement · Paragraph 245 | 0.8216 | obligation | materials in its legal files to be used to verify compliance with its obligations hereunder and as otherwise required to comply with Applicable Law or such Party’s bona fide document retention policy; (d) Vyera shall hav |
| fts | CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement · Paragraph 272 | 8.2047 | indemnification | ARTICLE 13 INDEMNIFICATION AND INSURANCE 13.1 Indemnification by Vyera. |
| hybrid | CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement · Paragraph 245 | 0.0164 | obligation | materials in its legal files to be used to verify compliance with its obligations hereunder and as otherwise required to comply with Applicable Law or such Party’s bona fide document retention policy; (d) Vyera shall hav |

### governing law and jurisdiction for disputes

| variant | source | score | overlap | snippet |
|---|---|---|---|---|
| dense | CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement · Paragraph 267 | 1.0338 | dispute | (i) By agreeing to this binding arbitration provision, the Parties understand that they are waiving certain rights and protections which may otherwise be available if a dispute between the Parties were determined by liti |
| fts | contract_0 · Paragraph 1118 | 13.2664 | governing, jurisdiction, law | 8.9. Governing Law. This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware without giving effect to any choice or conflict of laws, provision or rule (whether of the State  |
| hybrid | CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement · Paragraph 267 | 0.0164 | dispute | (i) By agreeing to this binding arbitration provision, the Parties understand that they are waiving certain rights and protections which may otherwise be available if a dispute between the Parties were determined by liti |

### confidential information disclosure obligations

| variant | source | score | overlap | snippet |
|---|---|---|---|---|
| dense | CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement · Paragraph 199 | 0.722 | confidential, disclosure, information | Each Party agrees that, during the Term and for a period of ten (10) years thereafter, a Party (the “ Receiving Party”) receiving Confidential Information of the other Party (the “ Disclosing Party”) shall: (a) maintain  |
| fts | CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement · Paragraph 209 | 13.5977 | confidential, disclosure, information | (g) If and whenever any Confidential Information is disclosed in accordance with this Section 10.3, such disclosure shall not cause any such information to cease to be Confidential Information except to the extent that s |
| hybrid | CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement · Paragraph 199 | 0.0164 | confidential, disclosure, information | Each Party agrees that, during the Term and for a period of ten (10) years thereafter, a Party (the “ Receiving Party”) receiving Confidential Information of the other Party (the “ Disclosing Party”) shall: (a) maintain  |

### conditions precedent to closing the merger

| variant | source | score | overlap | snippet |
|---|---|---|---|---|
| dense | contract_0 · Paragraph 1087 | 0.7973 | merger | If the Merger is consummated, the representations and warranties of Parent, Sub and the Company contained in the Original Agreement, this Agreement, the Company Disclosure Letter (including any exhibit, schedule or annex |
| fts | contract_0 · Paragraph 1018 | 10.2879 | closing, condition, merger | 6.1. Conditions to Obligations of Each Party to Effect the Merger. The respective obligations of each party hereto to consummate the Merger and the other Transactions shall be subject to the satisfaction at or prior to t |
| hybrid | contract_0 · Paragraph 1018 | 0.0325 | closing, condition, merger | 6.1. Conditions to Obligations of Each Party to Effect the Merger. The respective obligations of each party hereto to consummate the Merger and the other Transactions shall be subject to the satisfaction at or prior to t |

### assignment of the contract without prior written consent

| variant | source | score | overlap | snippet |
|---|---|---|---|---|
| dense | contract_0 · Paragraph 1111 | 1.1037 | assignment, consent, written | 8.6. Assignment. Neither this Agreement nor any of the rights, interests or obligations under this Agreement may be assigned or delegated, in whole or in part, by operation of law or otherwise by any of the parties heret |
| fts | contract_0 · Paragraph 1111 | 19.4541 | assignment, consent, written | 8.6. Assignment. Neither this Agreement nor any of the rights, interests or obligations under this Agreement may be assigned or delegated, in whole or in part, by operation of law or otherwise by any of the parties heret |
| hybrid | contract_0 · Paragraph 1111 | 0.0328 | assignment, consent, written | 8.6. Assignment. Neither this Agreement nor any of the rights, interests or obligations under this Agreement may be assigned or delegated, in whole or in part, by operation of law or otherwise by any of the parties heret |

## Summary

- Documents indexed: 2 (1444 chunks)
- Ingestion failures: 0
- Queries flagged (empty or no term overlap in hybrid top hit): 0

Relevance flags are a keyword heuristic to direct attention; the tables above are the actual check.