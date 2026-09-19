"""Retrieval page.

A query box that runs the real phase-2 query helper (src/indexing/query.py)
against the LanceDB hybrid index and shows dense-only, FTS-only, and hybrid
(RRF-fused) results side by side, for debugging retrieval quality directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st

from src.indexing.build import DEFAULT_DB_PATH, open_table, table_exists
from src.indexing.query import compare_search

st.title("Retrieval")
st.caption(
    "Runs the real dense/FTS/hybrid query helper against the LanceDB index "
    "built on the Ingestion page."
)

if not table_exists(DEFAULT_DB_PATH):
    st.warning("No LanceDB index yet. Go to the Ingestion page and index at least one document first.")
    st.stop()

table = open_table(DEFAULT_DB_PATH)
st.caption(f"Index has {table.count_rows()} chunks.")

query = st.text_input("Query", placeholder="e.g. how long does a landlord have to refund a deposit?")
k = st.slider("Top-k per method", min_value=1, max_value=10, value=5)

if query:
    try:
        results = compare_search(table, query, k=k)
    except Exception as exc:  # noqa: BLE001 - surface embedding/search failures clearly
        st.error(f"Search failed: {exc}")
    else:
        col_dense, col_fts, col_hybrid = st.columns(3)
        for col, label, key in (
            (col_dense, "Dense (vector)", "dense"),
            (col_fts, "FTS (keyword)", "fts"),
            (col_hybrid, "Hybrid (RRF)", "hybrid"),
        ):
            with col:
                st.subheader(label)
                rows = results[key]
                if not rows:
                    st.write("No results.")
                for rank, row in enumerate(rows, start=1):
                    st.markdown(f"**{rank}. {row['metadata'].get('section_ref', row['chunk_id'])}**")
                    st.caption(row["metadata"].get("act", ""))
                    st.write(row["text"])
                    st.divider()
