"""Acceptance criterion 3: the React UI end to end against the LangChain API.

Starts lc.api on :8001 (isolated index) and the Vite dev server pointed at it
(VITE_API_BASE), then drives the UI with Playwright: ingest a PDF, ask a
question, open a proof, run a search, open Evaluation. One screenshot per step
in experiments/langchain_port/screens/, plus steps.json with the HTTP status
each step actually got.

    .venv/Scripts/python -m lc.eval.ui_screens      # needs playwright + chromium
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "experiments" / "langchain_port" / "screens"
API = "http://localhost:8001"
WEB = "http://localhost:5173"
DB = "data/lancedb_lc_ui"
CHATS = "data/chats_lc_ui"
PDF = REPO / "data" / "sample" / "6120f2b30278c05b292d2d55dd1667c1.pdf"
TXT = REPO / "data" / "sample" / "urban_tenancy_act_2019.txt"
QUESTION = "How long does a landlord have to refund a tenant's security deposit?"


def _wait(url: str, timeout: float = 180) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5):
                return
        except OSError:
            time.sleep(1)
    raise RuntimeError(f"{url} never came up")


def _ingest(page, path: Path) -> int:
    page.goto(f"{WEB}/ingest", wait_until="domcontentloaded")
    page.wait_for_selector("input[type=file]", state="attached", timeout=60_000)
    page.set_input_files("input[type=file]", str(path))
    with page.expect_response(lambda r: "/ingest" in r.url and r.request.method == "POST",
                              timeout=300_000) as got:
        page.get_by_role("button", name="Ingest and index").click()
    page.wait_for_timeout(1500)
    return got.value.status


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for path in (DB, CHATS):
        shutil.rmtree(REPO / path, ignore_errors=True)
    logs = OUT.parent / "logs"
    logs.mkdir(exist_ok=True)
    api = subprocess.Popen(
        [str(REPO / ".venv-lc" / "Scripts" / "python.exe"), "-m", "uvicorn", "lc.api:app", "--port", "8001"],
        cwd=REPO, env={**os.environ, "LEGAL_AI_LC_DB_PATH": DB, "LEGAL_AI_LC_CHATS_DIR": CHATS},
        stdout=open(logs / "ui_api.log", "w"), stderr=subprocess.STDOUT,  # noqa: SIM115
    )
    web = subprocess.Popen(
        "npm run dev -- --port 5173 --strictPort", shell=True, cwd=REPO / "web",
        env={**os.environ, "VITE_API_BASE": API},
        stdout=open(logs / "ui_vite.log", "w"), stderr=subprocess.STDOUT,  # noqa: SIM115
    )
    steps: dict[str, object] = {}
    try:
        _wait(f"{API}/health")
        _wait(WEB)
        with sync_playwright() as p:
            page = p.chromium.launch().new_page(viewport={"width": 1440, "height": 1000})

            steps["ingest_pdf"] = _ingest(page, PDF)
            page.screenshot(path=OUT / "1-ingest-pdf.png")  # full page is ~54k px of chunks
            steps["ingest_txt"] = _ingest(page, TXT)

            page.goto(f"{WEB}/ask", wait_until="domcontentloaded")
            box = page.get_by_placeholder("Ask about a statute")
            box.wait_for(state="visible", timeout=60_000)
            box.fill(QUESTION)
            with page.expect_response(lambda r: "/query" in r.url and r.request.method == "POST",
                                      timeout=300_000) as got:
                page.locator("form button[type=submit]").click()
            resp = got.value
            body = resp.json() if resp.status == 200 else {}
            steps["ask"] = {"status": resp.status, "decision": body.get("decision"),
                            "vcs": body.get("vcs"), "answer_mode": body.get("answer_mode")}
            page.wait_for_timeout(2000)
            page.screenshot(path=OUT / "2-ask.png", full_page=True)

            proof = page.locator("button[title='Show proof for this claim']").first
            steps["proof_button"] = proof.count() > 0
            if steps["proof_button"]:
                proof.click()
                page.wait_for_timeout(1200)
            page.screenshot(path=OUT / "3-proof.png", full_page=True)

            page.goto(f"{WEB}/search", wait_until="domcontentloaded")
            search = page.get_by_placeholder("How long does a landlord")
            search.wait_for(state="visible", timeout=60_000)
            search.fill(QUESTION)
            with page.expect_response(lambda r: "/retrieve" in r.url, timeout=300_000) as got:
                search.press("Enter")
            steps["search"] = got.value.status
            page.wait_for_timeout(3000)
            page.screenshot(path=OUT / "4-search.png", full_page=True)

            page.goto(f"{WEB}/evaluation", wait_until="networkidle")
            page.wait_for_timeout(2500)
            page.screenshot(path=OUT / "5-evaluation.png", full_page=True)
            steps["evaluation_loaded"] = True
    finally:
        api.terminate()
        subprocess.run(f"taskkill /F /T /PID {web.pid}", shell=True, capture_output=True)
        api.wait(timeout=30)
        for path in (DB, CHATS):
            shutil.rmtree(REPO / path, ignore_errors=True)
        (OUT / "steps.json").write_text(json.dumps(steps, indent=2), encoding="utf-8")
    print(json.dumps(steps, indent=2))


if __name__ == "__main__":
    main()
