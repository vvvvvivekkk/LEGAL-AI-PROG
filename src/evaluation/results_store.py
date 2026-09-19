"""Read logged experiment runs from /experiments for the API's /evaluation view.

Each run is a directory under experiments/ containing config.json and/or
results.json (written by run_retrieval_eval.py). This reader is deliberately
tolerant: a missing experiments/ dir or a run missing a file just yields
fewer/empty fields rather than raising — the UI shows "no runs yet".
"""

from __future__ import annotations

import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXPERIMENTS_DIR = _REPO_ROOT / "experiments"


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def load_runs(experiments_dir: str | Path = DEFAULT_EXPERIMENTS_DIR) -> list[dict]:
    """Return [{name, config, results}] for every run directory, name-sorted."""
    root = Path(experiments_dir)
    if not root.is_dir():
        return []
    runs: list[dict] = []
    for run_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        config = _read_json(run_dir / "config.json")
        results = _read_json(run_dir / "results.json")
        if not config and not results:
            continue
        runs.append({"name": run_dir.name, "config": config, "results": results})
    return runs
