"""Rerunnable end-to-end batch check driven through the real UI with Playwright.

Ingests a set of real ContractNLI agreements through the Ingest *page* (not the
API directly), then asks a mix of document-specific and general conceptual
questions through the Ask *page*, and records for every question:

  * the outcome -- verified / abstained / general-knowledge fallback
  * the VCS, when the answer was verified
  * whether the citations point at the document that actually contains the
    answer (each specific question declares its expected source file)

Everything runs against an isolated LanceDB under --db, so a run never touches
the working index. Both servers are started and stopped by this script.

Usage:
    python scripts/batch_ask_check.py                  # full run
    python scripts/batch_ask_check.py --headed         # watch it happen
    python scripts/batch_ask_check.py --keep-index     # reuse a previous index

Requires: pip install playwright && python -m playwright install chromium
and a working LLM backend (LLM_PROVIDER / GEMINI_API_KEY in .env).
"""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

CORPUS = REPO_ROOT / "data" / "corpus" / "civil_law" / "contractnli" / "contract-nli" / "raw"
DEFAULT_DB = REPO_ROOT / "data" / "lancedb_batch"
DEFAULT_OUT = REPO_ROOT / "experiments" / "batch_ask_check"

# Ten real agreements from the ContractNLI raw corpus. The five specific
# questions below are drawn from clauses actually present in the first three.
FILES = [
    "1013322_0000912057-00-023405_document_2.txt",       # Yahoo! / Restrac
    "1013687_0000950144-96-001973_document_37.txt",      # Phoenix International
    "1012459_0000912057-97-027209_document_4.txt",       # Federal Express / IBS
    "1002276_0001036050-99-002047_document_13.txt",
    "1010471_0000950134-97-006281_document_5.txt",
    "1011671_0000936392-99-000246_document_46.txt",
    "1013687_0000950144-96-001973_document_38.txt",
    "1014959_0000950116-96-000618_document_7.txt",
    "1016503_0000929624-00-000894_0010.txt",
    "1017358_0001017358-97-000002_document_4.txt",
]


@dataclass
class Question:
    text: str
    kind: str  # "specific" | "general"
    # Source stem whose chunks should be cited, for specific questions.
    expected_source: str | None = None
    # A phrase the answer should contain if it found the right clause.
    expects_phrase: str | None = None


QUESTIONS = [
    # --- Specific: each answerable from a clause in a named ingested file ----
    Question(
        "Which state's laws govern the mutual nondisclosure agreement between Yahoo! Inc. and Restrac?",
        "specific",
        expected_source="1013322_0000912057-00-023405_document_2",
        expects_phrase="california",
    ),
    Question(
        "Under the Yahoo and Restrac agreement, within how many days must Confidential Information "
        "disclosed orally be confirmed in writing to the recipient?",
        "specific",
        expected_source="1013322_0000912057-00-023405_document_2",
        expects_phrase="thirty",
    ),
    Question(
        "According to the agreements, what is Residual Information and may the receiving party use it?",
        "specific",
        expected_source="1013322_0000912057-00-023405_document_2",
        expects_phrase="residual",
    ),
    Question(
        "In the Phoenix International agreement, whose prior written authorization is required before "
        "a party may disclose Confidential Information?",
        "specific",
        expected_source="1013687_0000950144-96-001973_document_37",
        expects_phrase="officer",
    ),
    Question(
        "Which two companies are the parties to the mutual non-disclosure agreement involving "
        "Federal Express Corporation?",
        "specific",
        expected_source="1012459_0000912057-97-027209_document_4",
        expects_phrase="international billing",
    ),
    # --- General: conceptual, not about the corpus --------------------------
    Question("What is a non-disclosure agreement?", "general"),
    Question("What is confidential information?", "general"),
    Question("Define a mutual NDA.", "general"),
    Question("What does consideration mean in contract law?", "general"),
    Question("Explain what injunctive relief is.", "general"),
]


@dataclass
class Result:
    question: str
    kind: str
    outcome: str = "error"  # verified | abstained | general_knowledge | error
    vcs: float | None = None
    cited_sources: list[str] = field(default_factory=list)
    citation_ok: str = "n/a"  # yes | no | n/a
    phrase_ok: str = "n/a"
    note: str = ""


# ---------------------------------------------------------------------------
# Server management
# ---------------------------------------------------------------------------

def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for(url: str, timeout: float = 180.0) -> bool:
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status < 500:
                    return True
        except (urllib.error.URLError, OSError):
            time.sleep(1)
    return False


