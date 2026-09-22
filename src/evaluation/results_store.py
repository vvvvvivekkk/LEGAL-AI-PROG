"""Read logged experiment runs from /experiments for the API's /evaluation view.

Each run is a directory under experiments/ containing config.json and/or
results.json (written by run_retrieval_eval.py). A sweep groups several runs in
one directory (experiments/<date>-ablations/retrieval/<config>/), so nested run
directories are found too and named by their path relative to experiments/.
This reader is deliberately tolerant: a missing experiments/ dir or a run
missing a file just yields fewer/empty fields rather than raising — the UI
shows "no runs yet".
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


# How deep below experiments/ a run directory may sit. One level is a plain
# run, two is a sweep grouping its arms, three is a sweep of sweeps.
MAX_RUN_DEPTH = 3


def load_runs(experiments_dir: str | Path = DEFAULT_EXPERIMENTS_DIR) -> list[dict]:
    """Return [{name, config, results}] for every run directory, name-sorted.

    A directory counts as a run when it holds a config.json or results.json.
    Sweeps nest their arms in subdirectories, so the search descends into a
    directory that is not itself a run, and keeps descending past one that is —
    a sweep may carry its own summary alongside per-arm subdirectories. Names
    are the path relative to experiments/, so nested runs stay distinguishable.
    """
    root = Path(experiments_dir)
    if not root.is_dir():
        return []

    runs: list[dict] = []

    def walk(directory: Path, depth: int) -> None:
        if depth > MAX_RUN_DEPTH:
            return
        for child in sorted(p for p in directory.iterdir() if p.is_dir()):
            config = _read_json(child / "config.json")
            results = _read_json(child / "results.json")
            if config or results:
                runs.append(
                    {
                        "name": child.relative_to(root).as_posix(),
                        "config": config,
                        "results": results,
                    }
                )
            walk(child, depth + 1)

    walk(root, 1)
    return runs
