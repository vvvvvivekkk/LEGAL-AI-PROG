"""Build results.json from the raw runs plus the hand-assigned judgements below.

Every number comes from raw_run.json / raw_rerun.json / replay_fixed.json. The
labels, per-claim support checks and notes are judgements made by comparing each
recorded answer with the pre-written expected answer and source passage in
questions.json (committed before the run).

    python experiments/2026-09-24-human-e2e/build_results.py
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent

# id -> (label, does each claim's proof quote support it, note)
JUDGED = {
    "S1": ("FALSE_ABSTAIN", None,
           "Answer text is correct (3 years, tacit 1-year extension) and cites the right chunk (p18), but the "
           "model wrote the citations with full-width brackets 【】; the parser found no claims, so it abstained. "
           "Parser bug, fixed in f7f8dd9."),
    "S2": ("CORRECT_VERIFIED", [True], "Spain, cited NDA_7::p21 (clause 10)."),
    "S3": ("CORRECT_VERIFIED", [True], "Equitable remedies including injunction, cited HALO-NDA::p7 (section 6)."),
    "S4": ("FALSE_ABSTAIN", None,
           "Answer text is correct (August 16, 2017; Vivint Solar, Inc. and Vivint, Inc.) and cites the right "
           "chunk, but the source id 'VIVINT SOLAR, INC. - ...' contains a comma; the parser split the citation "
           "at it, V1 found neither half, VCS 0. Parser bug, fixed in 6b6a0f5."),
    "S5": ("FALSE_ABSTAIN", None,
           "Both claims correct and cite Section 10. Claim 1 (sixty days) ENTAILS 0.99; claim 2 ('the appeal "
           "must be made to the District Court') was scored 0.51 by the NLI model and contributed 0, so mean "
           "VCS 0.5 < 0.6. Over-strict NLI/threshold on a correct claim; not changed."),
    "C1": ("FALSE_ABSTAIN", None,
           "Retrieval: the 12 context chunks were 9 HALO and 3 NDA_7, with no Helu Kabel chunk at all (p18 missing), so "
           "the model correctly said it lacked the Helu term. The pipeline retrieves one pool for the whole "
           "question; a cross-document question gets crowded by one document. Not changed."),
    "C2": ("OTHER", [True, True],
           "Verified with VCS 1.00, and both shown claims are correct and correctly cited (German law excl. "
           "CISG, D1 clause 11; California, D3 section 7). But only 2 of the 3 asked-for agreements are "
           "answered: NDA_7::p21 (Spain) was not retrieved, the model's line 'INSUFFICIENT_CONTEXT: ... 28 "
           "March 2014 NDA is not stated' carried no citation and was silently dropped from the displayed "
           "answer, so the UI shows a Verified answer that looks complete. Not a hallucination; an "
           "incompleteness the user is not told about."),
    "U1": ("CORRECT_ABSTAIN", None, "No liquidated-damages clause; abstained."),
    "U2": ("OTHER", None,
           "Routed to the general-knowledge path because 'What is the maximum ...' looks definitional and the "
           "question had no document marker; the model then replied 'that isn't a general legal-concept "
           "question' under a 'General knowledge' badge. No false fact was shown, but the user got a refusal "
           "labelled as a general-knowledge answer instead of an abstention. Routing bug, fixed in fb7bf75."),
    "U3": ("CORRECT_ABSTAIN", None, "No geographic scope in the amendment; abstained."),
    "G1": ("CORRECT_GENERAL", None, "Accurate four-sentence definition, labelled general knowledge."),
    "G2": ("CORRECT_GENERAL", None, "Accurate mutual vs one-way explanation, labelled general knowledge."),
    "F1": ("CORRECT_ABSTAIN", None, "No arbitration/Singapore; abstained, did not confirm the premise."),
    "F2": ("CORRECT_ABSTAIN", None,
           "Abstained, and the abstention text corrects the premise: the Act only specifies ninety days."),
    "P1": ("CORRECT_VERIFIED", [True],
           "Paraphrase with none of the Act's key words; answered six months' rent, cited s7:a."),
}

RERUN_JUDGED = {
    "S1": ("FALSE_ABSTAIN", [True, True],
           "The model used normal brackets this time, so the parser fix was not exercised live. Both claims "
           "correct and cite p18; claim 2 ENTAILS, but claim 1 ('The Helu Kabel confidentiality agreement is "
           "valid for three years...') was NEUTRAL: p18 never names Helu Kabel (only the header chunk p1 does), "
           "so NLI would not confirm the entity. VCS 0.5 < 0.6. Same over-strict NLI pattern as S5."),
    "S4": ("CORRECT_VERIFIED", [True, True], "Now Verified, VCS 1.00, both claims cite the preamble chunk p1."),
    "U2": ("CORRECT_ABSTAIN", None, "Now stays on the verified path and abstains (no rent-increase provision)."),
}


def main() -> None:
    questions = {q["id"]: q for q in json.loads((HERE / "questions.json").read_text(encoding="utf-8"))["questions"]}
    raw = json.loads((HERE / "raw_run.json").read_text(encoding="utf-8"))
    rerun = json.loads((HERE / "raw_rerun.json").read_text(encoding="utf-8"))
    replay = json.loads((HERE / "replay_fixed.json").read_text(encoding="utf-8"))

    def row(q: dict, judged: dict) -> dict:
        label, support, note = judged[q["id"]]
        spec = questions[q["id"]]
        return {
            "id": q["id"], "category": spec["category"], "question": spec["question"],
            "expected_behaviour": spec["expected_behaviour"], "expected_answer": spec["expected_answer"],
            "source": spec["source"],
            "badge": q.get("badge"), "vcs": q.get("vcs"), "http_status": q["status"],
            "attempts": q["attempts"], "seconds": q["seconds"],
            "answer_text": q.get("answer_text"), "grounded_answer_text": q.get("grounded_answer_text"),
            "claims": [{"claim_text": c["claim_text"], "cited": c["cited"], "quoted_span": c["quoted_span"],
                        "vcs_contribution": c["vcs_contribution"], "verdicts": c["verdicts"]}
                       for c in q.get("claims", [])],
            "context_chunk_ids": q.get("context_chunk_ids"),
            "quote_supports_claim": support, "label": label, "note": note,
            "screenshots": [s for s in (q.get("screenshot"), q.get("proof_screenshot")) if s],
        }

    rows = [row(q, JUDGED) for q in raw["questions"]]
    rerun_rows = [row(q, RERUN_JUDGED) for q in rerun["questions"]]
    after = {r["id"]: r for r in rows} | {r["id"]: r for r in rerun_rows}

    secs = [r["seconds"] for r in rows]
    results = {
        "run": {"started": raw["started"], "finished": raw["finished"], "llm": raw["health"]["llm"],
                "index": "data/lancedb_lc_e2e (fresh)", "judging": "each answer compared with the pre-written "
                "expected answer and source passage in questions.json (commit 2ea519d, before the run)"},
        "summary": {
            "labels_before_fixes": dict(Counter(r["label"] for r in rows)),
            "labels_after_fixes": dict(Counter(r["label"] for r in after.values())),
            "labels_by_category_before": {c: dict(Counter(r["label"] for r in rows if r["category"] == c))
                                          for c in dict.fromkeys(r["category"] for r in rows)},
            "query_latency_s": {"n": len(secs), "mean": round(statistics.mean(secs), 2),
                                "median": round(statistics.median(secs), 2),
                                "min": min(secs), "max": max(secs)},
            "http_errors_or_retries": sum(len(r["attempts"]) - 1 + (r["http_status"] != 200) for r in rows),
        },
        "ingest": [{"doc": i["doc"], "file": i["file"], "status": i["status"], "seconds": i["seconds"],
                    "chunks": i["body"].get("new_chunk_count"), "used_fallback": i["body"].get("used_fallback"),
                    "chunking": "paragraph fallback" if i["body"].get("used_fallback") else "SAC (Act/Section)",
                    "source_id": i["body"].get("source_id"), "screenshot": i["screenshot"]} for i in raw["ingest"]],
        "edge_cases": {
            "duplicate": {"status": raw["edge_cases"]["duplicate"]["status"],
                          "detail": raw["edge_cases"]["duplicate"]["body"].get("detail"),
                          "warning_shown": raw["edge_cases"]["duplicate"]["warning_shown"],
                          "replace_button_visible": raw["edge_cases"]["duplicate"]["replace_button_visible"],
                          "screenshot": raw["edge_cases"]["duplicate"]["screenshot"]},
            "replace": {"status": raw["edge_cases"]["replace"]["status"],
                        "chunks": raw["edge_cases"]["replace"]["body"].get("new_chunk_count"),
                        "same_chunk_count_as_first_ingest": raw["edge_cases"]["replace_same_chunk_count"],
                        "seconds": raw["edge_cases"]["replace"]["seconds"],
                        "screenshot": raw["edge_cases"]["replace"]["screenshot"]},
            "home_after_ingest": raw["edge_cases"]["home_after_ingest"],
        },
        "questions": rows,
        "search": raw["search"],
        "app": raw["app"],
        "fixes": [
            {"commit": "6b6a0f5", "bug": "comma inside a source id split the citation", "questions": ["S4"],
             "test": "tests/generation/test_parser.py::test_extract_keeps_a_comma_inside_the_source_id (+ lc parity case)"},
            {"commit": "f7f8dd9", "bug": "full-width citation brackets 【】 not recognised", "questions": ["S1"],
             "test": "tests/generation/test_parser.py::test_full_width_brackets_are_citations (+ lc parity case)"},
            {"commit": "fb7bf75", "bug": "'... under the <Act>?' routed to general knowledge", "questions": ["U2"],
             "test": "tests/generation/test_general_knowledge.py (U2 question added to DOCUMENT_SPECIFIC)"},
        ],
        "rerun_after_fixes": {"git_head": rerun["git_head"], "index": "data/lancedb_lc_e2e_rerun (fresh, same 5 docs via the Ingest page)",
                              "ingest": rerun["ingest"], "questions": rerun_rows},
        "replay_of_recorded_outputs": replay,
    }
    (HERE / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results["summary"], indent=2))


if __name__ == "__main__":
    main()
