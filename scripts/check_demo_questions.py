"""Ingest the criminal-law demo pack and ask every question in it, through the API.

Uses the same endpoints as the web app, so run it against a backend that is up
(start.bat, or `uvicorn lc.api:app`):

    python scripts/check_demo_questions.py
    python scripts/check_demo_questions.py --only V1,E5,U1      # a few questions
    python scripts/check_demo_questions.py --skip-ingest        # files already uploaded

For every question it prints the badge, the VCS, the cited chunks and a verdict:
  PASS             verified and cites the expected section (or refused / general
                   knowledge when that is what the question expects)
  CHECK            verified, but cites a different chunk; read the answer
  FALSE_REFUSAL    the expected section was retrieved but the answer was not verified
  RETRIEVAL_MISS   the expected section never reached the model
  FAIL             a refusal test was answered as Verified, or a general question was not
Results are also written to data/processed/demo_crime_check.json (gitignored).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "data" / "demo_crime"
OUT = ROOT / "data" / "processed" / "demo_crime_check.json"
GROUNDED = {"verified", "paraphrase", "easy"}


def ingest_all(client: httpx.Client) -> None:
    for path in sorted(PACK.glob("*.txt")):
        with path.open("rb") as fh:
            r = client.post("/ingest", files={"file": (path.name, fh, "text/plain")})
        if r.status_code == 200:
            body = r.json()
            how = "paragraph fallback" if body.get("used_fallback") else "SAC"
            print(f"  ingested  {path.name}: {body['new_chunk_count']} chunks ({how})")
        elif r.status_code == 409:
            print(f"  already   {path.name}")
        else:
            sys.exit(f"  ERROR {r.status_code} on {path.name}: {r.text[:300]}")


def ask(client: httpx.Client, question: str) -> tuple[dict, float]:
    payload = {"query": question, "k": 12, "rerank": True}
    for attempt in range(2):
        start = time.perf_counter()
        r = client.post("/query", json=payload)
        took = time.perf_counter() - start
        if r.status_code == 200:
            return r.json(), took
        if r.status_code in (429, 503) and attempt == 0:
            print(f"    {r.status_code} from the backend (rate limit or provider); retrying in 30 s")
            time.sleep(30)
            continue
        return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}, took
    return {"error": "no response"}, 0.0


def judge(q: dict, res: dict) -> str:
    if "error" in res:
        return "ERROR"
    mode = res.get("answer_mode", "verified")
    cited = {cid for c in res["proof"]["claims"] for cid in c["supporting_chunk_ids"]}
    if q["type"] in GROUNDED:
        if mode == "verified" and not res["abstained"]:
            return "PASS" if q["gold"] in cited else "CHECK"
        return "FALSE_REFUSAL" if q["gold"] in res["context_chunk_ids"] else "RETRIEVAL_MISS"
    if q["type"] == "general":
        return "PASS" if mode == "general_knowledge" else "FAIL"
    # false_premise / unanswerable: must not be shown as Verified. A verified answer
    # to a false premise may be a correction, so a person has to read it.
    if mode == "verified" and not res["abstained"]:
        return "CHECK" if q["type"] == "false_premise" else "FAIL"
    return "PASS"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--only", help="comma-separated question ids, e.g. V1,E5")
    ap.add_argument("--skip-ingest", action="store_true")
    ap.add_argument("--delay", type=float, default=2.0, help="seconds between questions")
    args = ap.parse_args()

    questions = json.loads((PACK / "questions.json").read_text(encoding="utf-8"))
    if args.only:
        wanted = {x.strip() for x in args.only.split(",")}
        questions = [q for q in questions if q["id"] in wanted]

    with httpx.Client(base_url=args.base, timeout=180) as client:
        try:
            client.get("/health").raise_for_status()
        except httpx.HTTPError as exc:
            sys.exit(f"Backend not reachable at {args.base} ({exc}). Start it with start.bat first.")
        if not args.skip_ingest:
            print("Ingesting the demo pack:")
            ingest_all(client)
        stats = client.get("/stats").json()
        print(f"Index: {stats}\n")

        results = []
        for i, q in enumerate(questions, 1):
            res, took = ask(client, q["q"])
            verdict = judge(q, res)
            cited = sorted({cid for c in res.get("proof", {}).get("claims", []) for cid in c["supporting_chunk_ids"]})
            vcs = res.get("vcs")
            print(f"[{i}/{len(questions)}] {q['id']:4} {verdict:14} {res.get('answer_mode', '-'):17} "
                  f"VCS {('%.2f' % vcs) if vcs is not None else '—':4}  {took:5.1f}s  {q['q']}")
            if verdict != "PASS":
                print(f"         expected: {q['expect']}")
                print(f"         got:      {(res.get('answer_text') or res.get('error', ''))[:300]}")
                print(f"         cited:    {', '.join(cited) or '—'}   (expected {q['gold'] or '—'})")
            results.append({**q, "verdict": verdict, "seconds": round(took, 2), "answer_mode": res.get("answer_mode"),
                            "vcs": vcs, "answer_text": res.get("answer_text"), "cited": cited,
                            "error": res.get("error")})
            time.sleep(args.delay)

    counts = Counter(r["verdict"] for r in results)
    print("\nSummary:", ", ".join(f"{k} {v}" for k, v in counts.most_common()), f"(of {len(results)})")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"base": args.base, "index": stats, "counts": counts, "results": results},
                              indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