class Servers:
    """Starts uvicorn + the Vite dev server, and stops them on exit."""

    def __init__(self, db_path: Path, log_dir: Path, model: str | None = None):
        self.db_path = db_path
        self.log_dir = log_dir
        self.model = model
        self.api_port = _free_port()
        self.web_port = _free_port()
        self.procs: list[subprocess.Popen] = []
        self.api_url = f"http://127.0.0.1:{self.api_port}"
        self.web_url = f"http://127.0.0.1:{self.web_port}"

    def __enter__(self) -> "Servers":
        import os

        self.log_dir.mkdir(parents=True, exist_ok=True)
        api_env = {
            **os.environ,
            "LEGAL_AI_DB_PATH": str(self.db_path),
            **({"LLM_MODEL": self.model} if self.model else {}),
            # The UI runs on an ephemeral port, which is not in the API's
            # default dev origins -- without this every request fails preflight.
            "LEGAL_AI_CORS_ORIGINS": f"http://127.0.0.1:{self.web_port},http://localhost:{self.web_port}",
        }
        api_log = open(self.log_dir / "uvicorn.log", "w", encoding="utf-8")
        self.procs.append(
            subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "src.api.main:app",
                 "--host", "127.0.0.1", "--port", str(self.api_port)],
                cwd=REPO_ROOT, env=api_env, stdout=api_log, stderr=subprocess.STDOUT,
            )
        )
        print(f"  api  -> {self.api_url}  (index: {self.db_path})")

        web_env = {**os.environ, "VITE_API_BASE": self.api_url}
        web_log = open(self.log_dir / "vite.log", "w", encoding="utf-8")
        npm = shutil.which("npm") or shutil.which("npm.cmd")
        if npm is None:
            raise RuntimeError("npm not found on PATH — cannot start the UI")
        self.procs.append(
            subprocess.Popen(
                # Bind explicitly: Vite's default "localhost" can resolve to ::1
                # only, which a 127.0.0.1 health check never reaches.
                [npm, "run", "dev", "--",
                 "--host", "127.0.0.1", "--port", str(self.web_port), "--strictPort"],
                cwd=REPO_ROOT / "web", env=web_env, stdout=web_log,
                stderr=subprocess.STDOUT, shell=False,
            )
        )
        print(f"  web  -> {self.web_url}")

        if not _wait_for(f"{self.api_url}/health"):
            raise RuntimeError(f"API never came up — see {self.log_dir / 'uvicorn.log'}")
        if not _wait_for(self.web_url):
            raise RuntimeError(f"UI never came up — see {self.log_dir / 'vite.log'}")
        return self

    def __exit__(self, *exc) -> None:
        for p in self.procs:
            p.terminate()
        for p in self.procs:
            try:
                p.wait(timeout=15)
            except subprocess.TimeoutExpired:
                p.kill()


# ---------------------------------------------------------------------------
# UI drivers
# ---------------------------------------------------------------------------

def ingest_files(page, web_url: str, paths: list[Path]) -> list[tuple[str, str]]:
    """Upload each file through the Ingest page. Returns (filename, status)."""
    out = []
    for path in paths:
        page.goto(f"{web_url}/ingest", wait_until="domcontentloaded")
        page.wait_for_selector("input[type=file]", state="attached", timeout=60_000)
        page.set_input_files("input[type=file]", str(path))

        # Read the real HTTP outcome rather than scraping the rendered text.
        try:
            with page.expect_response(
                lambda r: "/ingest" in r.url and r.request.method == "POST", timeout=300_000
            ) as got:
                page.get_by_role("button", name="Ingest and index").click()
            response = got.value
        except Exception as exc:  # noqa: BLE001 - record and keep going
            out.append((path.name, f"timeout ({type(exc).__name__})"))
            continue

        if response.status == 200:
            out.append((path.name, "indexed"))
        elif response.status == 409:
            out.append((path.name, "duplicate"))
        else:
            out.append((path.name, f"failed {response.status}"))
        print(f"    {out[-1][1]:>9}  {path.name}", flush=True)
    return out


