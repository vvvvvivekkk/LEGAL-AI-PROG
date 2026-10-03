"""Ingest every .txt and .pdf file in a folder, through the API.

Uses the same /ingest endpoint as the web app, so the backend must be running
(start.bat, or `uvicorn lc.api:app`). Defaults to the criminal-law demo pack:

    python scripts/ingest_folder.py                      # data/demo_crime (27 files)
    python scripts/ingest_folder.py data/sample          # any other folder
    python scripts/ingest_folder.py --replace            # re-index files already in the index

Files already in the index are skipped (or, with --replace, removed and indexed
again). Ends with the index totals, as shown on the Home page.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "data" / "demo_crime"
TYPES = {".txt": "text/plain", ".pdf": "application/pdf"}


def post(client: httpx.Client, path: Path) -> httpx.Response:
    with path.open("rb") as fh:
        return client.post("/ingest", files={"file": (path.name, fh, TYPES[path.suffix.lower()])})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", nargs="?", default=str(DEFAULT))
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--replace", action="store_true", help="remove and re-index files already indexed")
    args = ap.parse_args()

    folder = Path(args.folder)
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in TYPES)
    if not files:
        sys.exit(f"No .txt or .pdf files in {folder}")

    counts = {"indexed": 0, "skipped": 0, "replaced": 0}
    with httpx.Client(base_url=args.base, timeout=300) as client:
        try:
            client.get("/health").raise_for_status()
        except httpx.HTTPError as exc:
            sys.exit(f"Backend not reachable at {args.base} ({exc}). Start it with start.bat first.")

        for path in files:
            r = post(client, path)
            if r.status_code == 409 and args.replace:
                source_id = r.json()["detail"]["duplicate_source_id"]
                client.delete(f"/documents/{source_id}").raise_for_status()
                r = post(client, path)
                counts["replaced"] += 1
            if r.status_code == 200:
                body = r.json()
                how = "by paragraph" if body.get("used_fallback") else "by section"
                print(f"  indexed   {path.name}: {body['new_chunk_count']} chunks ({how})")
                counts["indexed"] += 1
            elif r.status_code == 409:
                print(f"  skipped   {path.name}: already in the index")
                counts["skipped"] += 1
            else:
                sys.exit(f"  ERROR {r.status_code} on {path.name}: {r.text[:300]}")

        stats = client.get("/stats").json()
    print(
        f"\n{counts['indexed']} indexed ({counts['replaced']} replaced), {counts['skipped']} skipped. "
        f"Index now holds {stats.get('documents')} documents, {stats.get('chunks')} chunks."
    )


if __name__ == "__main__":
    main()
