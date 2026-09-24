"""Human-style end-to-end run of Legal AI on the LangChain backend, driven through the UI.

Starts lc.api on :8001 on a fresh isolated index (data/lancedb_lc_e2e,
data/chats_lc_e2e) and the Vite UI on :5173 (web/.env -> :8001), then with
Playwright: ingests documents.json one by one on the Ingest page, re-uploads one
(duplicate -> Replace), checks Home counters, asks every question in
questions.json in its own new chat on the Ask page (opening every proof), runs
Search for three questions, screenshots Evaluation, checks chat history survives
a reload and a delete, deletes one document via the API and re-asks about it.

Every HTTP response the UI received is recorded as-is in raw_run.json; judging
against questions.json happens afterwards, by hand, in results.json/report.md.

    .venv/Scripts/python experiments/2026-09-24-human-e2e/run_e2e.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SHOTS = HERE / "screens"
LOGS = HERE / "logs"  # gitignored
RAW = HERE / "raw_run.json"
API = "http://localhost:8001"
WEB = "http://localhost:5173"
DB, CHATS = "data/lancedb_lc_e2e", "data/chats_lc_e2e"
PAUSE_S = 5          # between questions (Groq free tier)
RETRY_WAIT_S = 30    # one retry after a 429/503
DUPLICATE_DOC = "D1"
DELETE_DOC = "D3"
REASK_AFTER_DELETE = "S3"
SEARCH_QUESTIONS = {  # question id -> distinctive phrase of its gold passage
    "S1": "valid for three years",
    "S3": "entitled to equitable remedies",
    "S5": "within sixty days of the order",
}

run: dict = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "llm_provider": None,
             "ingest": [], "edge_cases": {}, "questions": [], "search": [], "app": {}}


def save() -> None:
    RAW.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")


def norm(text: str) -> str:
    # pypdf splits words with stray spaces ("signat ures"), so compare without any.
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def wait_up(url: str, timeout: float = 240) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5):
                return
        except OSError:
            time.sleep(1)
    raise RuntimeError(f"{url} never came up")


def home_counters(page) -> dict:
    page.goto(f"{WEB}/", wait_until="networkidle")
    page.wait_for_timeout(1500)
    text = page.inner_text("body")
    docs = re.search(r"(\d+)\s*documents indexed", text)
    chunks = re.search(r"(\d+)\s*chunks indexed", text)
    return {"documents": int(docs.group(1)) if docs else None,
            "chunks": int(chunks.group(1)) if chunks else None}


def ingest_via_ui(page, path: Path, shot: str) -> dict:
    page.goto(f"{WEB}/ingest", wait_until="domcontentloaded")
    page.wait_for_selector("input[type=file]", state="attached", timeout=60_000)
    page.set_input_files("input[type=file]", str(path))
    start = time.perf_counter()
    with page.expect_response(lambda r: "/ingest" in r.url and r.request.method == "POST",
                              timeout=600_000) as got:
        page.get_by_role("button", name="Ingest and index").click()
    resp = got.value
    elapsed = time.perf_counter() - start
    body = resp.json()
    page.wait_for_timeout(1500)
    page.screenshot(path=SHOTS / shot)
    return {"status": resp.status, "seconds": round(elapsed, 2), "body": body, "screenshot": f"screens/{shot}"}


def ask_via_ui(page, question: str, shot_prefix: str) -> dict:
    """New chat, type, submit; one retry on 429/503. Opens every citation's proof."""
    attempts = []
    for attempt in range(2):
        page.goto(f"{WEB}/ask", wait_until="domcontentloaded")
        page.get_by_role("button", name="+ New chat").click()
        box = page.get_by_placeholder("Ask about a statute")
        box.wait_for(state="visible", timeout=60_000)
        box.fill(question)
        start = time.perf_counter()
        with page.expect_response(lambda r: "/query" in r.url and r.request.method == "POST",
                                  timeout=600_000) as got:
            page.locator("form button[type=submit]").click()
        resp = got.value
        elapsed = time.perf_counter() - start
        try:
            body = resp.json()
        except Exception:  # noqa: BLE001
            body = {"raw": resp.text()[:500]}
        attempts.append({"status": resp.status, "seconds": round(elapsed, 2),
                         "detail": body.get("detail") if resp.status != 200 else None})
        if resp.status in (429, 503) and attempt == 0:
            time.sleep(RETRY_WAIT_S)
            continue
        break

    page.wait_for_timeout(2500)
    page.screenshot(path=SHOTS / f"{shot_prefix}-answer.png", full_page=True)
    out = {"attempts": attempts, "status": resp.status, "seconds": attempts[-1]["seconds"],
           "screenshot": f"screens/{shot_prefix}-answer.png"}
    if resp.status != 200:
        out["error"] = body
        return out

    text = page.inner_text("main") if page.locator("main").count() else page.inner_text("body")
    if body.get("answer_mode") == "general_knowledge":
        badge = "General knowledge"
    elif body.get("decision") == "ANSWER":
        badge = "Verified"
    else:
        badge = "Abstained"
    out.update({
        "badge": badge,
        "badge_text_on_page": {"Verified": "Verified" in text, "Abstained": "Abstained" in text,
                               "General knowledge": "General knowledge" in text},
        "decision": body.get("decision"), "answer_mode": body.get("answer_mode"),
        "vcs": body.get("vcs"), "answer_text": body.get("answer_text"),
        "grounded_answer_text": body.get("grounded_answer_text"),
        "context_chunk_ids": body.get("context_chunk_ids"),
        "claims": [{"claim_text": c["claim_text"], "cited": c["supporting_chunk_ids"],
                    "quoted_span": c.get("quoted_span"), "vcs_contribution": c.get("vcs_contribution"),
                    "verdicts": c.get("verdicts")} for c in (body.get("proof") or {}).get("claims", [])],
    })
    if badge == "Verified":
        buttons = page.locator("button[title='Show proof for this claim']")
        n = buttons.count()
        panels = page.get_by_text(re.compile(r"^contributes "))
        for i in range(n):
            # Every citation button of a claim toggles the same panel: if a click
            # closed one, click again so all panels end up open.
            opened = panels.count()
            buttons.nth(i).click()
            page.wait_for_timeout(500)
            if panels.count() < opened:
                buttons.nth(i).click()
                page.wait_for_timeout(500)
        out["proof_panels_open"] = panels.count()
        page.wait_for_timeout(800)
        page.screenshot(path=SHOTS / f"{shot_prefix}-proof.png", full_page=True)
        out["proof_buttons_opened"] = n
        out["proof_screenshot"] = f"screens/{shot_prefix}-proof.png"
    return out


