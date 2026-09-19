"""Evaluation page (placeholder).

Reads /experiments for logged ablation runs (phase 6). No fabricated data --
if nothing has been logged yet, this page says so plainly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st

EXPERIMENTS_DIR = _REPO_ROOT / "experiments"

st.title("Evaluation")

run_dirs = sorted(p for p in EXPERIMENTS_DIR.glob("*") if p.is_dir()) if EXPERIMENTS_DIR.is_dir() else []
run_dirs = [p for p in run_dirs if (p / "results.json").is_file()]

if not run_dirs:
    st.info("No evaluation runs yet -- see docs/phases/phase-06-evaluation.md")
    st.stop()

for run_dir in run_dirs:
    st.subheader(run_dir.name)
    config_path = run_dir / "config.json"
    results_path = run_dir / "results.json"
    if config_path.is_file():
        with st.expander("config.json"):
            st.json(json.loads(config_path.read_text(encoding="utf-8")))
    st.json(json.loads(results_path.read_text(encoding="utf-8")))
