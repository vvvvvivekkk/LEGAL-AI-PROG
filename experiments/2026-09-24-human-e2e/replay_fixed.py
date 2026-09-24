"""Replay the exact model outputs recorded for S1 and S4 in raw_run.json through
the fixed parser + V1-V6 verification (same chunks, real roberta-large-mnli).

The live rerun asks the LLM again, which may not reproduce the original output;
this shows what the fixes do to the answers that actually failed.

    PYTHONPATH=. .venv-lc/Scripts/python experiments/2026-09-24-human-e2e/replay_fixed.py
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from langchain_core.documents import Document

from lc.generation import CitationOutputParser
from lc.verification import verification_step
from src.verification.nli import RobertaMNLI

HERE = Path(__file__).resolve().parent
IDS = ("S1", "S4")


def main() -> None:
    run = json.loads((HERE / "raw_run.json").read_text(encoding="utf-8"))
    chunks = {c["chunk_id"]: c for i in run["ingest"] for c in i["body"].get("new_chunks", [])}
    step = verification_step(RobertaMNLI())
    out = {"git_head": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                                      text=True, cwd=HERE).stdout.strip(), "replays": []}
    for q in run["questions"]:
        if q["id"] not in IDS:
            continue
        context = [Document(page_content=chunks[cid]["text"],
                            metadata={"chunk_id": cid, "contextual_summary": chunks[cid]["contextual_summary"],
                                      "chunk_metadata": chunks[cid]["metadata"]})
                   for cid in q["context_chunk_ids"]]
        parsed = CitationOutputParser().parse(q["answer_text"])
        vr = step.invoke({"question": q["question"], "context": context, "parsed": parsed})
        row = {"id": q["id"], "before": {"badge": q["badge"], "vcs": q["vcs"]},
               "after": {"decision": vr.vcs_result.decision, "vcs": vr.vcs_result.vcs,
                         "claims": [{"text": c.text, "cited": c.cited_chunk_ids} for c in parsed.claims],
                         "per_claim_vcs": [c.vcs for c in vr.vcs_result.per_claim]}}
        out["replays"].append(row)
        print(row["id"], row["before"], "->", row["after"]["decision"], row["after"]["vcs"], row["after"]["per_claim_vcs"])
    (HERE / "replay_fixed.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