def rerun(ids: list[str]) -> None:
    """After a fix: fresh index, same 5 documents through the Ingest page, then
    only the given questions, each in a new chat. Writes raw_rerun.json."""
    global RAW, DB, CHATS
    RAW, DB, CHATS = HERE / "raw_rerun.json", "data/lancedb_lc_e2e_rerun", "data/chats_lc_e2e_rerun"
    run["rerun_of"] = ids
    run["git_head"] = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                                     capture_output=True, text=True).stdout.strip()
    docs = json.loads((HERE / "documents.json").read_text(encoding="utf-8"))
    by_id = {q["id"]: q for q in json.loads((HERE / "questions.json").read_text(encoding="utf-8"))["questions"]}
    for path in (DB, CHATS):
        shutil.rmtree(REPO / path, ignore_errors=True)
    api, web = _start_servers()
    try:
        with sync_playwright() as p:
            page = p.chromium.launch().new_page(viewport={"width": 1440, "height": 1000})
            page.on("dialog", lambda d: d.accept())
            for d in docs:
                r = ingest_via_ui(page, REPO / d["path"], f"rerun-ingest-{d['id']}.png")
                run["ingest"].append({"doc": d["id"], "status": r["status"],
                                      "new_chunk_count": r["body"].get("new_chunk_count")})
            save()
            for qid in ids:
                r = ask_via_ui(page, by_id[qid]["question"], f"rerun-ask-{qid}")
                r["id"], r["question"] = qid, by_id[qid]["question"]
                run["questions"].append(r)
                save()
                print(f"rerun {qid}: {r['status']} {r.get('badge')} vcs={r.get('vcs')} {r['seconds']}s", flush=True)
                time.sleep(PAUSE_S)
    finally:
        run["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
        save()
        _stop_servers(api, web)


def _start_servers():
    api = subprocess.Popen(
        [str(REPO / ".venv-lc" / "Scripts" / "python.exe"), "-m", "uvicorn", "lc.api:app", "--port", "8001"],
        cwd=REPO, env={**os.environ, "LEGAL_AI_LC_DB_PATH": DB, "LEGAL_AI_LC_CHATS_DIR": CHATS},
        stdout=open(LOGS / "api.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT,  # noqa: SIM115
    )
    web = subprocess.Popen("npm run dev -- --port 5173 --strictPort", shell=True, cwd=REPO / "web",
                           stdout=open(LOGS / "vite.log", "w"), stderr=subprocess.STDOUT)  # noqa: SIM115
    wait_up(f"{API}/health")
    wait_up(WEB)
    run["health"] = json.loads(urllib.request.urlopen(f"{API}/health").read())
    return api, web


def _stop_servers(api, web) -> None:
    api.terminate()
    subprocess.run(f"taskkill /F /T /PID {web.pid}", shell=True, capture_output=True)
    try:
        api.wait(timeout=30)
    except subprocess.TimeoutExpired:
        api.kill()


def main() -> None:
    if "--rerun" in sys.argv:
        return rerun(sys.argv[sys.argv.index("--rerun") + 1].split(","))
    docs = json.loads((HERE / "documents.json").read_text(encoding="utf-8"))
    questions = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))["questions"]
    by_id = {q["id"]: q for q in questions}
    SHOTS.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    for path in (DB, CHATS):
        shutil.rmtree(REPO / path, ignore_errors=True)

    api = subprocess.Popen(
        [str(REPO / ".venv-lc" / "Scripts" / "python.exe"), "-m", "uvicorn", "lc.api:app", "--port", "8001"],
        cwd=REPO, env={**os.environ, "LEGAL_AI_LC_DB_PATH": DB, "LEGAL_AI_LC_CHATS_DIR": CHATS},
        stdout=open(LOGS / "api.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT,  # noqa: SIM115
    )
    web = subprocess.Popen("npm run dev -- --port 5173 --strictPort", shell=True, cwd=REPO / "web",
                           stdout=open(LOGS / "vite.log", "w"), stderr=subprocess.STDOUT)  # noqa: SIM115
    try:
        wait_up(f"{API}/health")
        wait_up(WEB)
        run["health"] = json.loads(urllib.request.urlopen(f"{API}/health").read())
        run["llm_provider"] = run["health"].get("llm", {}).get("provider")
        save()

        with sync_playwright() as p:
            page = p.chromium.launch().new_page(viewport={"width": 1440, "height": 1000})
            page.on("dialog", lambda d: d.accept())  # a stray confirm() must not hang the run

            # ---- Step 3: ingest one at a time -------------------------------
            for d in docs:
                r = ingest_via_ui(page, REPO / d["path"], f"ingest-{d['id']}.png")
                r["doc"] = d["id"]
                r["file"] = d["file"]
                run["ingest"].append(r)
                save()
                print(f"ingest {d['id']}: {r['status']} {r['body'].get('new_chunk_count')} chunks "
                      f"fallback={r['body'].get('used_fallback')} {r['seconds']}s", flush=True)
            source_ids = {r["doc"]: r["body"].get("source_id") for r in run["ingest"]}

            dup_doc = next(d for d in docs if d["id"] == DUPLICATE_DOC)
            dup = ingest_via_ui(page, REPO / dup_doc["path"], "edge-duplicate.png")
            replace_btn = page.get_by_role("button", name=re.compile("Replace existing document"))
            dup["replace_button_visible"] = replace_btn.count() > 0
            dup["warning_shown"] = "already in the index" in page.inner_text("body")
            replaced = None
            if dup["replace_button_visible"]:
                start = time.perf_counter()
                with page.expect_response(lambda r: "/ingest" in r.url and r.request.method == "POST",
                                          timeout=600_000) as got:
                    replace_btn.click()
                resp = got.value
                replaced = {"status": resp.status, "seconds": round(time.perf_counter() - start, 2),
                            "body": resp.json()}
                page.wait_for_timeout(1500)
                page.screenshot(path=SHOTS / "edge-replace.png")
                replaced["screenshot"] = "screens/edge-replace.png"
            first = next(r for r in run["ingest"] if r["doc"] == DUPLICATE_DOC)["body"]["new_chunk_count"]
            run["edge_cases"]["duplicate"] = dup
            run["edge_cases"]["replace"] = replaced
            run["edge_cases"]["replace_same_chunk_count"] = (
                replaced is not None and replaced["body"].get("new_chunk_count") == first)
            home = home_counters(page)
            page.screenshot(path=SHOTS / "home-after-ingest.png")
            api_stats = httpx.get(f"{API}/stats").json()
            run["edge_cases"]["home_after_ingest"] = {
                "ui": home, "api": {"documents": api_stats["documents"], "chunks": api_stats["chunks"]},
                "expected_chunks": sum(r["body"].get("new_chunk_count", 0) for r in run["ingest"]),
                "screenshot": "screens/home-after-ingest.png"}
            save()
            print("edge cases:", json.dumps({k: run["edge_cases"][k] for k in ("replace_same_chunk_count",
                                                                                "home_after_ingest")}), flush=True)

            # ---- Step 4: ask every question in its own new chat -------------
            for q in questions:
                r = ask_via_ui(page, q["question"], f"ask-{q['id']}")
                r["id"] = q["id"]
                r["question"] = q["question"]
                run["questions"].append(r)
                save()
                print(f"ask {q['id']}: {r['status']} {r.get('badge')} vcs={r.get('vcs')} {r['seconds']}s", flush=True)
                time.sleep(PAUSE_S)

            # ---- Step 6: Search ---------------------------------------------
            for qid, phrase in SEARCH_QUESTIONS.items():
                page.goto(f"{WEB}/search", wait_until="domcontentloaded")
                box = page.get_by_placeholder("How long does a landlord")
                box.wait_for(state="visible", timeout=60_000)
                box.fill(by_id[qid]["question"])
                with page.expect_response(lambda r: "/retrieve" in r.url, timeout=300_000) as got:
                    box.press("Enter")
                body = got.value.json()
                page.wait_for_timeout(2500)
                page.screenshot(path=SHOTS / f"search-{qid}.png", full_page=True)
                row = {"id": qid, "status": got.value.status, "gold_phrase": phrase,
                       "screenshot": f"screens/search-{qid}.png", "columns": {}}
                for name, hits in body.get("variants", {}).items():
                    ranks = [i + 1 for i, h in enumerate(hits) if norm(phrase) in norm(h.get("text"))]
                    row["columns"][name] = {"gold_rank": ranks[0] if ranks else None,
                                            "top_ids": [h.get("chunk_id") for h in hits]}
                run["search"].append(row)
                save()
                print(f"search {qid}:", {k: v["gold_rank"] for k, v in row["columns"].items()}, flush=True)

            # ---- Evaluation page --------------------------------------------
            page.goto(f"{WEB}/evaluation", wait_until="networkidle")
            page.wait_for_timeout(3000)
            page.screenshot(path=SHOTS / "evaluation.png")
            emap = httpx.get(f"{API}/embedding-map").json()
            run["app"]["evaluation"] = {"screenshot": "screens/evaluation.png",
                                        "map_sources": emap.get("sources"), "map_points": len(emap.get("points", []))}
            save()

            # ---- Chat history: reload, then delete one ----------------------
            page.goto(f"{WEB}/ask", wait_until="networkidle")
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(1500)
            delete_btns = page.locator("button[aria-label^='Delete conversation']")
            before = delete_btns.count()
            api_before = len(httpx.get(f"{API}/chats").json()["conversations"])
            page.screenshot(path=SHOTS / "chats-after-reload.png")
            victim = delete_btns.first.get_attribute("aria-label")
            with page.expect_response(lambda r: "/chats/" in r.url and r.request.method == "DELETE",
                                      timeout=60_000) as got:
                delete_btns.first.click()
            del_status = got.value.status
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(1500)
            after = page.locator("button[aria-label^='Delete conversation']").count()
            still_there = page.locator(f"button[aria-label=\"{victim}\"]").count()
            page.screenshot(path=SHOTS / "chats-after-delete.png")
            run["app"]["chat_history"] = {
                "chats_asked": sum(len(q["attempts"]) for q in run["questions"]),
                "ui_after_reload": before, "api_after_reload": api_before,
                "deleted": victim, "delete_status": del_status,
                "ui_after_delete_and_reload": after, "deleted_still_listed": still_there,
                "api_after_delete": len(httpx.get(f"{API}/chats").json()["conversations"]),
                "screenshots": ["screens/chats-after-reload.png", "screens/chats-after-delete.png"]}
            save()
            print("chats:", run["app"]["chat_history"], flush=True)

            # ---- Delete one document via the API ----------------------------
            before_home = home_counters(page)
            sid = source_ids[DELETE_DOC]
            resp = httpx.delete(f"{API}/documents/{sid}")
            after_home = home_counters(page)
            page.screenshot(path=SHOTS / "home-after-delete.png")
            time.sleep(PAUSE_S)
            reask = ask_via_ui(page, by_id[REASK_AFTER_DELETE]["question"], f"after-delete-{REASK_AFTER_DELETE}")
            run["app"]["delete_document"] = {
                "doc": DELETE_DOC, "source_id": sid, "status": resp.status_code, "body": resp.json(),
                "home_before": before_home, "home_after": after_home,
                "screenshot": "screens/home-after-delete.png",
                "reask": {"id": REASK_AFTER_DELETE, **reask}}
            save()
            print("delete doc:", resp.status_code, before_home, "->", after_home,
                  "reask:", reask.get("badge"), flush=True)
    finally:
        run["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
        save()
        api.terminate()
        subprocess.run(f"taskkill /F /T /PID {web.pid}", shell=True, capture_output=True)
        try:
            api.wait(timeout=30)
        except subprocess.TimeoutExpired:
            api.kill()


if __name__ == "__main__":
    sys.exit(main())