def ask(page, web_url: str, question: Question, api_url: str) -> tuple[Result, dict]:
    """Ask one question through the Ask page and read the rendered outcome."""
    result = Result(question=question.text, kind=question.kind)

    page.goto(f"{web_url}/ask", wait_until="domcontentloaded")
    box = page.get_by_placeholder("Ask about a statute")
    box.wait_for(state="visible", timeout=60_000)
    box.fill(question.text)

    with page.expect_response(
        lambda r: "/query" in r.url and r.request.method == "POST", timeout=300_000
    ) as got:
        page.locator("form button[type=submit]").click()
    response = got.value

    if response.status != 200:
        detail = ""
        try:
            detail = str(response.json().get("detail", ""))
        except Exception:  # noqa: BLE001 - non-JSON error body
            pass
        result.note = f"HTTP {response.status} {detail}"[:160]
        # A rate-limited or unavailable backend is not a pipeline result --
        # call it out so it is never mistaken for an abstention.
        result.outcome = "backend_error" if response.status == 503 else "error"
        return result, {}

    body = response.json()
    result.outcome = body.get("answer_mode", "verified")
    result.vcs = body.get("vcs")

    cited = []
    for claim in body.get("proof", {}).get("claims", []):
        for cid in claim.get("supporting_chunk_ids", []):
            source = cid.split("::")[0]
            if source not in cited:
                cited.append(source)
    result.cited_sources = cited

    if question.kind == "specific":
        if result.outcome == "verified":
            result.citation_ok = "yes" if question.expected_source in cited else "no"
        else:
            result.citation_ok = "n/a"
        if question.expects_phrase:
            text = (body.get("answer_text") or "").lower()
            result.phrase_ok = "yes" if question.expects_phrase in text else "no"

    # Let the answer finish animating in before any screenshot is taken.
    page.wait_for_timeout(1200)
    return result, body


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_table(results: list[Result]) -> None:
    headers = ["#", "Kind", "Question", "Outcome", "VCS", "Cite OK", "Phrase", "Cited source"]
    rows = []
    for i, r in enumerate(results, 1):
        rows.append([
            str(i),
            r.kind,
            r.question if len(r.question) <= 58 else r.question[:55] + "...",
            r.outcome,
            f"{r.vcs:.2f}" if r.vcs is not None else "-",
            r.citation_ok,
            r.phrase_ok,
            (r.cited_sources[0][:34] if r.cited_sources else "-"),
        ])

    widths = [max(len(h), *(len(row[c]) for row in rows)) for c, h in enumerate(headers)]
    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    print("\n" + line)
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(cell.ljust(w) for cell, w in zip(row, widths)))

    specific = [r for r in results if r.kind == "specific"]
    general = [r for r in results if r.kind == "general"]
    print(
        f"\nspecific: {sum(r.outcome == 'verified' for r in specific)}/{len(specific)} verified, "
        f"{sum(r.citation_ok == 'yes' for r in specific)}/{len(specific)} cited the expected document"
    )
    print(
        f"general:  {sum(r.outcome == 'general_knowledge' for r in general)}/{len(general)} "
        f"used the general-knowledge fallback, "
        f"{sum(r.outcome == 'abstained' for r in general)} abstained, "
        f"{sum(r.outcome == 'verified' for r in general)} answered from documents"
    )


