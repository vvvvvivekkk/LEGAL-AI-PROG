"""Acceptance criterion 4: /query latency, LangChain vs plain Python.

Starts both APIs side by side on their own isolated indexes (src on :8000 from
.venv, lc on :8001 from .venv-lc), ingests data/sample/*.txt into each through
/ingest, warms each with one query, then asks the 10 labelled questions
ROUNDS times with reranking on. Requests alternate between the two servers and
the order flips every question, so LLM-provider drift during the session hits
both arms equally. Wall-clock time per request is measured client-side.

    .venv-lc/Scripts/python -m lc.eval.latency_eval

Writes experiments/langchain_port/latency/{config,results}.json.
"""

from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
import time
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[2]
SAMPLE = REPO / "data" / "sample"
QUERYSET = REPO / "data" / "eval" / "retrieval_queryset.json"
OUT = REPO / "experiments" / "langchain_port" / "latency"
ROUNDS = 2
BODY = {"rerank": True, "self_consistency": 0, "allow_general_knowledge": True}

ARMS = {
    "python": {"port": 8000, "python": REPO / ".venv" / "Scripts" / "python.exe",
               "app": "src.api.main:app", "env": {"LEGAL_AI_DB_PATH": "data/lancedb_latency_py",
                                                   "LEGAL_AI_CHATS_DIR": "data/chats_latency_py"}},
    "langchain": {"port": 8001, "python": REPO / ".venv-lc" / "Scripts" / "python.exe",
                  "app": "lc.api:app", "env": {"LEGAL_AI_LC_DB_PATH": "data/lancedb_latency_lc",
                                                "LEGAL_AI_LC_CHATS_DIR": "data/chats_latency_lc"}},
}


def _start(arm: dict) -> subprocess.Popen:
    for path in arm["env"].values():
        shutil.rmtree(REPO / path, ignore_errors=True)
    log = open(OUT / f"server_{arm['port']}.log", "w", encoding="utf-8")  # noqa: SIM115
    return subprocess.Popen(
        [str(arm["python"]), "-m", "uvicorn", arm["app"], "--port", str(arm["port"])],
        cwd=REPO, env={**os.environ, **arm["env"]}, stdout=log, stderr=subprocess.STDOUT,
    )


def _wait(client: httpx.Client, port: int, timeout: float = 180) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if client.get(f"http://127.0.0.1:{port}/health").status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise RuntimeError(f"server on :{port} did not come up")


def _ask(client: httpx.Client, port: int, question: str) -> dict:
    start = time.perf_counter()
    resp = client.post(f"http://127.0.0.1:{port}/query", json={"query": question, **BODY})
    elapsed = time.perf_counter() - start
    row = {"status": resp.status_code, "latency_s": elapsed}
    if resp.status_code == 200:
        body = resp.json()
        row["decision"] = body.get("decision") or body.get("status")
        row["vcs"] = body.get("vcs")
    else:
        row["error"] = resp.text[:300]
    return row


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    questions = [q["query"] for q in json.loads(QUERYSET.read_text(encoding="utf-8"))["queries"]]
    procs = {name: _start(arm) for name, arm in ARMS.items()}
    rows: list[dict] = []
    try:
        with httpx.Client(timeout=600) as client:
            for name, arm in ARMS.items():
                _wait(client, arm["port"])
                for path in sorted(SAMPLE.glob("*.txt")):
                    r = client.post(f"http://127.0.0.1:{arm['port']}/ingest",
                                    files={"file": (path.name, path.read_bytes(), "text/plain")})
                    r.raise_for_status()
                print(f"{name}: ingested, warming")
                _ask(client, arm["port"], questions[0])

            order = list(ARMS)
            for rnd in range(ROUNDS):
                for i, question in enumerate(questions):
                    for name in (order if (i + rnd) % 2 == 0 else order[::-1]):
                        row = _ask(client, ARMS[name]["port"], question)
                        row.update({"arm": name, "round": rnd, "query": question})
                        rows.append(row)
                        print(f"r{rnd} q{i} {name:<9} {row['status']} {row['latency_s']:.2f}s "
                              f"{row.get('decision')}")
    finally:
        for p in procs.values():
            p.terminate()
        for p in procs.values():
            p.wait(timeout=30)
        for arm in ARMS.values():
            for path in arm["env"].values():
                shutil.rmtree(REPO / path, ignore_errors=True)

    summary = {}
    for name in ARMS:
        ok = [r["latency_s"] for r in rows if r["arm"] == name and r["status"] == 200]
        summary[name] = {
            "n_ok": len(ok),
            "n_failed": sum(1 for r in rows if r["arm"] == name and r["status"] != 200),
            "mean_s": statistics.mean(ok) if ok else None,
            "median_s": statistics.median(ok) if ok else None,
            "stdev_s": statistics.stdev(ok) if len(ok) > 1 else None,
        }
    py, lc = summary["python"]["mean_s"], summary["langchain"]["mean_s"]
    summary["langchain_vs_python_mean"] = (lc / py - 1) if py and lc else None
    (OUT / "config.json").write_text(json.dumps(
        {"questions": str(QUERYSET.relative_to(REPO)), "rounds": ROUNDS, "request": BODY,
         "corpus": "data/sample/*.txt", "llm_provider": os.environ.get("LLM_PROVIDER"),
         "arms": {n: {"port": a["port"], "app": a["app"]} for n, a in ARMS.items()}}, indent=2),
        encoding="utf-8")
    (OUT / "results.json").write_text(json.dumps({"summary": summary, "requests": rows}, indent=2),
                                      encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
