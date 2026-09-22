# Qualitative examples

Drawn from logged runs. Each names its source.

## 1. Verified answer with a correct citation

Source: `experiments/batch_ask_check/` (screenshot `screenshots/verified.png`,
row 5 of `report.md`).

> **Q:** Which two companies are the parties to the mutual non-disclosure
> agreement involving Federal Express Corporation?
>
> **A:** Federal Express Corporation ("Federal") and International Billing
> Services, Inc. ("IBS") are the parties to the mutual non-disclosure
> agreement. `[1012459_0000912057-97-027209_document_4::p4]`
>
> **Verified — VCS 1.00, 1 claim checked.**

The citation resolves to the document that actually contains the answer, which
was checked independently against the expected source file.

## 2. Correct abstention

Source: `experiments/2026-09-23-ablations/verification/full_chain/results.json`,
query "On what grounds may a landlord seek eviction of a tenant?"

Decision ABSTAIN at VCS 0.0 across 3 claims, with **no hard gate firing** — the
citations all existed and none was contradicted; the NLI returned NEUTRAL on
each claim. Under `minus_v5` the same three claims are surfaced to the user.

This example is doing double duty and should be labelled honestly in the paper:
it demonstrates the gate working, **and** it is one of the three false
abstentions in `results.md` §5, because the query did retrieve its gold chunk.
It is evidence for the calibration gap, not a clean success.

## 3. Caught fabricated citation

Source: `experiments/2026-09-23-ablations/verification/*/results.json`,
`fabricated_citation` probe.

Every citation in 14 real claims was rewritten to an id never retrieved. The
full chain caught 14/14 — V1's gate fired on all 14 and each claim scored 0.0.
With V5 removed, all 14 reach the user despite scoring 0.0.

**Note for the write-up:** this is a deterministic perturbation of real answers,
not a hallucination the model produced. It shows what the chain catches, and
must not be presented as a measured hallucination rate.

## 4. Labelled general-knowledge fallback

Source: `experiments/batch_ask_check/screenshots/general_knowledge.png`.

> **Q:** What is a non-disclosure agreement?
>
> Badged **"General knowledge — not verified against your documents"**, no
> citations, no VCS, with an explicit note that the indexed documents did not
> support an answer.

Contrast with row 7 of the same run: *"What is confidential information?"* was
**answered from the documents** at VCS 0.99, because that corpus does define
the term. The fallback fires only when verification declines — the precedence
is what keeps a general answer from displacing a sourced one.

## 5. TODO

A worked example of a **caught genuine hallucination** — one the model actually
produced, not a perturbation — is missing, and is the single most valuable
example for the paper. It requires either a run where the generator
hallucinates naturally, or an adversarial prompt set. Not yet obtained.