def write_report(path: Path, results: list[Result], ingested: list[tuple[str, str]],
                 model: str | None) -> None:
    """Write a committable markdown summary next to results.json."""
    import datetime

    specific = [r for r in results if r.kind == "specific"]
    general = [r for r in results if r.kind == "general"]
    lines = [
        "# Batch Ask check",
        "",
        f"Run: {datetime.date.today().isoformat()}  ",
        f"Model: `{model or 'default (LLM_MODEL/.env)'}`  ",
        f"Driver: `scripts/batch_ask_check.py` (Playwright, real Ingest + Ask pages)",
        "",
        "## Ingestion",
        "",
        "| file | status |",
        "|---|---|",
    ]
    lines += [f"| `{f}` | {status} |" for f, status in ingested]
    lines += [
        "",
        "## Questions",
        "",
        "| # | kind | question | outcome | VCS | cited expected doc | expected phrase |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(results, 1):
        vcs = f"{r.vcs:.2f}" if r.vcs is not None else "-"
        note = f" <br>`{r.note}`" if r.note else ""
        lines.append(
            f"| {i} | {r.kind} | {r.question}{note} | **{r.outcome}** | {vcs} "
            f"| {r.citation_ok} | {r.phrase_ok} |"
        )
    lines += [
        "",
        "## Summary",
        "",
        f"- specific: {sum(r.outcome == 'verified' for r in specific)}/{len(specific)} verified, "
        f"{sum(r.citation_ok == 'yes' for r in specific)}/{len(specific)} cited the expected document",
        f"- general: {sum(r.outcome == 'general_knowledge' for r in general)}/{len(general)} "
        f"used the general-knowledge fallback, "
        f"{sum(r.outcome == 'abstained' for r in general)} abstained",
        f"- backend errors: {sum(r.outcome == 'backend_error' for r in results)}",
        "",
        "Screenshots of representative answers are in `screenshots/`.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB), help="LanceDB directory for this run")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="where to write results + screenshots")
    parser.add_argument("--headed", action="store_true", help="show the browser")
    parser.add_argument("--keep-index", action="store_true", help="reuse an existing index")
    parser.add_argument("--max-files", type=int, default=len(FILES), help="ingest only the first N files")
    parser.add_argument("--max-questions", type=int, default=len(QUESTIONS),
                        help="ask only the first N of each question kind")
    parser.add_argument("--model", default=None,
                        help="LLM_MODEL override for this run (free-tier quota is per model)")
    parser.add_argument("--pause", type=float, default=4.0,
                        help="seconds to wait between questions, to stay under rate limits")
    parser.add_argument("--question-retries", type=int, default=2,
                        help="re-ask a question this many extra times if the LLM backend 503s")
    parser.add_argument("--retry-wait", type=float, default=60.0,
                        help="seconds to wait before re-asking after a backend error")
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    db_path = Path(args.db)
    out_dir = Path(args.out)
    shots = out_dir / "screenshots"
    shots.mkdir(parents=True, exist_ok=True)

    if not args.keep_index and db_path.exists():
        shutil.rmtree(db_path)

    files = FILES[: args.max_files]
    if args.max_questions < len(QUESTIONS):
        half = max(1, args.max_questions // 2)
        specific = [q for q in QUESTIONS if q.kind == "specific"][:half]
        general = [q for q in QUESTIONS if q.kind == "general"][:half]
        questions = specific + general
    else:
        questions = QUESTIONS

    missing = [f for f in files if not (CORPUS / f).exists()]
    if missing:
        print(f"Missing corpus files: {missing}\nRun the corpus fetch script first.", file=sys.stderr)
        return 2

    print("Starting servers...")
    with Servers(db_path, out_dir / "logs", model=args.model) as servers:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=not args.headed)
            page = browser.new_page(viewport={"width": 1280, "height": 1000})

            print(f"\nIngesting {len(FILES)} agreements through the Ingest page...")
            ingested = ingest_files(page, servers.web_url, [CORPUS / f for f in files])

            print(f"\nAsking {len(questions)} questions through the Ask page...", flush=True)
            results: list[Result] = []
            bodies: list[dict] = []
            # One screenshot per outcome kind, the first time it occurs.
            captured: set[str] = set()
            for i, question in enumerate(questions, 1):
                result, body = ask(page, servers.web_url, question, servers.api_url)
                # A saturated free-tier backend 503s in bursts. Re-ask rather
                # than recording a backend error as if it were a pipeline result.
                for _ in range(args.question_retries):
                    if result.outcome != "backend_error":
                        break
                    print(f"        backend 503 — retrying in {args.retry_wait:.0f}s", flush=True)
                    time.sleep(args.retry_wait)
                    result, body = ask(page, servers.web_url, question, servers.api_url)
                results.append(result)
                bodies.append(body)
                print(f"    {i:>2}. [{result.outcome:^18}] {question.text[:62]}", flush=True)
                if result.note:
                    print(f"        {result.note}", flush=True)
                time.sleep(args.pause)
                if result.outcome not in captured and result.outcome not in ("error", "backend_error"):
                    captured.add(result.outcome)
                    page.screenshot(path=str(shots / f"{result.outcome}.png"), full_page=True)

            browser.close()

    print_table(results)

    payload = {
        "files": [{"file": f, "status": s} for f, s in ingested],
        "results": [
            {
                "question": r.question, "kind": r.kind, "outcome": r.outcome, "vcs": r.vcs,
                "cited_sources": r.cited_sources, "citation_ok": r.citation_ok,
                "phrase_ok": r.phrase_ok, "note": r.note,
            }
            for r in results
        ],
        "answers": [b.get("answer_text", "") for b in bodies],
    }
    (out_dir / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_report(out_dir / "report.md", results, ingested, args.model)
    print(f"\nresults  -> {out_dir / 'results.json'}")
    print(f"screenshots -> {shots}  ({', '.join(sorted(captured)) or 'none'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
