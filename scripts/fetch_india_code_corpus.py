"""Download a starter corpus of real Indian Central Acts (PDF) from the official
Legislative Department listing, save them under data/corpus/india_code/, and
push to git ONLY if the total download size is under 500MB.

Run on a machine with real internet access:
    pip install requests
    python scripts/fetch_india_code_corpus.py

This is a utility script, not part of the pipeline -- it just populates
data/corpus/india_code/ with real files you can then ingest through the UI
or the batch ingestion command.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests

LISTING_URL = "https://legislative.gov.in/central-acts-updated/"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "corpus" / "india_code"
SIZE_LIMIT_BYTES = 500 * 1024 * 1024  # 500MB -- push only if the whole batch is under this

# Keywords used to pick a diverse ~25-30 act subset out of the ~800+ listed.
# Matching is case-insensitive substring against the link text on the listing page.
WANTED_KEYWORDS = [
    "indian contract act",
    "indian penal code",
    "code of criminal procedure",
    "code of civil procedure",
    "indian evidence act",
    "negotiable instruments act",
    "arbitration and conciliation act",
    "companies act",
    "information technology act",
    "consumer protection act",
    "right to information act",
    "competition act",
    "income-tax act",
    "environment (protection) act",
    "motor vehicles act",
    "minimum wages act",
    "factories act",
    "industrial disputes act",
    "maternity benefit act",
    "juvenile justice",
    "protection of women from domestic violence",
    "prevention of money-laundering act",
    "insolvency and bankruptcy code",
    "real estate (regulation and development) act",
    "digital personal data protection act",
    "sale of goods act",
    "specific relief act",
    "limitation act",
    "registration act",
    "transfer of property act",
]

PDF_LINK_RE = re.compile(r'href="([^"]+\.pdf)"[^>]*>([^<]*)</a>', re.IGNORECASE)


def discover_links() -> list[tuple[str, str]]:
    """Fetch the listing page and pull out (url, act_name) pairs matching our keywords.

    The exact HTML structure of legislative.gov.in isn't something I could verify from
    the sandbox that wrote this script (network-restricted) -- if this regex finds
    nothing, the page structure has likely changed or uses JS rendering; print the
    raw HTML snippet around any "act" mentions and adjust the regex/keyword matching,
    or fall back to browsing https://www.indiacode.nic.in/ manually for a few PDF
    handle URLs and hardcoding them in a FALLBACK_LINKS list below.
    """
    resp = requests.get(LISTING_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    html = resp.text

    found: list[tuple[str, str]] = []
    for match in PDF_LINK_RE.finditer(html):
        href, text = match.group(1), match.group(2).strip()
        haystack = (text + " " + href).lower()
        for kw in WANTED_KEYWORDS:
            if kw in haystack:
                found.append((urljoin(LISTING_URL, href), text or kw))
                break

    # de-dupe by URL, keep order
    seen = set()
    deduped = []
    for url, name in found:
        if url not in seen:
            seen.add(url)
            deduped.append((url, name))
    return deduped


def download_all(links: list[tuple[str, str]]) -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    saved = []
    for url, name in links:
        safe_name = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()[:80] or "act"
        dest = OUT_DIR / f"{safe_name}.pdf"
        try:
            r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            dest.write_bytes(r.content)
            saved.append(dest)
            print(f"OK   {name!r} -> {dest.name} ({len(r.content)/1024:.0f} KB)")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {name!r} <- {url}: {exc}")
    return saved


def maybe_push(saved: list[Path]) -> None:
    total_bytes = sum(p.stat().st_size for p in saved if p.exists())
    print(f"\nTotal downloaded: {total_bytes/1024/1024:.1f} MB across {len(saved)} files")

    if total_bytes == 0:
        print("Nothing downloaded -- see FAIL lines above. Not touching git.")
        return

    if total_bytes >= SIZE_LIMIT_BYTES:
        print(f"Over the 500MB limit -- leaving files local only, NOT pushing to GitHub.")
        return

    print("Under 500MB -- committing and pushing.")
    repo_root = OUT_DIR.parent.parent.parent
    subprocess.run(["git", "add", str(OUT_DIR)], cwd=repo_root, check=True)
    status = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo_root)
    if status.returncode == 0:
        print("No changes to commit (files already present and unchanged).")
        return
    subprocess.run(
        ["git", "commit", "-m", f"Add {len(saved)} real India Code Act PDFs as a starter corpus"],
        cwd=repo_root,
        check=True,
    )
    subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True)
    print("Pushed.")


if __name__ == "__main__":
    print(f"Fetching {LISTING_URL} ...")
    links = discover_links()
    if not links:
        print(
            "No matching PDF links found on the listing page -- the page structure may "
            "differ from what this script assumed. Open the URL in a browser, find a "
            "few real Act PDF links, and either fix PDF_LINK_RE/WANTED_KEYWORDS above "
            "or add them directly to a FALLBACK_LINKS list.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Matched {len(links)} acts, downloading...")
    saved = download_all(links)
    maybe_push(saved)
